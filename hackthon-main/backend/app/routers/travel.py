"""Travel data endpoints — hotels, flights, weather, locations.

Weather uses Open-Meteo (no API key). Hotels/flights/locations proxy to
Amadeus Self-Service. All endpoints are public — no auth required — so the
frontend can render live data on landing/discover pages before login.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.schemas.travel import (
    FlightItinerary,
    FlightOffer,
    FlightSegment,
    FlightsResponse,
    HotelListItem,
    HotelOfferGroup,
    HotelOfferItem,
    HotelOfferPrice,
    HotelsResponse,
    LocationHit,
    LocationSearchResponse,
    WeatherCurrent,
    WeatherDay,
    WeatherResponse,
)
from app.services.amadeus import AmadeusError, amadeus_client
from app.services.travel_mock import (
    mock_flights,
    mock_hotels,
    mock_locations,
    resolve_iata_mock,
)


router = APIRouter(prefix="/api/travel", tags=["travel"])


def _mock_notice_header() -> dict[str, str]:
    """Every mock-fallback response includes this so the frontend can badge
    the results as "demo mode"."""
    return {"X-Travel-Data-Source": "mock"}


def _amadeus_error(err: AmadeusError) -> HTTPException:
    status = 503 if err.status == 503 else 502
    return HTTPException(status_code=status, detail=str(err))


# ---- locations -------------------------------------------------------------

@router.get("/locations", response_model=LocationSearchResponse)
async def search_locations(
    keyword: str = Query(..., min_length=2),
    sub_type: str = Query("CITY,AIRPORT", alias="subType"),
) -> LocationSearchResponse:
    if not amadeus_client.is_configured:
        return mock_locations(keyword)
    try:
        data = await amadeus_client.get(
            "/v1/reference-data/locations",
            {"keyword": keyword, "subType": sub_type, "page[limit]": 10},
        )
    except AmadeusError as e:
        raise _amadeus_error(e)

    return LocationSearchResponse(
        results=[
            LocationHit(
                name=item.get("name", ""),
                iata_code=item.get("iataCode", ""),
                sub_type=item.get("subType", ""),
                city_name=(item.get("address") or {}).get("cityName"),
                country_code=(item.get("address") or {}).get("countryCode"),
                geo=item.get("geoCode"),
            )
            for item in (data.get("data") or [])
            if item.get("iataCode")
        ]
    )


# ---- hotels ----------------------------------------------------------------

@router.get("/hotels", response_model=HotelsResponse)
async def hotels(
    city: str | None = Query(None, description="Free-text city name; resolved via locations"),
    city_code: str | None = Query(None, alias="cityCode", description="IATA city code (e.g. PAR)"),
    check_in: str | None = Query(None, alias="checkIn"),
    check_out: str | None = Query(None, alias="checkOut"),
    adults: int = Query(1, ge=1, le=9),
) -> HotelsResponse:
    if not city and not city_code:
        raise HTTPException(status_code=400, detail="city or cityCode is required")

    if not amadeus_client.is_configured:
        resolved = (city_code or "").upper() or (resolve_iata_mock(city or "") or "")
        if not resolved:
            raise HTTPException(status_code=404, detail=f"No IATA city code found for '{city}'")
        return mock_hotels(resolved, check_in, check_out, adults)

    try:
        resolved = (city_code or "").upper() or await amadeus_client.resolve_iata(city or "", "CITY")
        if not resolved:
            raise HTTPException(status_code=404, detail=f"No IATA city code found for '{city}'")

        listing = await amadeus_client.get(
            "/v1/reference-data/locations/hotels/by-city",
            {"cityCode": resolved},
        )
        hotels_data = listing.get("data") or []
        hotel_ids = ",".join(h["hotelId"] for h in hotels_data[:20] if h.get("hotelId"))

        offers_data: list[dict[str, Any]] = []
        if hotel_ids:
            offers_resp = await amadeus_client.get(
                "/v3/shopping/hotel-offers",
                {
                    "hotelIds": hotel_ids,
                    "adults": adults,
                    "checkInDate": check_in,
                    "checkOutDate": check_out,
                    "bestRateOnly": "true",
                },
            )
            offers_data = offers_resp.get("data") or []
    except AmadeusError as e:
        raise _amadeus_error(e)

    return HotelsResponse(
        city_code=resolved,
        hotels=[
            HotelListItem(
                hotel_id=h["hotelId"],
                name=h.get("name", ""),
                iata_code=h.get("iataCode"),
                geo=h.get("geoCode"),
            )
            for h in hotels_data
            if h.get("hotelId")
        ],
        offers=[
            HotelOfferGroup(
                hotel_id=group.get("hotel", {}).get("hotelId", ""),
                hotel_name=group.get("hotel", {}).get("name", ""),
                available=bool(group.get("available")),
                offers=[
                    HotelOfferItem(
                        id=o.get("id", ""),
                        check_in_date=o.get("checkInDate", ""),
                        check_out_date=o.get("checkOutDate", ""),
                        room_description=((o.get("room") or {}).get("description") or {}).get("text"),
                        price=HotelOfferPrice(
                            currency=o.get("price", {}).get("currency", ""),
                            total=o.get("price", {}).get("total", ""),
                            base=o.get("price", {}).get("base"),
                        ),
                    )
                    for o in (group.get("offers") or [])
                ],
            )
            for group in offers_data
        ],
    )


# ---- flights ---------------------------------------------------------------

@router.get("/flights", response_model=FlightsResponse)
async def flights(
    origin: str | None = Query(None, description="IATA airport/city code"),
    destination: str | None = Query(None, description="IATA airport/city code"),
    origin_city: str | None = Query(None, alias="originCity"),
    destination_city: str | None = Query(None, alias="destinationCity"),
    departure_date: str = Query(..., alias="departureDate"),
    return_date: str | None = Query(None, alias="returnDate"),
    adults: int = Query(1, ge=1, le=9),
    currency: str = Query("INR"),
    max_offers: int = Query(10, alias="max", ge=1, le=50),
) -> FlightsResponse:
    if not amadeus_client.is_configured:
        origin_iata = (origin or "").upper() or (resolve_iata_mock(origin_city or "") or "")
        dest_iata = (destination or "").upper() or (resolve_iata_mock(destination_city or "") or "")
        if not origin_iata or not dest_iata:
            missing = origin_city if not origin_iata else destination_city
            raise HTTPException(status_code=404, detail=f"Could not resolve IATA code for '{missing}'")
        return mock_flights(origin_iata, dest_iata, departure_date, return_date, currency, max_offers)

    try:
        origin_iata = (origin or "").upper() or (
            await amadeus_client.resolve_iata(origin_city) if origin_city else None
        )
        dest_iata = (destination or "").upper() or (
            await amadeus_client.resolve_iata(destination_city) if destination_city else None
        )
        if not origin_iata or not dest_iata:
            missing = origin_city if not origin_iata else destination_city
            raise HTTPException(status_code=404, detail=f"Could not resolve IATA code for '{missing}'")

        data = await amadeus_client.get(
            "/v2/shopping/flight-offers",
            {
                "originLocationCode": origin_iata,
                "destinationLocationCode": dest_iata,
                "departureDate": departure_date,
                "returnDate": return_date,
                "adults": adults,
                "currencyCode": currency,
                "max": max_offers,
            },
        )
    except AmadeusError as e:
        raise _amadeus_error(e)

    return FlightsResponse(
        origin=origin_iata,
        destination=dest_iata,
        offers=[
            FlightOffer(
                id=o.get("id", ""),
                currency=o.get("price", {}).get("currency", ""),
                total=o.get("price", {}).get("grandTotal") or o.get("price", {}).get("total", ""),
                itineraries=[
                    FlightItinerary(
                        duration=itin.get("duration", ""),
                        segments=[
                            FlightSegment(
                                departure_iata=seg.get("departure", {}).get("iataCode", ""),
                                departure_at=seg.get("departure", {}).get("at", ""),
                                arrival_iata=seg.get("arrival", {}).get("iataCode", ""),
                                arrival_at=seg.get("arrival", {}).get("at", ""),
                                carrier_code=seg.get("carrierCode", ""),
                                number=seg.get("number", ""),
                                duration=seg.get("duration"),
                                stops=seg.get("numberOfStops", 0),
                            )
                            for seg in (itin.get("segments") or [])
                        ],
                    )
                    for itin in (o.get("itineraries") or [])
                ],
            )
            for o in (data.get("data") or [])
        ],
    )


# ---- weather ---------------------------------------------------------------

async def _geocode(client: httpx.AsyncClient, place: str) -> dict[str, Any] | None:
    r = await client.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": place, "count": 1, "language": "en", "format": "json"},
    )
    if r.status_code != 200:
        return None
    results = (r.json() or {}).get("results") or []
    return results[0] if results else None


@router.get("/weather", response_model=WeatherResponse)
async def weather(
    place: str | None = Query(None, description="Free-text location (geocoded via Open-Meteo)"),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
) -> WeatherResponse:
    if lat is None or lon is None:
        if not place:
            raise HTTPException(status_code=400, detail="Provide place or lat+lon")
        async with httpx.AsyncClient(timeout=10.0) as client:
            hit = await _geocode(client, place)
        if not hit:
            raise HTTPException(status_code=404, detail=f"Location '{place}' not found")
        lat, lon = hit["latitude"], hit["longitude"]
        location = {"name": hit.get("name"), "country": hit.get("country"), "lat": lat, "lon": lon}
    else:
        location = {"lat": lat, "lon": lon}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                "forecast_days": 7,
                "timezone": "auto",
            },
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Open-Meteo request failed")
    payload = r.json()
    cur = payload.get("current") or {}
    daily = payload.get("daily") or {}

    days: list[WeatherDay] = []
    for i, date in enumerate(daily.get("time") or []):
        days.append(
            WeatherDay(
                date=date,
                temp_max=daily["temperature_2m_max"][i],
                temp_min=daily["temperature_2m_min"][i],
                weather_code=daily["weather_code"][i],
                precipitation_mm=daily["precipitation_sum"][i],
            )
        )

    return WeatherResponse(
        location=location,
        current=WeatherCurrent(
            temperature_c=cur.get("temperature_2m", 0.0),
            weather_code=cur.get("weather_code", 0),
            wind_kph=cur.get("wind_speed_10m", 0.0),
            humidity=cur.get("relative_humidity_2m", 0),
        ),
        daily=days,
    )
