from functools import lru_cache
import json
from typing import Annotated, List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./voyager.db"

    jwt_secret: str = Field(default="dev-insecure-change-me", validation_alias=AliasChoices("JWT_SECRET", "SECRET_KEY"))
    jwt_algorithm: str = Field(default="HS256", validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"))
    jwt_expires_minutes: int = Field(default=60 * 24, gt=0, validation_alias=AliasChoices("JWT_EXPIRES_MINUTES", "ACCESS_TOKEN_EXPIRE_MINUTES"))

    @field_validator("database_url", mode="before")
    @classmethod
    def _postgres_driver(cls, value):
        return value.replace("postgresql://", "postgresql+psycopg://", 1) if isinstance(value, str) else value

    # NoDecode prevents pydantic-settings from trying to JSON-parse the raw
    # env string — the CSV validator below handles it explicitly.
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    google_maps_api_key: str | None = None

    amadeus_client_id: str | None = None
    amadeus_client_secret: str | None = None
    amadeus_env: str = "test"

    # Gemini — powers the Planner/Executor/Supervisor agents. Get a free key
    # at https://aistudio.google.com/apikey. Free tier: 15 rpm, 1M tokens/day.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # OpenTripPlanner — Executor Agent queries this for ground-transit polylines
    # + stoptime cross-reference. Default: Digitransit's free public Finland
    # instance. For other regions, set OTP_GRAPHQL_URL to your own OTP + adjust
    # the coverage bbox in services/otp.py.
    otp_graphql_url: str | None = "https://api.digitransit.fi/routing/v2/finland/gtfs/v1"
    otp_client_name: str = "voyager-hackathon"
    otp_subscription_key: str | None = None   # optional Digitransit API key

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            if v.strip().startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
