"""Python client models for ETI/Domo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Floor:
    """Object holding the ETI/Domo floor description."""

    id: int
    name: str

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Floor:
        """Return a State object from a ETI/Domo API response."""

        return Floor(
            id=int(data["floor_ind"]),
            name=str(data["name"]),
        )


@dataclass
class Room:
    """Object holding the ETI/Domo room description."""

    id: int
    name: str
    floor_id: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Room:
        """Return a State object from a ETI/Domo API response."""

        return Room(
            id=int(data["room_ind"]),
            name=str(data["name"]),
            floor_id=int(data["floor_ind"]),
        )
