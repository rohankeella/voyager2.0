import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StoryUpdateKind(str, enum.Enum):
    WEATHER = "WEATHER"
    CROWD = "CROWD"
    PRICE = "PRICE"
    GENERIC = "GENERIC"


class StoryPost(Base):
    """F-21 structured story post.

    Editorial in nature (`body_md`, `summary`, `cover_image_url`) but every
    filterable field is a first-class column so the feed ranker (F-22) and
    context-tag mapper (F-23) never have to parse markdown to answer
    "does this match?".
    """

    __tablename__ = "story_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("providers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    experience_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiences.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(400), nullable=True)
    body_md: Mapped[str] = mapped_column(String(20000))
    cover_image_url: Mapped[str | None] = mapped_column(String(600), nullable=True)

    city: Mapped[str | None] = mapped_column(String(120), index=True)
    location_hint: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"lat":.., "lng":..}

    # Structured mirror of the semantic tags embedded in body_md. Kept as a
    # denormalised list so the feed query can index/filter without a join.
    context_tags: Mapped[list] = mapped_column(JSON, default=list)

    # 0..100 heuristic — see services/editorial.narrative_quality_score.
    narrative_quality_score: Mapped[float] = mapped_column(Float, default=50.0, index=True)

    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    updates = relationship(
        "StoryUpdate", back_populates="post", cascade="all, delete-orphan",
        order_by="StoryUpdate.created_at.desc()",
    )


class StoryUpdate(Base):
    """F-24 in-post adaptive update. Each row expresses one contextual
    condition (`condition` JSON) that, when true, should surface the
    corresponding `message` banner at the top of the rendered post.

    Conditions are matched by `services.editorial.resolve_active_updates` at
    read time against a `RuntimeContext` (weather, current hour, crowd
    level, etc.) supplied by the client.
    """

    __tablename__ = "story_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str] = mapped_column(ForeignKey("story_posts.id", ondelete="CASCADE"), index=True)
    kind: Mapped[StoryUpdateKind] = mapped_column(Enum(StoryUpdateKind), index=True)
    message: Mapped[str] = mapped_column(String(400))
    # e.g. {"weather": "rain"}, {"hour_between": [17,19]}, {"crowd_gte": 85}
    condition: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    post = relationship("StoryPost", back_populates="updates")
