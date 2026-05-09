from abc import ABC, abstractmethod

from app.models import Listing


class BaseScraper(ABC):
    @abstractmethod
    def fetch(self) -> list[Listing]:
        pass