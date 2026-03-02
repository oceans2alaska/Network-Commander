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


LOG_PATH = "/home/david/Documents/GitHub/Network-Commander/.cursor/debug-eac3fa.log"

def _debug_log(msg: str, data: dict) -> None:
    import json
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({"sessionId": "eac3fa", "location": "config.py:get_settings", "message": msg, "data": data, "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass

@lru_cache()
def get_settings() -> Settings:
    # #region agent log
    has_dotenv = os.path.exists(".env")
    unifi_keys = [k for k in os.environ if k.startswith("UNIFI_")]
    _debug_log("get_settings called", {"has_dotenv": has_dotenv, "unifi_env_keys": unifi_keys, "calling_Settings_with_args": False})
    # #endregion
    # Allow loading from a .env file if present
    if has_dotenv:
        from dotenv import load_dotenv

        load_dotenv(override=False)
        # #region agent log
        unifi_keys_after = [k for k in os.environ if k.startswith("UNIFI_")]
        _debug_log("after load_dotenv", {"unifi_env_keys": unifi_keys_after})
        # #endregion

    # #region agent log
    _debug_log("about to call Settings() with no arguments", {})
    # #endregion
    try:
        return Settings()  # type: ignore[arg-type]
    except Exception as e:
        # #region agent log
        _debug_log("Settings() validation failed", {"error_type": type(e).__name__, "error_msg": str(e)[:500]})
        # #endregion
        raise

