"""
Application configuration and environment variable parsing.

This module provides a lightweight configuration class that reads
environment variables and exposes typed attributes.  The class is
implemented without Pydantic to avoid dependency issues in restricted
environments.  Defaults are sensible for local development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: Optional[float] = None) -> Optional[float]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class Settings:
    """Configuration values loaded from environment variables."""

    EBAY_APP_ID: Optional[str] = os.getenv("EBAY_APP_ID")
    EBAY_CLIENT_ID: Optional[str] = os.getenv("EBAY_CLIENT_ID")
    EBAY_CLIENT_SECRET: Optional[str] = os.getenv("EBAY_CLIENT_SECRET")
    EBAY_ENV: str = os.getenv("EBAY_ENV", "PROD")

    ENABLE_EBAY: bool = _env_bool("ENABLE_EBAY", True)
    ENABLE_VINTED: bool = _env_bool("ENABLE_VINTED", False)
    VINTED_REGION: str = os.getenv("VINTED_REGION", "uk")

    WA_PHONE_ID: Optional[str] = os.getenv("WA_PHONE_ID")
    WA_TOKEN: Optional[str] = os.getenv("WA_TOKEN")
    RECIPIENT_PHONE: Optional[str] = os.getenv("RECIPIENT_PHONE")

    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_FROM: Optional[str] = os.getenv("TWILIO_WHATSAPP_FROM")

    PROFIT_MIN: float = _env_float("PROFIT_MIN", 10.0) or 10.0
    MARGIN_MIN_PERCENT: float = _env_float("MARGIN_MIN_PERCENT", 20.0) or 20.0

    KEYWORDS: str = os.getenv(
        "KEYWORDS", "driver,putter,irons,Scotty Cameron,Cobra,Taylormade,Titleist"
    )
    MAX_PRICE: Optional[float] = _env_float("MAX_PRICE")
    REGEX_INCLUDE: Optional[str] = os.getenv("REGEX_INCLUDE")
    REGEX_EXCLUDE: Optional[str] = os.getenv("REGEX_EXCLUDE")

    CURRENCY: str = os.getenv("CURRENCY", "GBP")
    POLL_INTERVAL: int = _env_int("POLL_INTERVAL", 5)
    VALUATION_STRATEGY: str = os.getenv("VALUATION_STRATEGY", "C")
    SHIPPING_TABLE_JSON: Optional[str] = os.getenv("SHIPPING_TABLE_JSON")
    SQLITE_DB: str = os.getenv("SQLITE_DB", "seen.db")


def get_settings() -> Settings:
    """Factory function to create a new Settings instance.

    Using a function rather than a global instance ensures environment
    variables are read each time the settings are needed, which is
    useful for testing and dynamic reloads.
    """
    return Settings()
