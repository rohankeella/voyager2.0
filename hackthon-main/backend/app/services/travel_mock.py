"""Offline fallback for `/api/travel` endpoints.

Kicks in when Amadeus credentials aren't configured. Returns deterministic
mock data so the frontend flight/hotel/location search works in demos and
CI without external API access. Mirrors the shape produced by
`travel.py`'s Pydantic response models so callers see no schema difference.

Follows the same pattern as `services/logistics.py` (Haversine fallback
when Google Maps key is absent) — the app degrades gracefully instead of
returning 503.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone

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
)


# ---- reference dataset -----------------------------------------------------
# Small worldwide airport/city set that covers the most-common demo routes.

_AIRPORTS: list[dict] = [
    # ---- India (metros, tier-2, and gateways to major tourist regions) ----
    {"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj International", "city": "Mumbai",     "country": "IN", "lat": 19.0896, "lng": 72.8656},
    {"iata": "DEL", "name": "Indira Gandhi International",              "city": "Delhi",      "country": "IN", "lat": 28.5562, "lng": 77.1000},
    {"iata": "BLR", "name": "Kempegowda International",                  "city": "Bangalore",  "country": "IN", "lat": 13.1979, "lng": 77.7063},
    {"iata": "MAA", "name": "Chennai International",                     "city": "Chennai",    "country": "IN", "lat": 12.9941, "lng": 80.1707},
    {"iata": "CCU", "name": "Netaji Subhas Chandra Bose International",  "city": "Kolkata",    "country": "IN", "lat": 22.6547, "lng": 88.4467},
    {"iata": "HYD", "name": "Rajiv Gandhi International",                "city": "Hyderabad",  "country": "IN", "lat": 17.2403, "lng": 78.4294},
    {"iata": "GOI", "name": "Dabolim",                                   "city": "Goa",        "country": "IN", "lat": 15.3808, "lng": 73.8314},
    {"iata": "COK", "name": "Cochin International",                      "city": "Kochi",      "country": "IN", "lat": 10.1520, "lng": 76.4019},
    {"iata": "TRV", "name": "Trivandrum International",                  "city": "Trivandrum", "country": "IN", "lat": 8.4821,  "lng": 76.9200},
    {"iata": "CJB", "name": "Coimbatore International",                  "city": "Coimbatore", "country": "IN", "lat": 11.0300, "lng": 77.0433},
    {"iata": "CCJ", "name": "Calicut International",                     "city": "Kozhikode",  "country": "IN", "lat": 11.1367, "lng": 75.9550},
    {"iata": "PNQ", "name": "Pune International",                        "city": "Pune",       "country": "IN", "lat": 18.5822, "lng": 73.9197},
    {"iata": "AMD", "name": "Sardar Vallabhbhai Patel International",    "city": "Ahmedabad",  "country": "IN", "lat": 23.0772, "lng": 72.6347},
    {"iata": "JAI", "name": "Jaipur International",                      "city": "Jaipur",     "country": "IN", "lat": 26.8242, "lng": 75.8122},
    {"iata": "UDR", "name": "Maharana Pratap",                           "city": "Udaipur",    "country": "IN", "lat": 24.6177, "lng": 73.8961},
    {"iata": "JDH", "name": "Jodhpur",                                   "city": "Jodhpur",    "country": "IN", "lat": 26.2511, "lng": 73.0489},
    {"iata": "JSA", "name": "Jaisalmer",                                 "city": "Jaisalmer",  "country": "IN", "lat": 26.8887, "lng": 70.8650},
    {"iata": "LKO", "name": "Chaudhary Charan Singh International",      "city": "Lucknow",    "country": "IN", "lat": 26.7606, "lng": 80.8893},
    {"iata": "VNS", "name": "Lal Bahadur Shastri International",         "city": "Varanasi",   "country": "IN", "lat": 25.4524, "lng": 82.8593},
    {"iata": "AGR", "name": "Agra",                                      "city": "Agra",       "country": "IN", "lat": 27.1558, "lng": 77.9608},
    {"iata": "ATQ", "name": "Sri Guru Ram Dass Jee International",       "city": "Amritsar",   "country": "IN", "lat": 31.7096, "lng": 74.7973},
    {"iata": "SXR", "name": "Sheikh ul-Alam International",              "city": "Srinagar",   "country": "IN", "lat": 33.9871, "lng": 74.7742},
    {"iata": "IXL", "name": "Kushok Bakula Rimpochee",                   "city": "Leh",        "country": "IN", "lat": 34.1358, "lng": 77.5464},
    {"iata": "DED", "name": "Dehradun (Jolly Grant)",                    "city": "Dehradun",   "country": "IN", "lat": 30.1897, "lng": 78.1804},
    {"iata": "KUU", "name": "Kullu Manali (Bhuntar)",                    "city": "Kullu",      "country": "IN", "lat": 31.8767, "lng": 77.1544},
    {"iata": "SLV", "name": "Shimla",                                    "city": "Shimla",     "country": "IN", "lat": 31.0818, "lng": 77.0678},
    {"iata": "GAU", "name": "Lokpriya Gopinath Bordoloi International",  "city": "Guwahati",   "country": "IN", "lat": 26.1061, "lng": 91.5859},
    {"iata": "IXB", "name": "Bagdogra",                                  "city": "Siliguri",   "country": "IN", "lat": 26.6812, "lng": 88.3286},
    {"iata": "BBI", "name": "Biju Patnaik International",                "city": "Bhubaneswar","country": "IN", "lat": 20.2444, "lng": 85.8178},
    {"iata": "IXZ", "name": "Veer Savarkar International",               "city": "Port Blair", "country": "IN", "lat": 11.6412, "lng": 92.7297},
    {"iata": "IXC", "name": "Chandigarh",                                "city": "Chandigarh", "country": "IN", "lat": 30.6735, "lng": 76.7885},
    {"iata": "IXM", "name": "Madurai",                                   "city": "Madurai",    "country": "IN", "lat": 9.8345,  "lng": 78.0934},
    {"iata": "TIR", "name": "Tirupati",                                  "city": "Tirupati",   "country": "IN", "lat": 13.6325, "lng": 79.5433},
    {"iata": "RPR", "name": "Swami Vivekananda",                         "city": "Raipur",     "country": "IN", "lat": 21.1804, "lng": 81.7388},
    {"iata": "IDR", "name": "Devi Ahilyabai Holkar",                     "city": "Indore",     "country": "IN", "lat": 22.7218, "lng": 75.8011},
    {"iata": "HJR", "name": "Khajuraho",                                 "city": "Khajuraho",  "country": "IN", "lat": 24.8172, "lng": 79.9186},

    # ---- East Asia ----
    {"iata": "KIX", "name": "Kansai International",                      "city": "Osaka",      "country": "JP", "lat": 34.4342, "lng": 135.2444},
    {"iata": "NRT", "name": "Narita International",                      "city": "Tokyo",      "country": "JP", "lat": 35.7647, "lng": 140.3863},
    {"iata": "HND", "name": "Haneda",                                    "city": "Tokyo",      "country": "JP", "lat": 35.5494, "lng": 139.7798},
    {"iata": "CTS", "name": "New Chitose",                               "city": "Sapporo",    "country": "JP", "lat": 42.7752, "lng": 141.6923},
    {"iata": "OKA", "name": "Naha",                                      "city": "Okinawa",    "country": "JP", "lat": 26.1958, "lng": 127.6459},
    {"iata": "ICN", "name": "Incheon International",                     "city": "Seoul",      "country": "KR", "lat": 37.4691, "lng": 126.4505},
    {"iata": "PEK", "name": "Beijing Capital",                           "city": "Beijing",    "country": "CN", "lat": 40.0799, "lng": 116.6031},
    {"iata": "PVG", "name": "Shanghai Pudong",                           "city": "Shanghai",   "country": "CN", "lat": 31.1443, "lng": 121.8083},
    {"iata": "HKG", "name": "Hong Kong International",                   "city": "Hong Kong",  "country": "HK", "lat": 22.3080, "lng": 113.9185},
    {"iata": "TPE", "name": "Taoyuan International",                     "city": "Taipei",     "country": "TW", "lat": 25.0777, "lng": 121.2328},

    # ---- Southeast Asia ----
    {"iata": "SIN", "name": "Changi",                                    "city": "Singapore",  "country": "SG", "lat": 1.3644,  "lng": 103.9915},
    {"iata": "BKK", "name": "Suvarnabhumi",                              "city": "Bangkok",    "country": "TH", "lat": 13.6900, "lng": 100.7501},
    {"iata": "HKT", "name": "Phuket International",                      "city": "Phuket",     "country": "TH", "lat": 8.1132,  "lng": 98.3169},
    {"iata": "CNX", "name": "Chiang Mai International",                  "city": "Chiang Mai", "country": "TH", "lat": 18.7669, "lng": 98.9628},
    {"iata": "USM", "name": "Samui",                                     "city": "Koh Samui",  "country": "TH", "lat": 9.5479,  "lng": 100.0622},
    {"iata": "KUL", "name": "Kuala Lumpur International",                "city": "Kuala Lumpur","country": "MY", "lat": 2.7456,  "lng": 101.7099},
    {"iata": "DPS", "name": "Ngurah Rai",                                "city": "Denpasar",   "country": "ID", "lat": -8.7482, "lng": 115.1671},
    {"iata": "CGK", "name": "Soekarno-Hatta International",              "city": "Jakarta",    "country": "ID", "lat": -6.1256, "lng": 106.6558},
    {"iata": "JOG", "name": "Yogyakarta International",                  "city": "Yogyakarta", "country": "ID", "lat": -7.9040, "lng": 110.0567},
    {"iata": "MNL", "name": "Ninoy Aquino International",                "city": "Manila",     "country": "PH", "lat": 14.5086, "lng": 121.0197},
    {"iata": "CEB", "name": "Mactan-Cebu International",                 "city": "Cebu",       "country": "PH", "lat": 10.3075, "lng": 123.9793},
    {"iata": "SGN", "name": "Tan Son Nhat International",                "city": "Ho Chi Minh","country": "VN", "lat": 10.8188, "lng": 106.6519},
    {"iata": "HAN", "name": "Noi Bai International",                     "city": "Hanoi",      "country": "VN", "lat": 21.2212, "lng": 105.8072},
    {"iata": "REP", "name": "Siem Reap-Angkor International",            "city": "Siem Reap",  "country": "KH", "lat": 13.4108, "lng": 103.8134},

    # ---- South Asia (neighbours) ----
    {"iata": "KTM", "name": "Tribhuvan International",                   "city": "Kathmandu",  "country": "NP", "lat": 27.6966, "lng": 85.3591},
    {"iata": "PBH", "name": "Paro International",                        "city": "Paro",       "country": "BT", "lat": 27.4033, "lng": 89.4247},
    {"iata": "CMB", "name": "Bandaranaike International",                "city": "Colombo",    "country": "LK", "lat": 7.1808,  "lng": 79.8842},
    {"iata": "MLE", "name": "Velana International",                      "city": "Male",       "country": "MV", "lat": 4.1918,  "lng": 73.5289},
    {"iata": "DAC", "name": "Hazrat Shahjalal International",            "city": "Dhaka",      "country": "BD", "lat": 23.8433, "lng": 90.4033},

    # ---- Middle East ----
    {"iata": "DXB", "name": "Dubai International",                       "city": "Dubai",      "country": "AE", "lat": 25.2532, "lng": 55.3657},
    {"iata": "AUH", "name": "Abu Dhabi International",                   "city": "Abu Dhabi",  "country": "AE", "lat": 24.4330, "lng": 54.6511},
    {"iata": "DOH", "name": "Hamad International",                       "city": "Doha",       "country": "QA", "lat": 25.2731, "lng": 51.6081},
    {"iata": "RUH", "name": "King Khalid International",                 "city": "Riyadh",     "country": "SA", "lat": 24.9576, "lng": 46.6988},
    {"iata": "JED", "name": "King Abdulaziz International",              "city": "Jeddah",     "country": "SA", "lat": 21.6796, "lng": 39.1565},
    {"iata": "TLV", "name": "Ben Gurion International",                  "city": "Tel Aviv",   "country": "IL", "lat": 32.0114, "lng": 34.8867},
    {"iata": "AMM", "name": "Queen Alia International",                  "city": "Amman",      "country": "JO", "lat": 31.7226, "lng": 35.9932},
    {"iata": "BEY", "name": "Beirut-Rafic Hariri International",         "city": "Beirut",     "country": "LB", "lat": 33.8209, "lng": 35.4884},
    {"iata": "CAI", "name": "Cairo International",                       "city": "Cairo",      "country": "EG", "lat": 30.1219, "lng": 31.4056},
    {"iata": "HRG", "name": "Hurghada International",                    "city": "Hurghada",   "country": "EG", "lat": 27.1783, "lng": 33.7994},

    # ---- Europe ----
    {"iata": "CDG", "name": "Charles de Gaulle",                         "city": "Paris",      "country": "FR", "lat": 49.0097, "lng": 2.5479},
    {"iata": "NCE", "name": "Nice Cote d'Azur",                          "city": "Nice",       "country": "FR", "lat": 43.6584, "lng": 7.2159},
    {"iata": "LHR", "name": "Heathrow",                                  "city": "London",     "country": "GB", "lat": 51.4700, "lng": -0.4543},
    {"iata": "EDI", "name": "Edinburgh",                                 "city": "Edinburgh",  "country": "GB", "lat": 55.9500, "lng": -3.3725},
    {"iata": "DUB", "name": "Dublin",                                    "city": "Dublin",     "country": "IE", "lat": 53.4213, "lng": -6.2701},
    {"iata": "AMS", "name": "Schiphol",                                  "city": "Amsterdam",  "country": "NL", "lat": 52.3086, "lng": 4.7639},
    {"iata": "BRU", "name": "Brussels",                                  "city": "Brussels",   "country": "BE", "lat": 50.9014, "lng": 4.4844},
    {"iata": "FRA", "name": "Frankfurt",                                 "city": "Frankfurt",  "country": "DE", "lat": 50.0379, "lng": 8.5622},
    {"iata": "BER", "name": "Berlin Brandenburg",                        "city": "Berlin",     "country": "DE", "lat": 52.3667, "lng": 13.5033},
    {"iata": "MUC", "name": "Munich",                                    "city": "Munich",     "country": "DE", "lat": 48.3538, "lng": 11.7861},
    {"iata": "VIE", "name": "Vienna International",                      "city": "Vienna",     "country": "AT", "lat": 48.1103, "lng": 16.5697},
    {"iata": "PRG", "name": "Vaclav Havel",                              "city": "Prague",     "country": "CZ", "lat": 50.1008, "lng": 14.2600},
    {"iata": "BUD", "name": "Budapest Ferenc Liszt International",       "city": "Budapest",   "country": "HU", "lat": 47.4394, "lng": 19.2611},
    {"iata": "WAW", "name": "Warsaw Chopin",                             "city": "Warsaw",     "country": "PL", "lat": 52.1657, "lng": 20.9671},
    {"iata": "ZRH", "name": "Zurich",                                    "city": "Zurich",     "country": "CH", "lat": 47.4647, "lng": 8.5492},
    {"iata": "GVA", "name": "Geneva",                                    "city": "Geneva",     "country": "CH", "lat": 46.2381, "lng": 6.1090},
    {"iata": "MAD", "name": "Barajas",                                   "city": "Madrid",     "country": "ES", "lat": 40.4936, "lng": -3.5668},
    {"iata": "BCN", "name": "Barcelona-El Prat",                         "city": "Barcelona",  "country": "ES", "lat": 41.2974, "lng": 2.0833},
    {"iata": "AGP", "name": "Malaga-Costa del Sol",                      "city": "Malaga",     "country": "ES", "lat": 36.6749, "lng": -4.4991},
    {"iata": "LIS", "name": "Humberto Delgado",                          "city": "Lisbon",     "country": "PT", "lat": 38.7742, "lng": -9.1342},
    {"iata": "FCO", "name": "Leonardo da Vinci-Fiumicino",               "city": "Rome",       "country": "IT", "lat": 41.8003, "lng": 12.2389},
    {"iata": "MXP", "name": "Milan Malpensa",                            "city": "Milan",      "country": "IT", "lat": 45.6306, "lng": 8.7281},
    {"iata": "VCE", "name": "Venice Marco Polo",                         "city": "Venice",     "country": "IT", "lat": 45.5053, "lng": 12.3519},
    {"iata": "FLR", "name": "Florence Amerigo Vespucci",                 "city": "Florence",   "country": "IT", "lat": 43.8100, "lng": 11.2051},
    {"iata": "NAP", "name": "Naples International",                      "city": "Naples",     "country": "IT", "lat": 40.8860, "lng": 14.2908},
    {"iata": "PMO", "name": "Palermo",                                   "city": "Palermo",    "country": "IT", "lat": 38.1759, "lng": 13.0910},
    {"iata": "ATH", "name": "Athens International",                      "city": "Athens",     "country": "GR", "lat": 37.9364, "lng": 23.9445},
    {"iata": "JTR", "name": "Santorini (Thira) National",                "city": "Santorini",  "country": "GR", "lat": 36.3992, "lng": 25.4793},
    {"iata": "HER", "name": "Heraklion",                                 "city": "Heraklion",  "country": "GR", "lat": 35.3397, "lng": 25.1803},
    {"iata": "IST", "name": "Istanbul",                                  "city": "Istanbul",   "country": "TR", "lat": 41.2753, "lng": 28.7519},
    {"iata": "ASR", "name": "Kayseri Erkilet",                           "city": "Kayseri",    "country": "TR", "lat": 38.7706, "lng": 35.4936},
    {"iata": "AYT", "name": "Antalya",                                   "city": "Antalya",    "country": "TR", "lat": 36.8987, "lng": 30.8005},
    {"iata": "KEF", "name": "Keflavik",                                  "city": "Reykjavik",  "country": "IS", "lat": 63.9850, "lng": -22.6056},
    {"iata": "OSL", "name": "Oslo Gardermoen",                           "city": "Oslo",       "country": "NO", "lat": 60.1939, "lng": 11.1004},
    {"iata": "TOS", "name": "Tromso",                                    "city": "Tromso",     "country": "NO", "lat": 69.6832, "lng": 18.9189},
    {"iata": "ARN", "name": "Stockholm Arlanda",                         "city": "Stockholm",  "country": "SE", "lat": 59.6519, "lng": 17.9186},
    {"iata": "CPH", "name": "Copenhagen Kastrup",                        "city": "Copenhagen", "country": "DK", "lat": 55.6180, "lng": 12.6560},
    {"iata": "HEL", "name": "Helsinki Vantaa",                           "city": "Helsinki",   "country": "FI", "lat": 60.3172, "lng": 24.9633},

    # ---- Africa ----
    {"iata": "CPT", "name": "Cape Town International",                   "city": "Cape Town",  "country": "ZA", "lat": -33.9689,"lng": 18.6017},
    {"iata": "JNB", "name": "O.R. Tambo International",                  "city": "Johannesburg","country": "ZA", "lat": -26.1367,"lng": 28.2411},
    {"iata": "NBO", "name": "Jomo Kenyatta International",               "city": "Nairobi",    "country": "KE", "lat": -1.3192, "lng": 36.9278},
    {"iata": "MBA", "name": "Moi International",                         "city": "Mombasa",    "country": "KE", "lat": -4.0348, "lng": 39.5942},
    {"iata": "JRO", "name": "Kilimanjaro International",                 "city": "Arusha",     "country": "TZ", "lat": -3.4293, "lng": 37.0745},
    {"iata": "ZNZ", "name": "Abeid Amani Karume International",          "city": "Zanzibar",   "country": "TZ", "lat": -6.2222, "lng": 39.2249},
    {"iata": "RAK", "name": "Marrakech Menara",                          "city": "Marrakech",  "country": "MA", "lat": 31.6069, "lng": -8.0363},
    {"iata": "CMN", "name": "Mohammed V International",                  "city": "Casablanca", "country": "MA", "lat": 33.3675, "lng": -7.5900},
    {"iata": "ADD", "name": "Bole International",                        "city": "Addis Ababa","country": "ET", "lat": 8.9779,  "lng": 38.7993},
    {"iata": "LOS", "name": "Murtala Muhammed International",            "city": "Lagos",      "country": "NG", "lat": 6.5774,  "lng": 3.3212},
    {"iata": "VFA", "name": "Victoria Falls",                            "city": "Victoria Falls","country":"ZW","lat": -18.0959,"lng": 25.8390},
    {"iata": "MRU", "name": "Sir Seewoosagur Ramgoolam International",   "city": "Port Louis", "country": "MU", "lat": -20.4302,"lng": 57.6836},
    {"iata": "SEZ", "name": "Seychelles International",                  "city": "Mahe",       "country": "SC", "lat": -4.6743, "lng": 55.5218},

    # ---- North America ----
    {"iata": "JFK", "name": "John F. Kennedy International",             "city": "New York",   "country": "US", "lat": 40.6413, "lng": -73.7781},
    {"iata": "EWR", "name": "Newark Liberty",                            "city": "Newark",     "country": "US", "lat": 40.6895, "lng": -74.1745},
    {"iata": "LAX", "name": "Los Angeles International",                 "city": "Los Angeles","country": "US", "lat": 33.9416, "lng": -118.4085},
    {"iata": "SFO", "name": "San Francisco International",               "city": "San Francisco","country":"US","lat": 37.6213, "lng": -122.3790},
    {"iata": "SEA", "name": "Seattle-Tacoma International",              "city": "Seattle",    "country": "US", "lat": 47.4502, "lng": -122.3088},
    {"iata": "ORD", "name": "Chicago O'Hare",                            "city": "Chicago",    "country": "US", "lat": 41.9742, "lng": -87.9073},
    {"iata": "MIA", "name": "Miami International",                       "city": "Miami",      "country": "US", "lat": 25.7959, "lng": -80.2870},
    {"iata": "MCO", "name": "Orlando International",                     "city": "Orlando",    "country": "US", "lat": 28.4312, "lng": -81.3081},
    {"iata": "LAS", "name": "Harry Reid International",                  "city": "Las Vegas",  "country": "US", "lat": 36.0840, "lng": -115.1537},
    {"iata": "BOS", "name": "Boston Logan",                              "city": "Boston",     "country": "US", "lat": 42.3656, "lng": -71.0096},
    {"iata": "IAD", "name": "Washington Dulles",                         "city": "Washington", "country": "US", "lat": 38.9531, "lng": -77.4565},
    {"iata": "HNL", "name": "Daniel K. Inouye International",            "city": "Honolulu",   "country": "US", "lat": 21.3245, "lng": -157.9251},
    {"iata": "ANC", "name": "Ted Stevens Anchorage International",       "city": "Anchorage",  "country": "US", "lat": 61.1743, "lng": -149.9963},
    {"iata": "YYZ", "name": "Toronto Pearson",                           "city": "Toronto",    "country": "CA", "lat": 43.6777, "lng": -79.6248},
    {"iata": "YVR", "name": "Vancouver International",                   "city": "Vancouver",  "country": "CA", "lat": 49.1967, "lng": -123.1815},
    {"iata": "YUL", "name": "Montreal-Trudeau",                          "city": "Montreal",   "country": "CA", "lat": 45.4657, "lng": -73.7455},
    {"iata": "MEX", "name": "Mexico City International",                 "city": "Mexico City","country": "MX", "lat": 19.4361, "lng": -99.0719},
    {"iata": "CUN", "name": "Cancun International",                      "city": "Cancun",     "country": "MX", "lat": 21.0365, "lng": -86.8771},
    {"iata": "HAV", "name": "Jose Marti International",                  "city": "Havana",     "country": "CU", "lat": 22.9892, "lng": -82.4091},
    {"iata": "SJU", "name": "Luis Munoz Marin International",            "city": "San Juan",   "country": "PR", "lat": 18.4394, "lng": -66.0018},

    # ---- South America ----
    {"iata": "GRU", "name": "Guarulhos International",                   "city": "Sao Paulo",  "country": "BR", "lat": -23.4356,"lng": -46.4731},
    {"iata": "GIG", "name": "Rio de Janeiro-Galeao",                     "city": "Rio de Janeiro","country":"BR","lat": -22.8100,"lng": -43.2506},
    {"iata": "MAO", "name": "Eduardo Gomes International",               "city": "Manaus",     "country": "BR", "lat": -3.0386, "lng": -60.0497},
    {"iata": "IGR", "name": "Cataratas del Iguazu",                      "city": "Puerto Iguazu","country":"AR","lat": -25.7373,"lng": -54.4734},
    {"iata": "EZE", "name": "Ministro Pistarini",                        "city": "Buenos Aires","country": "AR", "lat": -34.8222,"lng": -58.5358},
    {"iata": "SCL", "name": "Arturo Merino Benitez",                     "city": "Santiago",   "country": "CL", "lat": -33.3928,"lng": -70.7854},
    {"iata": "IPC", "name": "Mataveri (Easter Island)",                  "city": "Easter Island","country":"CL","lat": -27.1648,"lng": -109.4218},
    {"iata": "LIM", "name": "Jorge Chavez International",                "city": "Lima",       "country": "PE", "lat": -12.0219,"lng": -77.1143},
    {"iata": "CUZ", "name": "Alejandro Velasco Astete International",    "city": "Cusco",      "country": "PE", "lat": -13.5357,"lng": -71.9389},
    {"iata": "LPB", "name": "El Alto International",                     "city": "La Paz",     "country": "BO", "lat": -16.5133,"lng": -68.1925},
    {"iata": "BOG", "name": "El Dorado International",                   "city": "Bogota",     "country": "CO", "lat": 4.7016,  "lng": -74.1469},
    {"iata": "UIO", "name": "Mariscal Sucre International",              "city": "Quito",      "country": "EC", "lat": -0.1292, "lng": -78.3575},
    {"iata": "GPS", "name": "Seymour (Galapagos)",                       "city": "Baltra",     "country": "EC", "lat": -0.4536, "lng": -90.2659},

    # ---- Oceania ----
    {"iata": "SYD", "name": "Kingsford Smith",                           "city": "Sydney",     "country": "AU", "lat": -33.9399,"lng": 151.1753},
    {"iata": "MEL", "name": "Melbourne (Tullamarine)",                   "city": "Melbourne",  "country": "AU", "lat": -37.6690,"lng": 144.8410},
    {"iata": "BNE", "name": "Brisbane",                                  "city": "Brisbane",   "country": "AU", "lat": -27.3842,"lng": 153.1175},
    {"iata": "PER", "name": "Perth",                                     "city": "Perth",      "country": "AU", "lat": -31.9385,"lng": 115.9670},
    {"iata": "CNS", "name": "Cairns",                                    "city": "Cairns",     "country": "AU", "lat": -16.8858,"lng": 145.7550},
    {"iata": "AYQ", "name": "Ayers Rock (Connellan)",                    "city": "Uluru",      "country": "AU", "lat": -25.1861,"lng": 130.9756},
    {"iata": "AKL", "name": "Auckland",                                  "city": "Auckland",   "country": "NZ", "lat": -37.0082,"lng": 174.7850},
    {"iata": "CHC", "name": "Christchurch",                              "city": "Christchurch","country": "NZ", "lat": -43.4894,"lng": 172.5322},
    {"iata": "ZQN", "name": "Queenstown",                                "city": "Queenstown", "country": "NZ", "lat": -45.0211,"lng": 168.7392},
    {"iata": "NAN", "name": "Nadi International",                        "city": "Nadi",       "country": "FJ", "lat": -17.7554,"lng": 177.4436},
    {"iata": "PPT", "name": "Faa'a International",                       "city": "Papeete",    "country": "PF", "lat": -17.5537,"lng": -149.6067},
]

_BY_IATA: dict[str, dict] = {a["iata"]: a for a in _AIRPORTS}


# Common alternate names / nearby-city searches → best-matching IATA. Extend
# freely; the location search inspects this map after the direct name search.
_ALIASES: dict[str, str] = {
    # ------------------------------------------------------------------
    # India — city renames, states, regions, and famous heritage sites
    # ------------------------------------------------------------------
    "bombay":           "BOM",
    "bengaluru":        "BLR",
    "bangaluru":        "BLR",
    "madras":           "MAA",
    "calcutta":         "CCU",
    "kolkatta":         "CCU",
    "cochin":           "COK",
    "ernakulam":        "COK",
    "trivandrum":       "TRV",
    "thiruvananthapuram":"TRV",
    "gurgaon":          "DEL",
    "gurugram":         "DEL",
    "noida":            "DEL",
    "faridabad":        "DEL",

    # Indian states / regions → nearest hub
    "india":            "DEL",
    "kerala":           "COK",
    "backwaters":       "COK",
    "alleppey":         "COK",
    "alappuzha":        "COK",
    "kumarakom":        "COK",
    "munnar":           "COK",
    "wayanad":          "CCJ",
    "kovalam":          "TRV",
    "varkala":          "TRV",
    "kanyakumari":      "TRV",
    "rajasthan":        "JAI",
    "jaipur":           "JAI",
    "udaipur":          "UDR",
    "jodhpur":          "JDH",
    "jaisalmer":        "JSA",
    "pushkar":          "JAI",
    "ranthambore":      "JAI",
    "ranthambhore":     "JAI",
    "mount abu":        "UDR",
    "rann of kutch":    "AMD",
    "kutch":            "AMD",
    "gujarat":          "AMD",
    "somnath":          "AMD",
    "dwarka":           "AMD",
    "gir":              "AMD",
    "goa":              "GOI",
    "north goa":        "GOI",
    "south goa":        "GOI",
    "panaji":           "GOI",
    "himachal":         "KUU",
    "himachal pradesh": "KUU",
    "manali":           "KUU",
    "kullu":            "KUU",
    "spiti":            "KUU",
    "shimla":           "SLV",
    "kasol":            "KUU",
    "dharamshala":      "KUU",
    "mcleodganj":       "KUU",
    "uttarakhand":      "DED",
    "rishikesh":        "DED",
    "haridwar":         "DED",
    "mussoorie":        "DED",
    "nainital":         "DED",
    "auli":             "DED",
    "valley of flowers":"DED",
    "kedarnath":        "DED",
    "badrinath":        "DED",
    "char dham":        "DED",
    "jim corbett":      "DED",
    "corbett":          "DED",
    "kashmir":          "SXR",
    "srinagar":         "SXR",
    "gulmarg":          "SXR",
    "pahalgam":         "SXR",
    "sonmarg":          "SXR",
    "ladakh":           "IXL",
    "leh":              "IXL",
    "nubra":            "IXL",
    "pangong":          "IXL",
    "kargil":           "IXL",
    "zanskar":          "IXL",
    "punjab":           "ATQ",
    "amritsar":         "ATQ",
    "golden temple":    "ATQ",
    "wagah":            "ATQ",
    "chandigarh":       "IXC",
    "haryana":          "DEL",
    "agra":             "AGR",
    "taj mahal":        "AGR",
    "mathura":          "AGR",
    "vrindavan":        "AGR",
    "fatehpur sikri":   "AGR",
    "uttar pradesh":    "LKO",
    "lucknow":          "LKO",
    "varanasi":         "VNS",
    "banaras":          "VNS",
    "kashi":            "VNS",
    "ayodhya":          "LKO",
    "prayagraj":        "VNS",
    "allahabad":        "VNS",
    "khajuraho":        "HJR",
    "madhya pradesh":   "IDR",
    "indore":           "IDR",
    "bhopal":           "IDR",
    "ujjain":           "IDR",
    "sanchi":           "IDR",
    "orchha":           "HJR",
    "gwalior":          "AGR",
    "chhattisgarh":     "RPR",
    "raipur":           "RPR",
    "odisha":           "BBI",
    "orissa":           "BBI",
    "bhubaneswar":      "BBI",
    "puri":             "BBI",
    "konark":           "BBI",
    "west bengal":      "CCU",
    "kolkata":          "CCU",
    "darjeeling":       "IXB",
    "kalimpong":        "IXB",
    "siliguri":         "IXB",
    "sikkim":           "IXB",
    "gangtok":          "IXB",
    "north east":       "GAU",
    "northeast":        "GAU",
    "assam":            "GAU",
    "guwahati":         "GAU",
    "kaziranga":        "GAU",
    "meghalaya":        "GAU",
    "shillong":         "GAU",
    "cherrapunji":      "GAU",
    "arunachal":        "GAU",
    "arunachal pradesh":"GAU",
    "nagaland":         "GAU",
    "manipur":          "GAU",
    "mizoram":          "GAU",
    "tripura":          "GAU",
    "andaman":          "IXZ",
    "andamans":         "IXZ",
    "nicobar":          "IXZ",
    "havelock":         "IXZ",
    "port blair":       "IXZ",
    "tamil nadu":       "MAA",
    "chennai":          "MAA",
    "mahabalipuram":    "MAA",
    "pondicherry":      "MAA",
    "puducherry":       "MAA",
    "auroville":        "MAA",
    "madurai":          "IXM",
    "rameshwaram":      "IXM",
    "kanchipuram":      "MAA",
    "ooty":             "CJB",
    "coonoor":          "CJB",
    "kodaikanal":       "IXM",
    "coimbatore":       "CJB",
    "karnataka":        "BLR",
    "mysore":           "BLR",
    "mysuru":           "BLR",
    "coorg":            "BLR",
    "kodagu":           "BLR",
    "chikmagalur":      "BLR",
    "hampi":            "BLR",
    "gokarna":          "GOI",
    "mangalore":        "BLR",
    "hyderabad":        "HYD",
    "telangana":        "HYD",
    "andhra pradesh":   "HYD",
    "vizag":            "HYD",
    "visakhapatnam":    "HYD",
    "tirupati":         "TIR",
    "araku":            "HYD",
    "maharashtra":      "BOM",
    "pune":             "PNQ",
    "lonavala":         "PNQ",
    "mahabaleshwar":    "PNQ",
    "ajanta":           "BOM",
    "ellora":           "BOM",
    "aurangabad":       "BOM",
    "shirdi":           "BOM",
    "bihar":            "VNS",
    "patna":            "VNS",
    "bodh gaya":        "VNS",
    "nalanda":          "VNS",
    "jharkhand":        "CCU",

    # ------------------------------------------------------------------
    # East / Southeast Asia
    # ------------------------------------------------------------------
    "kyoto":            "KIX",
    "nara":             "KIX",
    "narita":           "NRT",
    "haneda":           "HND",
    "osaka":            "KIX",
    "hokkaido":         "CTS",
    "sapporo":          "CTS",
    "okinawa":          "OKA",
    "japan":            "NRT",
    "mount fuji":       "HND",
    "fuji":             "HND",
    "hiroshima":        "KIX",
    "korea":            "ICN",
    "south korea":      "ICN",
    "seoul":            "ICN",
    "busan":            "ICN",
    "jeju":             "ICN",
    "china":            "PEK",
    "beijing":          "PEK",
    "great wall":       "PEK",
    "great wall of china":"PEK",
    "forbidden city":   "PEK",
    "shanghai":         "PVG",
    "hong kong":        "HKG",
    "hongkong":         "HKG",
    "macau":            "HKG",
    "taiwan":           "TPE",
    "taipei":           "TPE",
    "singapore":        "SIN",
    "sentosa":          "SIN",
    "thailand":         "BKK",
    "bangkok":          "BKK",
    "phuket":           "HKT",
    "krabi":            "HKT",
    "phi phi":          "HKT",
    "koh samui":        "USM",
    "samui":            "USM",
    "koh phangan":      "USM",
    "chiang mai":       "CNX",
    "chiangmai":        "CNX",
    "chiang rai":       "CNX",
    "pattaya":          "BKK",
    "ayutthaya":        "BKK",
    "malaysia":         "KUL",
    "kuala lumpur":     "KUL",
    "penang":           "KUL",
    "langkawi":         "KUL",
    "borneo":           "KUL",
    "bali":             "DPS",
    "denpasar":         "DPS",
    "ubud":             "DPS",
    "uluwatu":          "DPS",
    "seminyak":         "DPS",
    "canggu":           "DPS",
    "nusa penida":      "DPS",
    "gili":             "DPS",
    "gili islands":     "DPS",
    "lombok":           "DPS",
    "indonesia":        "CGK",
    "jakarta":          "CGK",
    "yogyakarta":       "JOG",
    "borobudur":        "JOG",
    "prambanan":        "JOG",
    "komodo":           "CGK",
    "philippines":      "MNL",
    "manila":           "MNL",
    "cebu":             "CEB",
    "boracay":          "CEB",
    "palawan":          "MNL",
    "el nido":          "MNL",
    "vietnam":          "SGN",
    "ho chi minh":      "SGN",
    "saigon":           "SGN",
    "hanoi":            "HAN",
    "halong":           "HAN",
    "halong bay":       "HAN",
    "hoi an":           "SGN",
    "danang":           "SGN",
    "da nang":          "SGN",
    "sapa":             "HAN",
    "cambodia":         "REP",
    "siem reap":        "REP",
    "angkor":           "REP",
    "angkor wat":       "REP",
    "phnom penh":       "REP",

    # ------------------------------------------------------------------
    # South Asia (India's neighbours)
    # ------------------------------------------------------------------
    "nepal":            "KTM",
    "kathmandu":        "KTM",
    "pokhara":          "KTM",
    "everest":          "KTM",
    "mount everest":    "KTM",
    "annapurna":        "KTM",
    "lumbini":          "KTM",
    "bhutan":           "PBH",
    "paro":             "PBH",
    "thimphu":          "PBH",
    "tigers nest":      "PBH",
    "tiger's nest":     "PBH",
    "sri lanka":        "CMB",
    "srilanka":         "CMB",
    "ceylon":           "CMB",
    "colombo":          "CMB",
    "kandy":            "CMB",
    "sigiriya":         "CMB",
    "galle":            "CMB",
    "ella":             "CMB",
    "maldives":         "MLE",
    "male":             "MLE",
    "bangladesh":       "DAC",
    "dhaka":            "DAC",

    # ------------------------------------------------------------------
    # Middle East
    # ------------------------------------------------------------------
    "uae":              "DXB",
    "united arab emirates":"DXB",
    "dubai":            "DXB",
    "burj khalifa":     "DXB",
    "abu dhabi":        "AUH",
    "sharjah":          "DXB",
    "ras al khaimah":   "DXB",
    "qatar":            "DOH",
    "doha":             "DOH",
    "saudi":            "RUH",
    "saudi arabia":     "RUH",
    "riyadh":           "RUH",
    "jeddah":           "JED",
    "makkah":           "JED",
    "mecca":            "JED",
    "medina":           "JED",
    "israel":           "TLV",
    "tel aviv":         "TLV",
    "jerusalem":        "TLV",
    "jordan":           "AMM",
    "amman":            "AMM",
    "petra":            "AMM",
    "wadi rum":         "AMM",
    "dead sea":         "AMM",
    "lebanon":          "BEY",
    "beirut":           "BEY",
    "egypt":            "CAI",
    "cairo":            "CAI",
    "pyramids":         "CAI",
    "great pyramids":   "CAI",
    "giza":             "CAI",
    "luxor":            "CAI",
    "aswan":            "CAI",
    "sharm el sheikh":  "HRG",
    "hurghada":         "HRG",
    "red sea":          "HRG",

    # ------------------------------------------------------------------
    # Europe
    # ------------------------------------------------------------------
    "france":           "CDG",
    "paris":            "CDG",
    "eiffel tower":     "CDG",
    "louvre":           "CDG",
    "versailles":       "CDG",
    "provence":         "NCE",
    "nice":             "NCE",
    "cannes":           "NCE",
    "monaco":           "NCE",
    "french riviera":   "NCE",
    "cote d'azur":      "NCE",
    "uk":               "LHR",
    "united kingdom":   "LHR",
    "england":          "LHR",
    "britain":          "LHR",
    "london":           "LHR",
    "scotland":         "EDI",
    "edinburgh":        "EDI",
    "highlands":        "EDI",
    "ireland":          "DUB",
    "dublin":           "DUB",
    "netherlands":      "AMS",
    "holland":          "AMS",
    "amsterdam":        "AMS",
    "belgium":          "BRU",
    "brussels":         "BRU",
    "bruges":           "BRU",
    "germany":          "FRA",
    "frankfurt":        "FRA",
    "berlin":           "BER",
    "munich":           "MUC",
    "bavaria":          "MUC",
    "neuschwanstein":   "MUC",
    "black forest":     "MUC",
    "austria":          "VIE",
    "vienna":           "VIE",
    "salzburg":         "VIE",
    "hallstatt":        "VIE",
    "czech republic":   "PRG",
    "czechia":          "PRG",
    "prague":           "PRG",
    "hungary":          "BUD",
    "budapest":         "BUD",
    "poland":           "WAW",
    "warsaw":           "WAW",
    "krakow":           "WAW",
    "switzerland":      "ZRH",
    "zurich":           "ZRH",
    "geneva":           "GVA",
    "swiss alps":       "ZRH",
    "swiss-alps":       "ZRH",
    "interlaken":       "ZRH",
    "zermatt":          "ZRH",
    "matterhorn":       "ZRH",
    "jungfrau":         "ZRH",
    "lucerne":          "ZRH",
    "spain":            "MAD",
    "madrid":           "MAD",
    "barcelona":        "BCN",
    "sagrada familia":  "BCN",
    "seville":          "MAD",
    "granada":          "AGP",
    "malaga":           "AGP",
    "costa del sol":    "AGP",
    "ibiza":            "BCN",
    "mallorca":         "BCN",
    "canary islands":   "AGP",
    "portugal":         "LIS",
    "lisbon":           "LIS",
    "porto":            "LIS",
    "algarve":          "LIS",
    "italy":            "FCO",
    "rome":             "FCO",
    "vatican":          "FCO",
    "colosseum":        "FCO",
    "milan":            "MXP",
    "venice":           "VCE",
    "florence":         "FLR",
    "tuscany":          "FLR",
    "pisa":             "FLR",
    "cinque terre":     "FLR",
    "naples":           "NAP",
    "pompeii":          "NAP",
    "amalfi":           "NAP",
    "amalfi coast":     "NAP",
    "amalfi-coast":     "NAP",
    "capri":            "NAP",
    "sicily":           "PMO",
    "palermo":          "PMO",
    "sardinia":         "FCO",
    "greece":           "ATH",
    "athens":           "ATH",
    "acropolis":        "ATH",
    "santorini":        "JTR",
    "thira":            "JTR",
    "oia":              "JTR",
    "mykonos":          "JTR",
    "crete":            "HER",
    "heraklion":        "HER",
    "turkey":           "IST",
    "istanbul":         "IST",
    "hagia sophia":     "IST",
    "blue mosque":      "IST",
    "bosphorus":        "IST",
    "cappadocia":       "ASR",
    "goreme":           "ASR",
    "pamukkale":        "AYT",
    "antalya":          "AYT",
    "iceland":          "KEF",
    "reykjavik":        "KEF",
    "blue lagoon":      "KEF",
    "golden circle":    "KEF",
    "norway":           "OSL",
    "oslo":             "OSL",
    "bergen":           "OSL",
    "fjords":           "OSL",
    "tromso":           "TOS",
    "lofoten":          "TOS",
    "northern lights":  "KEF",
    "aurora":           "KEF",
    "aurora borealis":  "KEF",
    "sweden":           "ARN",
    "stockholm":        "ARN",
    "denmark":          "CPH",
    "copenhagen":       "CPH",
    "finland":          "HEL",
    "helsinki":         "HEL",
    "lapland":          "HEL",
    "rovaniemi":        "HEL",
    "santa claus":      "HEL",

    # ------------------------------------------------------------------
    # Africa
    # ------------------------------------------------------------------
    "south africa":     "JNB",
    "johannesburg":     "JNB",
    "cape town":        "CPT",
    "capetown":         "CPT",
    "kruger":           "JNB",
    "kruger national park":"JNB",
    "garden route":     "CPT",
    "safari":           "NBO",
    "kenya":            "NBO",
    "nairobi":          "NBO",
    "maasai mara":      "NBO",
    "masai mara":       "NBO",
    "mombasa":          "MBA",
    "diani":            "MBA",
    "tanzania":         "JRO",
    "kilimanjaro":      "JRO",
    "mount kilimanjaro":"JRO",
    "serengeti":        "JRO",
    "ngorongoro":       "JRO",
    "arusha":           "JRO",
    "zanzibar":         "ZNZ",
    "morocco":          "RAK",
    "marrakech":        "RAK",
    "marrakesh":        "RAK",
    "casablanca":       "CMN",
    "fez":              "RAK",
    "chefchaouen":      "CMN",
    "sahara":           "RAK",
    "ethiopia":         "ADD",
    "addis ababa":      "ADD",
    "nigeria":          "LOS",
    "lagos":            "LOS",
    "zimbabwe":         "VFA",
    "victoria falls":   "VFA",
    "mauritius":        "MRU",
    "port louis":       "MRU",
    "seychelles":       "SEZ",
    "mahe":             "SEZ",

    # ------------------------------------------------------------------
    # North America
    # ------------------------------------------------------------------
    "usa":              "JFK",
    "us":               "JFK",
    "united states":    "JFK",
    "america":          "JFK",
    "new york":         "JFK",
    "nyc":              "JFK",
    "manhattan":        "JFK",
    "brooklyn":         "JFK",
    "statue of liberty":"JFK",
    "times square":     "JFK",
    "central park":     "JFK",
    "newark":           "EWR",
    "los angeles":      "LAX",
    "hollywood":        "LAX",
    "california":       "LAX",
    "san diego":        "LAX",
    "san francisco":    "SFO",
    "sfo":              "SFO",
    "napa":             "SFO",
    "yosemite":         "SFO",
    "seattle":          "SEA",
    "chicago":          "ORD",
    "miami":            "MIA",
    "florida":          "MCO",
    "orlando":          "MCO",
    "disney world":     "MCO",
    "everglades":       "MIA",
    "key west":         "MIA",
    "las vegas":        "LAS",
    "vegas":            "LAS",
    "grand canyon":     "LAS",
    "boston":           "BOS",
    "new england":      "BOS",
    "washington":       "IAD",
    "dc":               "IAD",
    "hawaii":           "HNL",
    "honolulu":         "HNL",
    "maui":             "HNL",
    "kauai":            "HNL",
    "big island":       "HNL",
    "alaska":           "ANC",
    "anchorage":        "ANC",
    "denali":           "ANC",
    "canada":           "YYZ",
    "toronto":          "YYZ",
    "niagara":          "YYZ",
    "niagara falls":    "YYZ",
    "vancouver":        "YVR",
    "banff":            "YVR",
    "whistler":         "YVR",
    "rocky mountains":  "YVR",
    "montreal":         "YUL",
    "quebec":           "YUL",
    "mexico":           "MEX",
    "mexico city":      "MEX",
    "cancun":           "CUN",
    "riviera maya":     "CUN",
    "tulum":            "CUN",
    "playa del carmen": "CUN",
    "chichen itza":     "CUN",
    "cozumel":          "CUN",
    "cuba":             "HAV",
    "havana":           "HAV",
    "puerto rico":      "SJU",
    "san juan":         "SJU",

    # ------------------------------------------------------------------
    # South America
    # ------------------------------------------------------------------
    "brazil":           "GRU",
    "sao paulo":        "GRU",
    "rio":              "GIG",
    "rio de janeiro":   "GIG",
    "amazon":           "MAO",
    "manaus":           "MAO",
    "iguazu":           "IGR",
    "iguazu falls":     "IGR",
    "argentina":        "EZE",
    "buenos aires":     "EZE",
    "patagonia":        "EZE",
    "bariloche":        "EZE",
    "chile":            "SCL",
    "santiago":         "SCL",
    "atacama":          "SCL",
    "torres del paine": "SCL",
    "easter island":    "IPC",
    "peru":             "LIM",
    "lima":             "LIM",
    "cusco":            "CUZ",
    "cuzco":            "CUZ",
    "machu picchu":     "CUZ",
    "machu-picchu":     "CUZ",
    "sacred valley":    "CUZ",
    "rainbow mountain": "CUZ",
    "bolivia":          "LPB",
    "la paz":           "LPB",
    "salar de uyuni":   "LPB",
    "uyuni":            "LPB",
    "colombia":         "BOG",
    "bogota":           "BOG",
    "cartagena":        "BOG",
    "medellin":         "BOG",
    "ecuador":          "UIO",
    "quito":            "UIO",
    "galapagos":        "GPS",

    # ------------------------------------------------------------------
    # Oceania
    # ------------------------------------------------------------------
    "australia":        "SYD",
    "sydney":           "SYD",
    "opera house":      "SYD",
    "melbourne":        "MEL",
    "brisbane":         "BNE",
    "gold coast":       "BNE",
    "perth":            "PER",
    "cairns":           "CNS",
    "great barrier reef":"CNS",
    "barrier reef":     "CNS",
    "port douglas":     "CNS",
    "uluru":            "AYQ",
    "ayers rock":       "AYQ",
    "kangaroo island":  "SYD",
    "tasmania":         "MEL",
    "outback":          "AYQ",
    "new zealand":      "AKL",
    "newzealand":       "AKL",
    "auckland":         "AKL",
    "queenstown":       "ZQN",
    "milford sound":    "ZQN",
    "fiordland":        "ZQN",
    "christchurch":     "CHC",
    "hobbiton":         "AKL",
    "rotorua":          "AKL",
    "wellington":       "AKL",
    "fiji":             "NAN",
    "nadi":             "NAN",
    "tahiti":           "PPT",
    "bora bora":        "PPT",
    "borabora":         "PPT",
    "french polynesia": "PPT",
    "papeete":          "PPT",
    "moorea":           "PPT",
}


# Carrier codes used by the mock ranker. Each route seeds a permutation.
_CARRIERS: list[tuple[str, str]] = [
    ("AI", "Air India"),
    ("6E", "IndiGo"),
    ("EK", "Emirates"),
    ("QR", "Qatar Airways"),
    ("SQ", "Singapore Airlines"),
    ("JL", "Japan Airlines"),
    ("BA", "British Airways"),
    ("AF", "Air France"),
]


# --- helpers ---------------------------------------------------------------


def _haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dphi = math.radians(b["lat"] - a["lat"])
    dl = math.radians(b["lng"] - a["lng"])
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def _seed_int(*parts: str) -> int:
    """Stable hash → int, so the same route always produces the same offers."""
    h = hashlib.blake2b(("|".join(parts)).encode(), digest_size=4).digest()
    return int.from_bytes(h, "big")


def _iso_duration(mins: int) -> str:
    h, m = divmod(mins, 60)
    return f"PT{h}H{m}M"


# --- endpoints -------------------------------------------------------------


def _hit(a: dict) -> LocationHit:
    return LocationHit(
        name=a["name"],
        iata_code=a["iata"],
        sub_type="AIRPORT",
        city_name=a["city"],
        country_code=a["country"],
        geo={"latitude": a["lat"], "longitude": a["lng"]},
    )


def mock_locations(keyword: str) -> LocationSearchResponse:
    key = keyword.strip().lower()
    hits: list[LocationHit] = []
    seen: set[str] = set()

    # 1. direct name/city/IATA/country match
    for a in _AIRPORTS:
        if (key in a["iata"].lower()
                or key in a["name"].lower()
                or key in a["city"].lower()
                or key in a["country"].lower()):
            if a["iata"] not in seen:
                hits.append(_hit(a))
                seen.add(a["iata"])

    # 2. alias fallback so 'Kyoto' / 'Bombay' / 'Bali' resolve
    if not hits:
        iata = _ALIASES.get(key)
        if iata and iata in _BY_IATA and iata not in seen:
            hits.append(_hit(_BY_IATA[iata]))
            seen.add(iata)

    return LocationSearchResponse(results=hits[:10])


def resolve_iata_mock(keyword: str) -> str | None:
    """Best-effort match — used when someone passes a `city` name instead
    of an IATA code. Airport IATA codes win over city name matches."""
    hits = mock_locations(keyword).results
    return hits[0].iata_code if hits else None


def _make_flight_offer(
    seed: int,
    origin: dict,
    dest: dict,
    departure_date: str,
    return_date: str | None,
    currency: str,
    idx: int,
) -> FlightOffer:
    # Deterministic carrier + timing based on seed + index
    carrier_code, _carrier_name = _CARRIERS[(seed + idx) % len(_CARRIERS)]
    dep_hour = 5 + ((seed >> (idx * 3)) & 0xF) % 18   # 05:00 - 22:00
    dep_min = ((seed >> (idx * 5)) & 0x3) * 15         # 00/15/30/45

    dist_km = max(300.0, _haversine_km(origin, dest))
    # Rough flight time model: 90 km/h taxi + ~800 km/h cruise + 45m overhead
    cruise_mins = int(dist_km / 800.0 * 60)
    total_mins = 45 + cruise_mins
    stops = 1 if dist_km > 6000 and (seed + idx) % 3 == 0 else 0
    if stops:
        total_mins += 90  # layover

    dep_dt = datetime.fromisoformat(f"{departure_date}T{dep_hour:02d}:{dep_min:02d}:00+00:00")
    arr_dt = dep_dt + timedelta(minutes=total_mins)

    # Segments
    segments: list[FlightSegment] = []
    flight_no = str(100 + ((seed + idx * 7) % 900))
    if stops == 0:
        segments.append(FlightSegment(
            departure_iata=origin["iata"],
            departure_at=dep_dt.isoformat(),
            arrival_iata=dest["iata"],
            arrival_at=arr_dt.isoformat(),
            carrier_code=carrier_code,
            number=flight_no,
            duration=_iso_duration(total_mins),
            stops=0,
        ))
    else:
        # Layover through a hub between origin and destination
        hub_iata = "DXB" if origin["country"] != "IN" or dest["country"] != "IN" else "DEL"
        hub = _BY_IATA.get(hub_iata, _BY_IATA["DXB"])
        leg1_mins = int(_haversine_km(origin, hub) / 800.0 * 60) + 30
        leg2_mins = int(_haversine_km(hub, dest) / 800.0 * 60) + 30
        mid1_arr = dep_dt + timedelta(minutes=leg1_mins)
        mid2_dep = mid1_arr + timedelta(minutes=90)
        seg_arr = mid2_dep + timedelta(minutes=leg2_mins)
        segments.append(FlightSegment(
            departure_iata=origin["iata"], departure_at=dep_dt.isoformat(),
            arrival_iata=hub_iata, arrival_at=mid1_arr.isoformat(),
            carrier_code=carrier_code, number=flight_no, duration=_iso_duration(leg1_mins),
            stops=0,
        ))
        segments.append(FlightSegment(
            departure_iata=hub_iata, departure_at=mid2_dep.isoformat(),
            arrival_iata=dest["iata"], arrival_at=seg_arr.isoformat(),
            carrier_code=carrier_code, number=str(int(flight_no) + 1), duration=_iso_duration(leg2_mins),
            stops=0,
        ))

    itineraries = [FlightItinerary(duration=_iso_duration(total_mins), segments=segments)]

    if return_date:
        ret_dt = datetime.fromisoformat(f"{return_date}T{((dep_hour + 4) % 22):02d}:{dep_min:02d}:00+00:00")
        ret_arr = ret_dt + timedelta(minutes=total_mins)
        return_seg = FlightSegment(
            departure_iata=dest["iata"], departure_at=ret_dt.isoformat(),
            arrival_iata=origin["iata"], arrival_at=ret_arr.isoformat(),
            carrier_code=carrier_code, number=str(int(flight_no) + 500),
            duration=_iso_duration(total_mins), stops=0,
        )
        itineraries.append(FlightItinerary(duration=_iso_duration(total_mins), segments=[return_seg]))

    # Price model: distance-based + carrier premium + idx variance, in the
    # requested currency. INR base; other currencies scaled at rough rates.
    base_price_inr = 2200 + dist_km * 6.0 + ((seed + idx * 13) % 4000)
    if stops:
        base_price_inr *= 0.85  # 1-stop discount
    if return_date:
        base_price_inr *= 1.9   # round trip
    fx = {"INR": 1.0, "USD": 1 / 83.0, "EUR": 1 / 90.0, "GBP": 1 / 105.0, "JPY": 1 / 0.56}.get(currency, 1.0)
    total = round(base_price_inr * fx, 2)

    return FlightOffer(
        id=f"MOCK-{seed & 0xFFFF:04X}-{idx}",
        currency=currency,
        total=f"{total:.2f}",
        itineraries=itineraries,
    )


def mock_flights(
    origin_iata: str,
    destination_iata: str,
    departure_date: str,
    return_date: str | None,
    currency: str,
    max_offers: int,
) -> FlightsResponse:
    origin = _BY_IATA.get(origin_iata.upper())
    dest = _BY_IATA.get(destination_iata.upper())
    if origin is None or dest is None:
        # Unknown airport codes — synthesize a minimal stub so the endpoint
        # still returns something rather than 404.
        origin = origin or {"iata": origin_iata.upper(), "lat": 0.0, "lng": 0.0, "city": origin_iata, "country": "XX"}
        dest = dest or {"iata": destination_iata.upper(), "lat": 20.0, "lng": 20.0, "city": destination_iata, "country": "XX"}

    seed = _seed_int(origin["iata"], dest["iata"], departure_date, return_date or "one-way")
    offers = [
        _make_flight_offer(seed, origin, dest, departure_date, return_date, currency, i)
        for i in range(min(max_offers, 5))
    ]
    # Sort cheapest first — Amadeus doesn't but users expect it in demos.
    offers.sort(key=lambda o: float(o.total))
    return FlightsResponse(origin=origin["iata"], destination=dest["iata"], offers=offers)


# --- hotels ----------------------------------------------------------------


_HOTEL_CHAINS: list[tuple[str, tuple[int, int]]] = [
    ("Grand Meridian", (6500, 12000)),
    ("Vista Residences", (3500, 6800)),
    ("Ivy Boutique", (4200, 8500)),
    ("The Traveller's Rest", (1800, 3200)),
    ("Central Heights", (5500, 9500)),
]


def mock_hotels(
    city_code: str,
    check_in: str | None,
    check_out: str | None,
    adults: int,
) -> HotelsResponse:
    city = _BY_IATA.get(city_code.upper()) or {"city": city_code.upper(), "iata": city_code.upper()}
    seed = _seed_int(city_code.upper(), check_in or "", check_out or "", str(adults))

    hotels_list: list[HotelListItem] = []
    offers_list: list[HotelOfferGroup] = []

    for i, (chain, (low, high)) in enumerate(_HOTEL_CHAINS):
        hotel_id = f"MOCK{city_code.upper()}{i:02d}"
        hotel_name = f"{chain} {city.get('city', city_code.upper())}"
        hotels_list.append(HotelListItem(
            hotel_id=hotel_id,
            name=hotel_name,
            iata_code=city_code.upper(),
            geo={"latitude": city.get("lat", 0.0) + i * 0.005, "longitude": city.get("lng", 0.0) + i * 0.005},
        ))

        # Deterministic nightly rate per (city, hotel, dates)
        span = high - low
        nightly = low + ((seed >> (i * 4)) % span)
        offer_price = HotelOfferPrice(currency="INR", total=f"{nightly * max(1, adults) * 0.9:.2f}", base=f"{nightly:.2f}")
        offers_list.append(HotelOfferGroup(
            hotel_id=hotel_id,
            hotel_name=hotel_name,
            available=True,
            offers=[HotelOfferItem(
                id=f"{hotel_id}-OFR",
                check_in_date=check_in or "",
                check_out_date=check_out or "",
                room_description=["Deluxe Twin", "King Suite", "Family Room", "Standard Double", "Executive Suite"][i % 5],
                price=offer_price,
            )],
        ))

    offers_list.sort(key=lambda g: float(g.offers[0].price.total) if g.offers else 0)
    return HotelsResponse(city_code=city_code.upper(), hotels=hotels_list, offers=offers_list)
