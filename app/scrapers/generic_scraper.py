import hashlib
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.models import Listing
from app.scrapers.base_scraper import BaseScraper


class GenericRealEstateScraper(BaseScraper):
    def __init__(self, source: str, urls: list[str]):
        self.source = source
        self.urls = urls

    def fetch(self) -> list[Listing]:
        listings = []

        for url in self.urls:
            try:
                listings.extend(self._fetch_url(url))
            except Exception as error:
                print(f"[{self.source}] Error while fetching {url}: {error}")

        return listings

    def _fetch_url(self, url: str) -> list[Listing]:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
            },
            timeout=30,
        )

        response.raise_for_status()

        print(f"[{self.source}] HTTP status: {response.status_code}")
        print(f"[{self.source}] HTML length: {len(response.text)}")

        soup = BeautifulSoup(response.text, "lxml")

        candidates = self._extract_candidate_links(soup, url)

        print(f"[{self.source}] Candidate links found: {len(candidates)}")

        for title, listing_url, _ in candidates[:10]:
            print(f"- {title} -> {listing_url}")

        listings = []

        for title, listing_url, text in candidates:
            listing = Listing(
                external_id=self._make_external_id(listing_url),
                source=self.source,
                title=title,
                price=self._extract_price(text),
                rooms=self._extract_rooms(text),
                size=self._extract_size(text),
                neighborhood=self._extract_neighborhood(text),
                url=listing_url,
            )

            listings.append(listing)

        unique = {}

        for listing in listings:
            unique[listing.external_id] = listing

        return list(unique.values())[:30]

    def _extract_candidate_links(self, soup: BeautifulSoup, base_url: str):
        results = []

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            title = link.get_text(" ", strip=True)

            if not title or len(title) < 8:
                continue

            absolute_url = urljoin(base_url, href)

            if not self._looks_like_listing_url(absolute_url):
                continue

            container = link.find_parent(["article", "li", "div"])
            container_text = container.get_text(" ", strip=True) if container else title

            results.append((title, absolute_url, container_text))

        return results

    def _looks_like_listing_url(self, url: str) -> bool:
        lowered = url.lower()

        blocked_parts = [
            "kontakt",
            "contact",
            "pomoc",
            "help",
            "pravila",
            "uvjeti",
            "login",
            "registracija",
            "moj-njuskalo",
            "predaja-oglasa",
            "spremi-oglas",
            "facebook",
            "instagram",
            "youtube",
        ]

        if any(blocked in lowered for blocked in blocked_parts):
            return False

        if self.source == "njuskalo":
            return (
                "njuskalo.hr" in lowered
                and "/nekretnine/" in lowered
                and "oglas" in lowered
            )

        if self.source == "index":
            return (
                "index.hr/oglasi" in lowered
                and "oglas" in lowered
                and (
                    "stan" in lowered
                    or "najam" in lowered
                    or "nekretn" in lowered
                )
            )

        return False

    def _make_external_id(self, url: str) -> str:
        value = f"{self.source}:{url}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _extract_price(self, text: str):
        patterns = [
            r"(\d{2,5})\s*€",
            r"(\d{2,5})\s*eur",
            r"(\d{2,5})\s*eura",
        ]

        normalized = text.lower().replace(".", "")

        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return int(match.group(1))

        return None

    def _extract_size(self, text: str):
        patterns = [
            r"(\d{1,3}(?:[,.]\d{1,2})?)\s*m2",
            r"(\d{1,3}(?:[,.]\d{1,2})?)\s*m²",
            r"(\d{1,3}(?:[,.]\d{1,2})?)\s*kvadrata",
        ]

        normalized = text.lower()

        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return float(match.group(1).replace(",", "."))

        return None

    def _extract_rooms(self, text: str):
        normalized = text.lower().replace(",", ".")

        word_mapping = {
            "jednosoban": 1,
            "dvosoban": 2,
            "trosoban": 3,
            "četverosoban": 4,
            "cetverosoban": 4,
        }

        for word, number in word_mapping.items():
            if word in normalized:
                return number

        patterns = [
            r"(\d+(?:\.\d+)?)\s*sob",
            r"(\d+(?:\.\d+)?)\s*-sob",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return float(match.group(1))

        return None

    def _extract_neighborhood(self, text: str):
        neighborhoods = [
            "Trešnjevka",
            "Maksimir",
            "Centar",
            "Donji grad",
            "Gornji grad",
            "Črnomerec",
            "Vrbani",
            "Jarun",
            "Špansko",
            "Rudeš",
            "Kvatrić",
            "Dubrava",
            "Trnje",
            "Kajzerica",
            "Savica",
            "Sigečica",
            "Prečko",
            "Malešnica",
            "Stenjevec",
            "Podsused",
            "Sesvete",
            "Utrina",
            "Siget",
            "Središće",
            "Lanište",
            "Remetinec",
            "Botinec",
            "Borovje",
            "Knežija",
            "Svetice",
            "Medveščak",
        ]

        lowered = text.lower()

        for neighborhood in neighborhoods:
            if neighborhood.lower() in lowered:
                return neighborhood

        return None