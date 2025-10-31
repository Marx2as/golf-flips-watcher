"""
WhatsApp notification helpers.

This module implements sending messages via WhatsApp Cloud API and
Twilio's WhatsApp API.  It also contains helpers to format the
notification message based on the listing and computed cost breakdown.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

import requests

from .settings import Settings

logger = logging.getLogger(__name__)


def format_message(listing: Dict[str, str], breakdown: Tuple[float, float, float, float, float, float, float], settings: Settings) -> str:
    """Construct the WhatsApp notification text.

    The message includes the title, URL, condition, cost breakdown and
    potential resale value.  Values are formatted to two decimal
    places and use the configured currency.
    """
    (
        product_cost,
        buyer_protection_cost,
        shipping_cost,
        total_cost,
        potential_resale_value,
        profit,
        margin_percent,
    ) = breakdown
    currency_symbol = "\u00a3" if settings.CURRENCY.upper() == "GBP" else settings.CURRENCY + " "
    message = (
        f"Title: {listing['title']}\n"
        f"Link: {listing['url']}\n"
        f"Condition: {listing.get('condition', 'Unknown')}\n\n"
        f"Costs\n"
        f"Product: {currency_symbol}{product_cost:.2f}\n"
        f"Buyer protection: {currency_symbol}{buyer_protection_cost:.2f}\n"
        f"Shipping: {currency_symbol}{shipping_cost:.2f}\n"
        f"Total: {currency_symbol}{total_cost:.2f}\n\n"
        f"Value\n"
        f"Potential resale: {currency_symbol}{potential_resale_value:.2f}\n"
        f"Profit: {currency_symbol}{profit:.2f}  ({margin_percent:.2f}% )\n\n"
        f"{'\ud83d\udd35 Looks good!' if profit >= settings.PROFIT_MIN else '\ud83d\udfe4 Not profitable enough'}"
    )
    return message


class WhatsAppNotifier:
    """Send notifications through WhatsApp Cloud API or Twilio."""

    GRAPH_ENDPOINT_TEMPLATE = "https://graph.facebook.com/v17.0/{phone_id}/messages"
    TWILIO_ENDPOINT_TEMPLATE = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: str) -> bool:
        """Send a WhatsApp message using the configured provider.

        Returns ``True`` if the message was sent successfully, otherwise
        ``False``.  Attempts to use the WhatsApp Cloud API first; if
        missing or fails, falls back to Twilio if credentials are present.
        """
        # Try WhatsApp Cloud API
        if self.settings.WA_PHONE_ID and self.settings.WA_TOKEN:
            if self._send_cloud(message):
                return True
        # Fallback to Twilio
        if (
            self.settings.TWILIO_ACCOUNT_SID
            and self.settings.TWILIO_AUTH_TOKEN
            and self.settings.TWILIO_WHATSAPP_FROM
        ):
            return self._send_twilio(message)
        logger.error("No WhatsApp transport configured; unable to send notifications")
        return False

    def _send_cloud(self, message: str) -> bool:
        url = self.GRAPH_ENDPOINT_TEMPLATE.format(phone_id=self.settings.WA_PHONE_ID)
        payload = {
            "messaging_product": "whatsapp",
            "to": self.settings.RECIPIENT_PHONE,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.WA_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("WhatsApp Cloud API send failed: %s", exc)
            return False

    def _send_twilio(self, message: str) -> bool:
        url = self.TWILIO_ENDPOINT_TEMPLATE.format(account_sid=self.settings.TWILIO_ACCOUNT_SID)
        data = {
            "From": f"whatsapp:{self.settings.TWILIO_WHATSAPP_FROM}",
            "To": f"whatsapp:{self.settings.RECIPIENT_PHONE}",
            "Body": message,
        }
        try:
            resp = requests.post(
                url,
                data=data,
                auth=(self.settings.TWILIO_ACCOUNT_SID, self.settings.TWILIO_AUTH_TOKEN),
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Twilio WhatsApp send failed: %s", exc)
            return False
