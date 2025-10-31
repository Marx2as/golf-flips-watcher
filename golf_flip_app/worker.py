"""
Background worker to poll marketplaces and send notifications.

This module contains the main polling loop that calls the fetchers,
computes profitability, and triggers the notifier when conditions are
met.  The worker respects configuration flags that enable or disable
individual marketplaces and can be run either once or continuously.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from typing import List

from .settings import get_settings, Settings
from .seen_store import SeenStore
from .ebay_fetcher import EbayFetcher
from .vinted_fetcher import VintedFetcher
from .whatsapp import WhatsAppNotifier, format_message
from .valuation import compute_profit

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")


def parse_keywords(keyword_str: str) -> List[str]:
    return [kw.strip() for kw in keyword_str.split(",") if kw.strip()]


def condition_acceptable(condition: str) -> bool:
    if not condition:
        return False
    acceptable = ["new", "like new", "excellent", "very good", "good"]
    return condition.lower() in acceptable


async def run_once(settings: Settings) -> None:
    """Perform a single polling cycle across enabled marketplaces."""
    seen_store = SeenStore(settings.SQLITE_DB)
    notifier = WhatsAppNotifier(settings)
    keywords = parse_keywords(settings.KEYWORDS)
    max_price = settings.MAX_PRICE
    regex_include = re.compile(settings.REGEX_INCLUDE, re.IGNORECASE) if settings.REGEX_INCLUDE else None
    regex_exclude = re.compile(settings.REGEX_EXCLUDE, re.IGNORECASE) if settings.REGEX_EXCLUDE else None

    fetchers = []
    if settings.ENABLE_EBAY:
        fetchers.append(EbayFetcher(settings))
    if settings.ENABLE_VINTED:
        fetchers.append(VintedFetcher(settings))

    for fetcher in fetchers:
        try:
            listings = fetcher.fetch_listings(keywords, max_price)
        except Exception as exc:
            logger.error("Fetcher error: %s", exc)
            continue
        for listing in listings:
            marketplace = listing["marketplace"]
            listing_id = listing["listing_id"]
            if not listing_id:
                continue
            if seen_store.has_seen(marketplace, listing_id):
                continue
            title = listing.get("title", "")
            # apply regex include/exclude filters
            if regex_include and not regex_include.search(title):
                continue
            if regex_exclude and regex_exclude.search(title):
                continue
            # skip if condition unacceptable
            cond = listing.get("condition") or ""
            if cond and not condition_acceptable(cond):
                continue
            # compute cost and profit
            (
                product_cost,
                buyer_protection_cost,
                shipping_cost,
                total_cost,
                potential_resale_value,
                profit,
                margin_percent,
            ) = compute_profit(listing, settings)
            # Determine if meets thresholds
            if profit < settings.PROFIT_MIN or margin_percent < settings.MARGIN_MIN_PERCENT:
                # do not notify but mark seen to avoid re-processing low-profit items
                seen_store.mark_seen(marketplace, listing_id)
                continue
            # send message
            message = format_message(
                listing,
                (
                    product_cost,
                    buyer_protection_cost,
                    shipping_cost,
                    total_cost,
                    potential_resale_value,
                    profit,
                    margin_percent,
                ),
                settings,
            )
            if notifier.send(message):
                logger.info("Notification sent for %s %s", marketplace, listing_id)
            # Always mark as seen after attempt
            seen_store.mark_seen(marketplace, listing_id)
            # Log JSON payload for persistence
            payload = {
                "marketplace": marketplace,
                "listing_id": listing_id,
                "title": listing.get("title"),
                "url": listing.get("url"),
                "brand": listing.get("brand"),
                "model": listing.get("model"),
                "condition": listing.get("condition"),
                "product_cost": product_cost,
                "buyer_protection_cost": buyer_protection_cost,
                "shipping_cost": shipping_cost,
                "total_cost": total_cost,
                "potential_resale_value": potential_resale_value,
                "profit": profit,
                "margin_percent": margin_percent,
                "currency": settings.CURRENCY,
                "timestamp_utc": datetime.utcnow().isoformat(),
            }
            logger.info("Payload: %s", json.dumps(payload))


async def start_worker() -> None:
    """Continuously run polling cycles at the configured interval."""
    settings = get_settings()
    interval_seconds = max(settings.POLL_INTERVAL, 1) * 60
    while True:
        await run_once(settings)
        await asyncio.sleep(interval_seconds)


def main() -> None:
    """Entry point for the worker process."""
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
