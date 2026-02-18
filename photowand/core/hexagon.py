"""Hexagon-Geometrie fuer den sechseckigen Bilderrahmen."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HexagonGeometry:
    """Geometrie eines regulaeren Sechsecks.

    Flat-Top: Flache Seiten oben/unten, Ecken links/rechts.
    Pointy-Top: Ecken oben/unten, flache Seiten links/rechts.
    """

    circumradius_mm: float = 50.9  # Mittelpunkt bis Ecke (innere Rahmenoeffnung, aus STL-Analyse)
    pointy_top: bool = False

    @property
    def winkel(self) -> list[int]:
        """Vertex-Winkel je nach Orientierung."""
        if self.pointy_top:
            return [30, 90, 150, 210, 270, 330]
        return [0, 60, 120, 180, 240, 300]

    @property
    def apothem_mm(self) -> float:
        """Mittelpunkt bis Seitenmitte (= circumradius * cos(30°))."""
        return self.circumradius_mm * math.cos(math.radians(30))

    @property
    def breite_mm(self) -> float:
        """Breite des Sechsecks (horizontal)."""
        if self.pointy_top:
            return 2 * self.apothem_mm  # Flat-to-Flat horizontal
        return 2 * self.circumradius_mm  # Ecke-zu-Ecke horizontal

    @property
    def hoehe_mm(self) -> float:
        """Hoehe des Sechsecks (vertikal)."""
        if self.pointy_top:
            return 2 * self.circumradius_mm  # Ecke-zu-Ecke vertikal
        return 2 * self.apothem_mm  # Flat-to-Flat vertikal

    @property
    def kantenlaenge_mm(self) -> float:
        """Seitenlaenge = Umkreisradius bei regulaerem Sechseck."""
        return self.circumradius_mm

    def vertices_mm(self, cx: float = 0, cy: float = 0) -> list[tuple[float, float]]:
        """6 Eckpunkte in mm."""
        return [
            (
                cx + self.circumradius_mm * math.cos(math.radians(w)),
                cy + self.circumradius_mm * math.sin(math.radians(w)),
            )
            for w in self.winkel
        ]

    def vertices_px(
        self, cx: float, cy: float, dpi: float = 300
    ) -> list[tuple[float, float]]:
        """Eckpunkte in Pixelkoordinaten bei gegebener DPI."""
        r_px = self.mm_to_px(self.circumradius_mm, dpi)
        return [
            (
                cx + r_px * math.cos(math.radians(w)),
                cy + r_px * math.sin(math.radians(w)),
            )
            for w in self.winkel
        ]

    def bounding_box_px(self, dpi: float = 300) -> tuple[int, int]:
        """(breite, hoehe) in Pixeln bei gegebener DPI."""
        return (
            self.mm_to_px(self.breite_mm, dpi),
            self.mm_to_px(self.hoehe_mm, dpi),
        )

    @staticmethod
    def mm_to_px(mm: float, dpi: float = 300) -> int:
        """Konvertiert Millimeter in Pixel."""
        return round(mm / 25.4 * dpi)

    @staticmethod
    def px_to_mm(px: float, dpi: float = 300) -> float:
        """Konvertiert Pixel in Millimeter."""
        return px * 25.4 / dpi
