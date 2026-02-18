"""Layout-Engine: Positioniert Sechsecke auf verschiedenen Papierformaten."""

import math
from dataclasses import dataclass
from photowand.core.hexagon import HexagonGeometry


# Papierformate (Breite x Hoehe in mm, Hochformat)
PAPIER_FORMATE: dict[str, tuple[float, float]] = {
    "A5": (148.0, 210.0),
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
}


@dataclass
class HexSlotPosition:
    """Position eines Hexagon-Slots auf der Seite."""

    index: int
    center_x_mm: float
    center_y_mm: float
    row: int
    col: int


class LayoutEngine:
    """Berechnet die optimale Anordnung von Sechsecken auf einer Seite.

    Unterstuetzt A5, A4, A3, A2. Die Anzahl der Spalten und Zeilen
    wird automatisch berechnet.
    """

    def __init__(
        self,
        hex_geo: HexagonGeometry | None = None,
        dpi: int = 300,
        format_name: str = "A4",
    ):
        self.hex = hex_geo or HexagonGeometry()
        self.dpi = dpi
        self._format_name = format_name
        self._breite_mm, self._hoehe_mm = PAPIER_FORMATE[format_name]
        self._spalten = 0
        self._zeilen = 0
        self._berechne_raster()

    @property
    def format_name(self) -> str:
        return self._format_name

    @property
    def breite_mm(self) -> float:
        return self._breite_mm

    @property
    def hoehe_mm(self) -> float:
        return self._hoehe_mm

    @property
    def spalten(self) -> int:
        return self._spalten

    @property
    def zeilen(self) -> int:
        return self._zeilen

    @property
    def slot_anzahl(self) -> int:
        return self._spalten * self._zeilen

    def setze_format(self, format_name: str) -> None:
        """Wechselt das Papierformat."""
        self._format_name = format_name
        self._breite_mm, self._hoehe_mm = PAPIER_FORMATE[format_name]
        self._berechne_raster()

    def _berechne_raster(self) -> None:
        """Berechnet Spalten und Zeilen fuer das aktuelle Format."""
        hex_b = self.hex.breite_mm   # ~100mm
        hex_h = self.hex.hoehe_mm    # ~86.4mm
        self._spalten = int(self._breite_mm / hex_b)
        self._zeilen = int(self._hoehe_mm / hex_h)

    def berechne_positionen(self) -> list[HexSlotPosition]:
        """Berechnet die Slot-Positionen in Millimetern."""
        hex_b = self.hex.breite_mm
        hex_h = self.hex.hoehe_mm

        # Horizontale Verteilung (gleichmaessige Luecken)
        gesamt_hex_b = self._spalten * hex_b
        luecke_h = (self._breite_mm - gesamt_hex_b) / (self._spalten + 1)
        spalten_x = [
            luecke_h + hex_b / 2 + i * (hex_b + luecke_h)
            for i in range(self._spalten)
        ]

        # Vertikale Verteilung (gleichmaessige Luecken)
        gesamt_hex_h = self._zeilen * hex_h
        luecke_v = (self._hoehe_mm - gesamt_hex_h) / (self._zeilen + 1)
        zeilen_y = [
            luecke_v + hex_h / 2 + i * (hex_h + luecke_v)
            for i in range(self._zeilen)
        ]

        positionen = []
        index = 0
        for row, y in enumerate(zeilen_y):
            for col, x in enumerate(spalten_x):
                positionen.append(HexSlotPosition(
                    index=index,
                    center_x_mm=x,
                    center_y_mm=y,
                    row=row,
                    col=col,
                ))
                index += 1

        return positionen

    def berechne_positionen_px(self) -> list[HexSlotPosition]:
        """Positionen in Pixel bei self.dpi."""
        mm_positionen = self.berechne_positionen()
        return [
            HexSlotPosition(
                index=p.index,
                center_x_mm=HexagonGeometry.mm_to_px(p.center_x_mm, self.dpi),
                center_y_mm=HexagonGeometry.mm_to_px(p.center_y_mm, self.dpi),
                row=p.row,
                col=p.col,
            )
            for p in mm_positionen
        ]

    def seiten_groesse_px(self) -> tuple[int, int]:
        """Seitengroesse in Pixel bei self.dpi."""
        return (
            HexagonGeometry.mm_to_px(self._breite_mm, self.dpi),
            HexagonGeometry.mm_to_px(self._hoehe_mm, self.dpi),
        )


# Rueckwaertskompatibilitaet
A4LayoutEngine = LayoutEngine
