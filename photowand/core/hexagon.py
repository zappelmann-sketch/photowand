"""Hexagon-Geometrie fuer den sechseckigen Bilderrahmen."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HexagonGeometry:
    """Geometrie eines regulaeren Sechsecks in Flat-Top-Orientierung.

    Flat-Top: Flache Seiten oben/unten, Ecken links/rechts.
    Vertices bei 0, 60, 120, 180, 240, 300 Grad.
    """

    circumradius_mm: float = 49.9  # Mittelpunkt bis Ecke (aus STL-Analyse)

    @property
    def apothem_mm(self) -> float:
        """Mittelpunkt bis Seitenmitte (= circumradius * cos(30°))."""
        return self.circumradius_mm * math.cos(math.radians(30))

    @property
    def breite_mm(self) -> float:
        """Breite (Ecke-zu-Ecke, horizontal bei Flat-Top)."""
        return 2 * self.circumradius_mm

    @property
    def hoehe_mm(self) -> float:
        """Hoehe (Flat-to-Flat, vertikal bei Flat-Top)."""
        return 2 * self.apothem_mm

    @property
    def kantenlaenge_mm(self) -> float:
        """Seitenlaenge = Umkreisradius bei regulaerem Sechseck."""
        return self.circumradius_mm

    def vertices_mm(self, cx: float = 0, cy: float = 0) -> list[tuple[float, float]]:
        """6 Eckpunkte, Flat-Top, Start bei 0 Grad (rechts)."""
        return [
            (
                cx + self.circumradius_mm * math.cos(math.radians(winkel)),
                cy + self.circumradius_mm * math.sin(math.radians(winkel)),
            )
            for winkel in [0, 60, 120, 180, 240, 300]
        ]

    def vertices_px(
        self, cx: float, cy: float, dpi: float = 300
    ) -> list[tuple[float, float]]:
        """Eckpunkte in Pixelkoordinaten bei gegebener DPI."""
        r_px = self.mm_to_px(self.circumradius_mm, dpi)
        return [
            (
                cx + r_px * math.cos(math.radians(winkel)),
                cy + r_px * math.sin(math.radians(winkel)),
            )
            for winkel in [0, 60, 120, 180, 240, 300]
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
