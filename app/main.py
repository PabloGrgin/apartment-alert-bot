import time

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import CHECK_INTERVAL_MINUTES, load_filters
from app.db import init_db, listing_exists, mark_as_notified, save_listing
from app.scrapers.generic_scraper import GenericRealEstateScraper
from app.services.filter_service import matches_filters
from app.services.telegram_service import send_new_listing, send_telegram_message


def build_scrapers(filters: dict):
    scrapers = []

    sources = filters.get("sources", {})

    for source_name, source_config in sources.items():
        enabled = source_config.get("enabled", False)
        urls = source_config.get("urls", [])

        urls = [url for url in urls if url and not url.startswith("OVDJE_")]

        if enabled and urls:
            scrapers.append(GenericRealEstateScraper(source_name, urls))

    return scrapers


def check_listings():
    print("Checking apartment listings...")

    filters = load_filters()
    scrapers = build_scrapers(filters)

    if not scrapers:
        print("No scrapers configured. Check config/filters.yaml.")
        return

    total_found = 0
    total_new = 0
    total_sent = 0

    for scraper in scrapers:
        listings = scraper.fetch()
        total_found += len(listings)

        print(f"[{scraper.source}] Found {len(listings)} possible listings.")

        for listing in listings:
            if listing_exists(listing.external_id):
                continue

            total_new += 1
            save_listing(listing)

            if not matches_filters(listing, filters):
                print(f"Skipped by filters: {listing.title}")
                continue

            try:
                send_new_listing(listing)
                mark_as_notified(listing.external_id)
                total_sent += 1
                print(f"Sent Telegram notification: {listing.title}")
                time.sleep(1)
            except Exception as error:
                print(f"Telegram error for {listing.url}: {error}")

    print(f"Done. Found: {total_found}, new: {total_new}, sent: {total_sent}")


def main():
    init_db()

    print("Apartment alert bot started.")
    print(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")

    try:
        send_telegram_message("✅ Apartment alert bot je pokrenut.")
    except Exception as error:
        print(f"Could not send startup Telegram message: {error}")

    check_listings()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        check_listings,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()


if __name__ == "__main__":
    main()