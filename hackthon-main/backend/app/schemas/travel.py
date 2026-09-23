"""Pydantic models for /api/travel — hotels, weather, flights, locations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class LocationHit(BaseModel):
    name: str
    iata_code: str
    sub_type: str
    city_name: str | None = None
    country_code: str | None = None
    geo: dict[str, float] | None = None


class LocationSearchResponse(BaseModel):
    results: list[LocationHit]


class HotelListItem(BaseModel):
    hotel_id: str
    name: str
    iata_code: str | None = None
    geo: dict[str, float] | None = None


class HotelOfferPrice(BaseModel):
    currency: str
    total: str
    base: str | None = None


class HotelOfferItem(BaseModel):
    id: str
    check_in_date: str
    check_out_date: str
    room_description: str | None = None
    price: HotelOfferPrice


class HotelOfferGroup(BaseModel):
    hotel_id: str
    hotel_name: str
    available: bool
    offers: list[HotelOfferItem]


class HotelsResponse(BaseModel):
    city_code: str
    hotels: list[HotelListItem]
    offers: list[HotelOfferGroup]


class FlightSegment(BaseModel):
    departure_iata: str
    departure_at: str
    arrival_iata: str
    arrival_at: str
    carrier_code: str
    number: str
    duration: str | None = None
    stops: int = 0


class FlightItinerary(BaseModel):
    duration: str
    segments: list[FlightSegment]


class FlightOffer(BaseModel):
    id: str
    currency: str
    total: str
    itineraries: list[FlightItinerary]


class FlightsResponse(BaseModel):
    origin: str
    destination: str
    offers: list[FlightOffer]


class WeatherCurrent(BaseModel):
    temperature_c: float
    weather_code: int
    wind_kph: float
    humidity: int


class WeatherDay(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    weather_code: int
    precipitation_mm: float


class WeatherResponse(BaseModel):
    location: dict[str, Any]
    current: WeatherCurrent
    daily: list[WeatherDay]
