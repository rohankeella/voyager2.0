"""Seed script — populates a demo provider, ~30 experiences across four
cities, and one traveler. Run with:

    python -m app.seed
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models.capacity import (
    CapacityMetric,
    CapacitySourceKind,
    Nudge,
    NudgeKind,
    Zone,
    ZoneEvent,
)
from app.models.editorial import StoryPost, StoryUpdate, StoryUpdateKind
from app.models.experience import Experience, ExperienceCategory, OperatingHour
from app.models.graph import (
    EdgeKind,
    ItineraryEdge,
    ItineraryNode,
    NodeKind,
    RefundClass,
)
from app.models.itinerary import Itinerary
from app.models.provider import Provider
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.editorial import recompute_post_metadata
from app.services.slug import slugify


# Anchor points for four demo cities. Small offsets keep experiences visually
# distinct on a map without being wildly wrong for real-world placement.
CITIES = {
    "Bali":     {"lat": -8.4095,  "lng": 115.1889, "country": "Indonesia"},
    "Kyoto":    {"lat": 35.0116,  "lng": 135.7681, "country": "Japan"},
    "Paris":    {"lat": 48.8566,  "lng": 2.3522,   "country": "France"},
    "Mumbai":   {"lat": 19.0760,  "lng": 72.8777,  "country": "India"},
}


def _wide_hours(days: range = range(0, 7)) -> list[dict]:
    return [{"day_of_week": d, "open_time": "09:00", "close_time": "22:00"} for d in days]


SEED_EXPERIENCES: list[dict] = [
    # ---- Bali -----------------------------------------------------------
    {"title": "Ubud Rice Terrace Sunrise Walk", "city": "Bali", "category": "OUTDOOR",
     "base_cost": 1200, "duration_mins": 150, "tags": ["hiking", "photography", "wildlife"],
     "hours": [{"day_of_week": d, "open_time": "05:30", "close_time": "10:00"} for d in range(7)],
     "attributes": {"good_for": ["solo", "couple", "friends"], "accessibility": []}},
    {"title": "Seminyak Beach Sunset Yoga", "city": "Bali", "category": "OUTDOOR",
     "base_cost": 800, "duration_mins": 75, "tags": ["beaches", "photography"],
     "hours": [{"day_of_week": d, "open_time": "16:00", "close_time": "19:00"} for d in range(7)]},
    {"title": "Warung Babi Guling Tasting", "city": "Bali", "category": "FOOD",
     "base_cost": 900, "duration_mins": 90, "tags": ["food-tours"],
     "hours": _wide_hours()},
    {"title": "Batik Making Workshop", "city": "Bali", "category": "WORKSHOP",
     "base_cost": 1800, "duration_mins": 180, "tags": ["museums", "photography"],
     "hours": [{"day_of_week": d, "open_time": "10:00", "close_time": "16:00"} for d in range(0, 6)]},
    {"title": "Kuta Nightlife Crawl", "city": "Bali", "category": "NIGHTLIFE",
     "base_cost": 2200, "duration_mins": 210, "tags": ["nightlife", "food-tours"],
     "hours": [{"day_of_week": d, "open_time": "21:00", "close_time": "23:59"} for d in range(7)]},
    {"title": "Uluwatu Temple Kecak Fire Dance", "city": "Bali", "category": "CULTURE",
     "base_cost": 1500, "duration_mins": 120, "tags": ["historical-places", "photography", "festivals"],
     "hours": [{"day_of_week": d, "open_time": "17:00", "close_time": "20:00"} for d in range(7)]},

    # ---- Kyoto ---------------------------------------------------------
    {"title": "Fushimi Inari Torii Hike", "city": "Kyoto", "category": "OUTDOOR",
     "base_cost": 0, "duration_mins": 180, "tags": ["hiking", "photography", "historical-places"],
     "hours": []},  # 24/7
    {"title": "Kyoto Kaiseki Dinner", "city": "Kyoto", "category": "FOOD",
     "base_cost": 6500, "duration_mins": 150, "tags": ["food-tours"],
     "hours": [{"day_of_week": d, "open_time": "17:30", "close_time": "22:00"} for d in range(7)]},
    {"title": "Nishiki Market Food Tour", "city": "Kyoto", "category": "FOOD",
     "base_cost": 3500, "duration_mins": 150, "tags": ["food-tours", "shopping"],
     "hours": [{"day_of_week": d, "open_time": "10:00", "close_time": "17:00"} for d in range(7)]},
    {"title": "Tea Ceremony Experience — Gion", "city": "Kyoto", "category": "CULTURE",
     "base_cost": 3000, "duration_mins": 60, "tags": ["museums", "historical-places"],
     "hours": [{"day_of_week": d, "open_time": "10:00", "close_time": "18:00"} for d in range(7)]},
    {"title": "Arashiyama Bamboo Grove Cycling", "city": "Kyoto", "category": "OUTDOOR",
     "base_cost": 1400, "duration_mins": 180, "tags": ["photography", "road-trips"],
     "hours": _wide_hours()},
    {"title": "Pontocho Alley Sake Bars", "city": "Kyoto", "category": "NIGHTLIFE",
     "base_cost": 2800, "duration_mins": 150, "tags": ["nightlife", "food-tours"],
     "hours": [{"day_of_week": d, "open_time": "19:00", "close_time": "23:59"} for d in range(7)]},
    {"title": "Kinkaku-ji Temple Guided Tour", "city": "Kyoto", "category": "CULTURE",
     "base_cost": 500, "duration_mins": 90, "tags": ["museums", "historical-places", "photography"],
     "hours": [{"day_of_week": d, "open_time": "09:00", "close_time": "17:00"} for d in range(7)]},

    # ---- Paris ---------------------------------------------------------
    {"title": "Louvre Skip-the-Line", "city": "Paris", "category": "CULTURE",
     "base_cost": 2500, "duration_mins": 180, "tags": ["museums", "historical-places"],
     "hours": [{"day_of_week": d, "open_time": "09:00", "close_time": "18:00"} for d in range(7) if d != 1]},
    {"title": "Seine Sunset River Cruise", "city": "Paris", "category": "CULTURE",
     "base_cost": 2200, "duration_mins": 75, "tags": ["photography"],
     "hours": [{"day_of_week": d, "open_time": "18:00", "close_time": "22:30"} for d in range(7)]},
    {"title": "Le Marais Food Walking Tour", "city": "Paris", "category": "FOOD",
     "base_cost": 4200, "duration_mins": 180, "tags": ["food-tours"],
     "hours": [{"day_of_week": d, "open_time": "11:00", "close_time": "16:00"} for d in range(7)]},
    {"title": "Macaron Baking Workshop", "city": "Paris", "category": "WORKSHOP",
     "base_cost": 5500, "duration_mins": 150, "tags": ["food-tours"],
     "hours": [{"day_of_week": d, "open_time": "10:00", "close_time": "17:00"} for d in range(1, 6)]},
    {"title": "Montmartre Cabaret Evening", "city": "Paris", "category": "NIGHTLIFE",
     "base_cost": 8500, "duration_mins": 180, "tags": ["nightlife"],
     "hours": [{"day_of_week": d, "open_time": "20:00", "close_time": "23:59"} for d in range(7)]},
    {"title": "Musée d'Orsay Impressionist Tour", "city": "Paris", "category": "CULTURE",
     "base_cost": 1900, "duration_mins": 120, "tags": ["museums", "photography"],
     "hours": [{"day_of_week": d, "open_time": "09:30", "close_time": "18:00"} for d in range(7) if d != 0]},

    # ---- Mumbai --------------------------------------------------------
    {"title": "Bandra Street Art Photo Walk", "city": "Mumbai", "category": "CULTURE",
     "base_cost": 400, "duration_mins": 120, "tags": ["photography", "historical-places"],
     "hours": _wide_hours()},
    {"title": "Mohammed Ali Road Iftar Food Trail", "city": "Mumbai", "category": "FOOD",
     "base_cost": 700, "duration_mins": 150, "tags": ["food-tours"],
     "hours": [{"day_of_week": d, "open_time": "18:00", "close_time": "23:00"} for d in range(7)]},
    {"title": "Kanheri Caves Trek", "city": "Mumbai", "category": "OUTDOOR",
     "base_cost": 500, "duration_mins": 240, "tags": ["hiking", "trekking", "historical-places"],
     "hours": [{"day_of_week": d, "open_time": "07:30", "close_time": "17:00"} for d in range(7)]},
    {"title": "Bollywood Dance Workshop", "city": "Mumbai", "category": "WORKSHOP",
     "base_cost": 1200, "duration_mins": 90, "tags": ["museums"],
     "hours": [{"day_of_week": d, "open_time": "10:00", "close_time": "19:00"} for d in range(0, 6)]},
    {"title": "Marine Drive Night Photography", "city": "Mumbai", "category": "OUTDOOR",
     "base_cost": 0, "duration_mins": 90, "tags": ["photography", "nightlife"],
     "hours": [{"day_of_week": d, "open_time": "19:00", "close_time": "23:59"} for d in range(7)]},
    {"title": "Gateway of India Heritage Tour", "city": "Mumbai", "category": "CULTURE",
     "base_cost": 300, "duration_mins": 90, "tags": ["historical-places", "photography"],
     "hours": _wide_hours()},
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Demo traveler
        traveler = db.execute(select(User).where(User.email == "traveler@voyager.dev")).scalar_one_or_none()
        if not traveler:
            traveler = User(
                email="traveler@voyager.dev",
                password_hash=hash_password("voyager123"),
                full_name="Ava Traveler",
                country="IN",
                role=UserRole.TRAVELER,
                preferences={
                    "activities": ["food-tours", "photography", "museums"],
                    "priorities": ["food", "culture"],
                    "tripStyle": "couple",
                    "customDailyBudget": 5000,
                },
            )
            db.add(traveler)
            print("+ traveler traveler@voyager.dev / voyager123")

        # Demo provider account + profile
        provider_user = db.execute(select(User).where(User.email == "provider@voyager.dev")).scalar_one_or_none()
        if not provider_user:
            provider_user = User(
                email="provider@voyager.dev",
                password_hash=hash_password("voyager123"),
                full_name="Local Guides Co.",
                country="IN",
                role=UserRole.PROVIDER,
            )
            db.add(provider_user)
            db.flush()
            print("+ provider provider@voyager.dev / voyager123")

        provider = db.execute(select(Provider).where(Provider.user_id == provider_user.id)).scalar_one_or_none()
        if not provider:
            provider = Provider(
                user_id=provider_user.id,
                business_name="Local Guides Co.",
                contact_email="hello@localguides.dev",
                description="Curated tours across Bali, Kyoto, Paris and Mumbai.",
            )
            db.add(provider)
            db.flush()

        # Experiences (idempotent on slug)
        added = 0
        for spec in SEED_EXPERIENCES:
            slug = slugify(f"{spec['city']}-{spec['title']}")
            existing = db.execute(select(Experience).where(Experience.slug == slug)).scalar_one_or_none()
            if existing:
                continue
            city = CITIES[spec["city"]]
            exp = Experience(
                provider_id=provider.id,
                title=spec["title"],
                slug=slug,
                description=spec.get("description"),
                category=ExperienceCategory(spec["category"]),
                base_cost=spec["base_cost"],
                currency="INR",
                duration_mins=spec["duration_mins"],
                lat=city["lat"] + (hash(slug) % 100) * 0.0004,
                lng=city["lng"] + (hash(slug + "x") % 100) * 0.0004,
                city=spec["city"],
                country=city["country"],
                capacity_max=100,
                seats_available=100,
                attributes=spec.get("attributes", {}),
                interest_tags=spec["tags"],
            )
            for h in spec["hours"]:
                exp.hours.append(OperatingHour(**h))
            db.add(exp)
            added += 1

        db.commit()
        print(f"+ {added} experiences seeded")

        _seed_capacity(db)
        _seed_editorial(db, provider)
        _seed_dependency_graph(db, traveler)


def _seed_editorial(db, provider: Provider) -> None:
    """P4 seed: three story posts with parseable #tags in-body and a couple
    of adaptive updates to demonstrate F-24."""
    author = db.execute(select(User).where(User.id == provider.user_id)).scalar_one()
    now = datetime.now(timezone.utc)

    # A brand-new post with zero reviews but strong narrative + tag alignment
    # — demonstrates F-22 (can rank high despite being new).
    posts = [
        {
            "title": "Rainy afternoons in Gion, quietly",
            "summary": "When the Kyoto rain rolls in, the tourist crowds thin and Gion turns into a private theatre of umbrellas and lantern light.",
            "cover_image_url": "https://images.unsplash.com/photo-1528360983277-13d401cdc186?auto=format&fit=crop&w=1600&q=80",
            "city": "Kyoto",
            "days_old": 0,
            "body_md": """# The Gion nobody photographs

Every guidebook shows you Gion at golden hour. Come at 3pm on a wet Tuesday and the same
lanes empty out — the machiya houses lean in a little, the stone paving turns the colour of
tea, and the tea houses smell like woodsmoke and rain.

This is a **#RainyDayFriendly** afternoon, not a landmark tour. Duck into the ceramic
studio near Yasaka, order the tasting flight at the standing-only sake bar off Hanamikoji,
and finish with a bowl of yudofu somewhere small enough that the chef pours the broth
himself.

Tips:

- Bring cash. The best three shops here still don't take cards.
- Umbrella > raincoat. You'll be in and out of very small doorways.
- #Foodie #DateNight — reservations tighten after 6pm even in rain.
""",
        },
        {
            "title": "Under ₹700: a full day in Arashiyama",
            "summary": "Bamboo grove, temple gardens, riverside soba — all doable on a backpacker budget.",
            "cover_image_url": "https://images.unsplash.com/photo-1528164344705-47542687000d?auto=format&fit=crop&w=1600&q=80",
            "city": "Kyoto",
            "days_old": 30,
            "body_md": """A day in Arashiyama that respects your wallet.

Skip the tourist cable car and start at the north end of the bamboo path early —
you'll have the shafts of light to yourself. Onward to the moss gardens at Gio-ji
(entry is a few hundred yen), then loop back for a bowl of hand-cut soba at one of
the riverside stalls.

Everything below is walkable. Nothing on this list is over ₹700 for one.

#Budget #Outdoors #OffTheBeatenPath #SoloFriendly
""",
        },
        {
            "title": "Mumbai after sunset, minus the crush",
            "summary": "Marine Drive, Bandra art walls, and a hidden Iranian cafe — a slower evening in a fast city.",
            "cover_image_url": "https://images.unsplash.com/photo-1595658658481-d53d3f999875?auto=format&fit=crop&w=1600&q=80",
            "city": "Mumbai",
            "days_old": 3,
            "body_md": """A three-stop evening that lets Mumbai come to you.

Start at the Marine Drive curve just as the string lights come on. Walk north, no
particular pace, to the Bandra murals — the artist puts up new panels every couple
of months and the alleys behind Chapel Road are safe well into the night. Cap it
with cutting chai at the last unmodernised Iranian cafe in Fort.

#DateNight #Foodie #HiddenGem — brings the city down from a sprint to a walk.
""",
        },
    ]

    for spec in posts:
        slug = slugify(spec["title"])
        if db.execute(select(StoryPost).where(StoryPost.slug == slug)).scalar_one_or_none():
            continue
        published_at = now - timedelta(days=spec["days_old"])
        post = StoryPost(
            author_id=author.id,
            provider_id=provider.id,
            title=spec["title"],
            slug=slug,
            summary=spec["summary"],
            body_md=spec["body_md"],
            cover_image_url=spec["cover_image_url"],
            city=spec["city"],
            published=True,
            published_at=published_at,
            created_at=published_at,
        )
        recompute_post_metadata(post)
        db.add(post)
        db.flush()

        # F-24 sample updates on the first post
        if slug.startswith("rainy-afternoons"):
            db.add(StoryUpdate(
                post_id=post.id,
                kind=StoryUpdateKind.WEATHER,
                message="Rain alert: this route is at its best right now — indoor spots have short queues.",
                condition={"weather": "rain"},
            ))
            db.add(StoryUpdate(
                post_id=post.id,
                kind=StoryUpdateKind.CROWD,
                message="Gion is quiet — density under 40% in the last hour.",
                condition={"crowd_lte": 50},
            ))

    print("+ 3 story posts + 2 adaptive updates seeded")
    db.commit()


def _seed_dependency_graph(db, traveler: User) -> None:
    """P5 seed: a Kyoto trip itinerary with an intentionally tight airport
    transfer buffer, so F-30 risk assessment lights up on the first run.

    Graph shape:

        FlightIn --REQUIRES(45)--> AirportTransfer --REQUIRES(30)--> HotelCheckIn
                                                                       |
                                                                       v REQUIRES(20)
                                                                     TeaCeremony (activity)
                                                                       |
                                                                       v OPTIONAL
                                                                     GionEveningWalk
                                                                       |
                                                                       v SEQUENCED
                                                                     HotelCheckOut --REQUIRES(120)--> FlightOut
    """
    it = db.execute(select(Itinerary).where(Itinerary.title == "Kyoto Weekend")).scalar_one_or_none()
    if it is None:
        it = Itinerary(
            owner_id=traveler.id,
            title="Kyoto Weekend",
            destination_city="Kyoto",
        )
        db.add(it)
        db.flush()

    # Skip if graph already seeded
    if db.execute(select(ItineraryNode).where(ItineraryNode.itinerary_id == it.id)).scalar_one_or_none():
        return

    now = datetime.now(timezone.utc)
    day1 = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)

    def add_node(kind: NodeKind, title: str, start_offset_mins: int, duration_mins: int, **kwargs):
        node = ItineraryNode(
            itinerary_id=it.id,
            kind=kind, title=title,
            start_at=day1 + timedelta(minutes=start_offset_mins),
            end_at=day1 + timedelta(minutes=start_offset_mins + duration_mins),
            **kwargs,
        )
        db.add(node)
        db.flush()
        return node

    flight_in = add_node(
        NodeKind.FLIGHT, "Flight BOM -> KIX", 0, 420,
        cost=45000, currency="INR", refund_class=RefundClass.NON_REFUNDABLE, change_fee=8000,
        provider_ref="AA-234",
    )
    transfer = add_node(
        NodeKind.TRANSFER, "Airport Haruka Express", 445, 75,   # 25 min buffer from flight -> TIGHT for F-30
        cost=3500, currency="INR", refund_class=RefundClass.PARTIALLY_REFUNDABLE, change_fee=500,
    )
    hotel_in = add_node(
        NodeKind.HOTEL, "Hotel Check-in (Gion)", 570, 30,       # 50 min buffer from transfer
        cost=18000, currency="INR", refund_class=RefundClass.FULLY_REFUNDABLE,
    )
    tea = add_node(
        NodeKind.ACTIVITY, "Tea Ceremony", 660, 60,             # 60 min buffer
        cost=3000, currency="INR", refund_class=RefundClass.PARTIALLY_REFUNDABLE, change_fee=1000,
    )
    walk = add_node(
        NodeKind.ACTIVITY, "Gion Evening Walk (optional)", 840, 90,
        cost=0, currency="INR", refund_class=RefundClass.FULLY_REFUNDABLE,
    )
    hotel_out = add_node(
        NodeKind.HOTEL, "Hotel Check-out", 24 * 60 + 600, 30,   # next day 10:00 checkout
        cost=0, currency="INR", refund_class=RefundClass.FULLY_REFUNDABLE,
    )
    flight_out = add_node(
        NodeKind.FLIGHT, "Flight KIX -> BOM", 24 * 60 + 840, 420,  # 4 hours after checkout
        cost=42000, currency="INR", refund_class=RefundClass.NON_REFUNDABLE, change_fee=9000,
        provider_ref="AA-235",
    )

    def add_edge(src, dst, kind=EdgeKind.REQUIRES, buffer_mins=30):
        db.add(ItineraryEdge(
            itinerary_id=it.id,
            from_node_id=src.id, to_node_id=dst.id,
            edge_kind=kind, min_buffer_mins=buffer_mins,
        ))

    add_edge(flight_in, transfer, EdgeKind.REQUIRES, 45)   # 25-min actual gap < 45 required → F-30 risk
    add_edge(transfer, hotel_in, EdgeKind.REQUIRES, 30)
    add_edge(hotel_in, tea, EdgeKind.REQUIRES, 20)
    add_edge(tea, walk, EdgeKind.OPTIONAL, 30)
    add_edge(walk, hotel_out, EdgeKind.SEQUENCED, 0)
    add_edge(hotel_out, flight_out, EdgeKind.REQUIRES, 120)

    print("+ Kyoto trip DAG seeded (7 nodes, 6 edges, tight airport transfer buffer)")
    db.commit()


def _seed_capacity(db) -> None:
    """P3 seed: operator user + a handful of Kyoto zones with a rising-density
    time series and one imminent event, plus 3 nudges."""
    # Operator user
    operator = db.execute(select(User).where(User.email == "operator@voyager.dev")).scalar_one_or_none()
    if not operator:
        operator = User(
            email="operator@voyager.dev",
            password_hash=hash_password("voyager123"),
            full_name="Ops Team",
            country="JP",
            role=UserRole.OPERATOR,
        )
        db.add(operator)
        print("+ operator operator@voyager.dev / voyager123")

    # Zones (idempotent on city+name)
    zone_specs = [
        {"city": "Kyoto", "name": "Gion",      "center_lat": 35.0037, "center_lng": 135.7788, "radius_km": 0.8, "total_capacity": 2500},
        {"city": "Kyoto", "name": "Arashiyama","center_lat": 35.0094, "center_lng": 135.6667, "radius_km": 1.2, "total_capacity": 1800},
        {"city": "Kyoto", "name": "Higashiyama","center_lat": 34.9975,"center_lng": 135.7809, "radius_km": 1.0, "total_capacity": 2000},
        {"city": "Kyoto", "name": "Kyoto Sta.","center_lat": 34.9858, "center_lng": 135.7588, "radius_km": 0.6, "total_capacity": 3000},
    ]
    zone_by_name: dict[str, Zone] = {}
    for spec in zone_specs:
        existing = db.execute(
            select(Zone).where(Zone.city == spec["city"], Zone.name == spec["name"])
        ).scalar_one_or_none()
        if existing:
            zone_by_name[spec["name"]] = existing
            continue
        z = Zone(**spec)
        db.add(z)
        db.flush()
        zone_by_name[spec["name"]] = z

    # Metric time-series (last 60 min) — Gion rising fast toward saturation,
    # Higashiyama moderate, Arashiyama quiet, Station steady.
    #
    # Skips seeding if a recent metric already exists so re-runs are cheap.
    now = datetime.now(timezone.utc)
    already = db.execute(
        select(CapacityMetric).where(CapacityMetric.recorded_at >= now - timedelta(minutes=5))
    ).scalar_one_or_none()
    if already is None:
        curves = {
            "Gion":        [(60, 45), (45, 60), (30, 72), (15, 84), (0, 92)],   # rising steeply
            "Higashiyama": [(60, 40), (45, 44), (30, 48), (15, 52), (0, 56)],   # gradual
            "Arashiyama":  [(60, 22), (45, 24), (30, 26), (15, 28), (0, 30)],   # low
            "Kyoto Sta.":  [(60, 55), (45, 55), (30, 55), (15, 55), (0, 55)],   # flat
        }
        for name, series in curves.items():
            z = zone_by_name[name]
            for mins_ago, density in series:
                occupancy = int(z.total_capacity * density / 100.0)
                db.add(CapacityMetric(
                    zone_id=z.id,
                    source_kind=CapacitySourceKind.VENUE,
                    source_label=f"{name} sensors",
                    occupancy_count=occupancy,
                    capacity_max=z.total_capacity,
                    density_pct=density,
                    recorded_at=now - timedelta(minutes=mins_ago),
                ))
        print("+ capacity metrics seeded (rising Gion, quiet Arashiyama)")

    # Event: concert in Gion ending in 20 minutes → triggers F-17 pressure
    gion = zone_by_name["Gion"]
    ev_exists = db.execute(
        select(ZoneEvent).where(ZoneEvent.zone_id == gion.id, ZoneEvent.name == "Gion Open-Air Concert")
    ).scalar_one_or_none()
    if not ev_exists:
        db.add(ZoneEvent(
            zone_id=gion.id,
            name="Gion Open-Air Concert",
            start_at=now - timedelta(hours=2),
            end_at=now + timedelta(minutes=20),
            expected_attendance=1500,
        ))
        print("+ Gion concert event (ends in 20m)")

    # Nudges: one targeting Arashiyama, one generic
    if not db.execute(select(Nudge)).scalar_one_or_none():
        arashi = zone_by_name["Arashiyama"]
        db.add(Nudge(
            kind=NudgeKind.DISCOUNT,
            title="10% off in Arashiyama",
            description="Use code OFFPEAK10 at partner cafes in Arashiyama tonight.",
            target_zone_id=arashi.id,
            payload={"code": "OFFPEAK10", "pct_off": 10},
        ))
        db.add(Nudge(
            kind=NudgeKind.PRIORITY_PASS,
            title="Priority entry to any low-traffic venue",
            description="Skip the queue when you route away from a red zone.",
            target_zone_id=None,
            payload={"queue_skip": True},
        ))
        db.add(Nudge(
            kind=NudgeKind.BADGE,
            title="Zone Balancer badge",
            description="Awarded for helping smooth crowd flow.",
            target_zone_id=None,
            payload={"badge_id": "zone_balancer_v1"},
        ))
        print("+ 3 nudges seeded")

    db.commit()


if __name__ == "__main__":
    seed()
