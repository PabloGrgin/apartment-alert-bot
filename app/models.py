from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    external_id: str
    source: str
    title: str
    price: Optional[int]
    rooms: Optional[float]
    size: Optional[float]
    neighborhood: Optional[str]
    url: str