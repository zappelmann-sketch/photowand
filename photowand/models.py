"""Datenmodelle fuer die Photowand-Anwendung."""

from dataclasses import dataclass, field
from PIL import Image


@dataclass
class HexSlotData:
    """Daten eines einzelnen Hexagon-Slots."""

    slot_index: int
    foto_pfad: str | None = None
    foto_bild: Image.Image | None = None
    zoom: float = 1.0
    offset_x: float = 0.0  # Verschiebung in mm
    offset_y: float = 0.0  # Verschiebung in mm

    @property
    def ist_belegt(self) -> bool:
        return self.foto_bild is not None
