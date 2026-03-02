import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel, AnyHttpUrl, Field, validator


class Settings(BaseModel):
    unifi_controller_url: AnyHttpUrl = Field(..., alias="UNIFI_CONTROLLER_URL")
    unifi_username: str = Field(..., alias="UNIFI_USERNAME")
    unifi_password: str = Field(..., alias="UNIFI_PASSWORD")
    unifi_site: str = Field("default", alias="UNIFI_SITE")
    unifi_is_udm_pro: bool = Field(False, alias="UNIFI_IS_UDM_PRO")
    unifi_verify_ssl: bool = Field(True, alias="UNIFI_VERIFY_SSL")
    ping_targets: List[str] = Field(default_factory=lambda: ["1.1.1.1", "8.8.8.8"], alias="PING_TARGETS")

    @validator("unifi_is_udm_pro", "unifi_verify_ssl", pre=True)
    def _bool_from_env(cls, v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        return str(v).strip().lower() in {"1", "true", "yes", "y"}

    @validator("ping_targets", pre=True)
    def _split_targets(cls, v):
        if isinstance(v, list):
            return v
        if not v:
            return ["1.1.1.1", "8.8.8.8"]
        return [item.strip() for item in str(v).split(",") if item.strip()]

    class Config:
        allow_population_by_field_name = True
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    # Allow loading from a .env file if present
    if os.path.exists(".env"):
        from dotenv import load_dotenv

        load_dotenv(override=False)

    return Settings()  # type: ignore[arg-type]

