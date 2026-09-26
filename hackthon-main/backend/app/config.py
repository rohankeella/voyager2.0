from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./voyager.db"

    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

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
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
