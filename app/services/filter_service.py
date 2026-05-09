from app.models import Listing


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    replacements = {
        "č": "c",
        "ć": "c",
        "š": "s",
        "đ": "d",
        "ž": "z",
    }

    value = value.lower()

    for original, replacement in replacements.items():
        value = value.replace(original, replacement)

    return value


def matches_filters(listing: Listing, filters: dict) -> bool:
    global_filters = filters.get("global", {})

    max_price = global_filters.get("max_price")
    min_size = global_filters.get("min_size")
    max_size = global_filters.get("max_size")
    min_rooms = global_filters.get("min_rooms")
    allowed_neighborhoods = global_filters.get("allowed_neighborhoods", [])

    if max_price is not None and listing.price is not None:
        if listing.price > max_price:
            return False

    if min_size is not None and listing.size is not None:
        if listing.size < min_size:
            return False

    if max_size is not None and listing.size is not None:
        if listing.size > max_size:
            return False

    if min_rooms is not None and listing.rooms is not None:
        if listing.rooms < min_rooms:
            return False

    if allowed_neighborhoods:
        title_text = normalize_text(listing.title)
        neighborhood_text = normalize_text(listing.neighborhood)
        combined_text = f"{title_text} {neighborhood_text}"

        normalized_allowed = [normalize_text(kvart) for kvart in allowed_neighborhoods]

        if not any(kvart in combined_text for kvart in normalized_allowed):
            return False

    return True