import html
import requests

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from app.models import Listing


def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    response.raise_for_status()


def send_new_listing(listing: Listing):
    title = html.escape(listing.title)
    source = html.escape(listing.source.upper())
    neighborhood = html.escape(listing.neighborhood or "Nepoznato")
    url = html.escape(listing.url)

    price_text = f"{listing.price} €" if listing.price is not None else "Nepoznato"
    size_text = f"{listing.size} m²" if listing.size is not None else "Nepoznato"
    rooms_text = str(listing.rooms) if listing.rooms is not None else "Nepoznato"

    message = f"""
🏠 <b>Novi oglas za stan</b>

<b>{title}</b>

💶 <b>Cijena:</b> {price_text}
🛏 <b>Sobe:</b> {rooms_text}
📐 <b>Kvadratura:</b> {size_text}
📍 <b>Kvart:</b> {neighborhood}
🌐 <b>Izvor:</b> {source}

🔗 <a href="{url}">Otvori oglas</a>
""".strip()

    send_telegram_message(message)