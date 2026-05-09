import hashlib
import re
import xml.etree.ElementTree as ET
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
        # For Njuskalo, try RSS feed first (much harder to bot-block)
        if self.source == "njuskalo":
            rss_url = self._to_rss_url(url)
            try:
                return self._fetch_rss(rss_url)
            except Exception as e:
                print(f"[{self.source}] RSS fetch failed ({e}), trying HTML scrape...")
        return self._fetch_html(url)

    def _to_rss_url(self, url: str) -> str:
        separator = "&" if "?" in url else "?"
        return url + separator + "format=rss"

    def _fetch_rss(self, url: str) -> list[Listing]:
        response = requests.get(url, headers=self._get_headers(rss=True), timeout=30)
        response.raise_for_status()

        print(f"[{self.source}] RSS HTTP status: {response.status_code}")
        print(f"[{self.source}] RSS length: {len(response.text)}")

        # Detect CAPTCHA returned instead of RSS
        if "<rss" not in response.text[:1000] and "<?xml" not in response.text[:500]:
            if "ShieldSquare" in response.text or "captcha" in response.text.lower():
                raise Exception("CAPTCHA page returned — IP blocked by Njuskalo anti-bot")
            raise Exception(f"Response is not RSS XML. Got: {response.text[:300]}")

        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if channel is None:
            raise Exception("No <channel> in RSS")

        items = channel.findall("item")
        print(f"[{self.source}] RSS items found: {len(items)}")

        listings = []
        for item in items:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")

            if title_el is None or link_el is None:
                continue

            title = (title_el.text or "").strip()
            listing_url = (link_el.text or "").strip()
            description = (desc_el.text or "") if desc_el is not None else ""

            combined = f"{title} {description}"
            clean_text = re.sub(r"<[^>]+>", " ", combined)

            listing = Listing(
                external_id=self._make_external_id(listing_url),
                source=self.source,
                title=title,
                price=self._extract_price(clean_text),
                rooms=self._extract_rooms(clean_text),
                size=self._extract_size(clean_text),
                neighborhood=self._extract_neighborhood(clean_text),
                url=listing_url,
            )
            listings.append(listing)

        unique = {l.external_id: l for l in listings}
        return list(unique.values())[:50]

    def _fetch_html(self, url: str) -> list[Listing]:
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        response.raise_for_status()

        print(f"[{self.source}] HTTP status: {response.status_code}")
        print(f"[{self.source}] HTML length: {len(response.text)}")

        # Detect bot-block / CAPTCHA page
        if "ShieldSquare" in response.text or "shieldsquare" in response.text.lower():
            print(f"[{self.source}] ⚠️  CAPTCHA/bot-block detected! Railway IP is blocked by Njuskalo.")
            print(f"[{self.source}] Fix: use RSS feed URL (add &format=rss) or a rotating proxy.")
            return []

        if "captcha" in response.text.lower() and len(response.text) < 50_000:
            print(f"[{self.source}] ⚠️  Possible CAPTCHA page ({len(response.text)} chars).")
            return []

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

        unique = {l.external_id: l for l in listings}
        return list(unique.values())[:30]

    def _get_headers(self, rss: bool = False) -> dict:
        base = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }
        if rss:
            base["Accept"] = "application/rss+xml, application/xml, text/xml, */*"
        else:
            base["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            base["Upgrade-Insecure-Requests"] = "1"
        return base

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
            "kontakt", "contact", "pomoc", "help", "pravila", "uvjeti",
            "login", "registracija", "moj-njuskalo", "predaja-oglasa",
            "spremi-oglas", "facebook", "instagram", "youtube",
        ]
        if any(b in lowered for b in blocked_parts):
            return False
        if self.source == "njuskalo":
            return "njuskalo.hr" in lowered and "/nekretnine/" in lowered and "oglas" in lowered
        if self.source == "index":
            return ("index.hr/oglasi" in lowered and "oglas" in lowered
                    and ("stan" in lowered or "najam" in lowered or "nekretn" in lowered))
        return False

    def _make_external_id(self, url: str) -> str:
        value = f"{self.source}:{url}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _extract_price(self, text: str):
        patterns = [r"(\d{2,5})\s*€", r"(\d{2,5})\s*eur", r"(\d{2,5})\s*eura"]
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
            "jednosoban": 1, "dvosoban": 2, "trosoban": 3,
            "četverosoban": 4, "cetverosoban": 4,
        }
        for word, number in word_mapping.items():
            if word in normalized:
                return number
        patterns = [r"(\d+(?:\.\d+)?)\s*sob", r"(\d+(?:\.\d+)?)\s*-sob"]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return float(match.group(1))
        return None

    def _extract_neighborhood(self, text: str):
        neighborhoods = [
            "Trešnjevka", "Maksimir", "Centar", "Donji grad", "Gornji grad",
            "Črnomerec", "Vrbani", "Jarun", "Špansko", "Rudeš", "Kvatrić",
            "Dubrava", "Trnje", "Kajzerica", "Savica", "Sigečica", "Prečko",
            "Malešnica", "Stenjevec", "Podsused", "Sesvete", "Utrina", "Siget",
            "Središće", "Lanište", "Remetinec", "Botinec", "Borovje",
            "Knežija", "Svetice", "Medveščak",
        ]
        lowered = text.lower()
        for neighborhood in neighborhoods:
            if neighborhood.lower() in lowered:
                return neighborhood
        return None