"""A4-Renderer: Erzeugt das finale 300-DPI-Druckbild."""

import math
from PIL import Image, ImageDraw
from photowand.core.hexagon import HexagonGeometry
from photowand.core.layout import LayoutEngine, HexSlotPosition
from photowand.models import HexSlotData


class A4Renderer:
    """Erzeugt das finale Druckbild mit allen hexagonal geclippten Fotos."""

    def __init__(
        self,
        layout: LayoutEngine | None = None,
        hex_geo: HexagonGeometry | None = None,
        dpi: int = 300,
    ):
        self.hex = hex_geo or HexagonGeometry()
        self.layout = layout or LayoutEngine(self.hex, dpi)
        self.dpi = dpi

    def render(
        self,
        slots: list[HexSlotData],
        schnittlinien: bool = True,
    ) -> Image.Image:
        """Erzeugt ein A4-Druckbild mit allen belegten Hexagon-Slots.

        Args:
            slots: Liste der 6 Slot-Daten (belegt oder leer).
            schnittlinien: Wenn True, werden Schnittlinien gezeichnet.

        Returns:
            RGBA-Bild in A4-Groesse bei self.dpi.
        """
        breite, hoehe = self.layout.seiten_groesse_px()
        canvas = Image.new("RGB", (breite, hoehe), "white")
        positionen = self.layout.berechne_positionen()

        for slot in slots:
            if not slot.ist_belegt or slot.foto_bild is None:
                continue

            pos = positionen[slot.slot_index]
            cx = HexagonGeometry.mm_to_px(pos.center_x_mm, self.dpi)
            cy = HexagonGeometry.mm_to_px(pos.center_y_mm, self.dpi)

            hex_bild = self._foto_in_hexagon(slot)
            # Einfuegen auf Canvas (zentriert)
            bb_w, bb_h = self.hex.bounding_box_px(self.dpi)
            paste_x = cx - bb_w // 2
            paste_y = cy - bb_h // 2

            # RGBA compositing
            if hex_bild.mode == "RGBA":
                canvas.paste(hex_bild, (paste_x, paste_y), hex_bild)
            else:
                canvas.paste(hex_bild, (paste_x, paste_y))

        if schnittlinien:
            self._zeichne_schnittlinien(canvas, positionen)

        return canvas

    def render_und_speichern(
        self,
        slots: list[HexSlotData],
        pfad: str,
        schnittlinien: bool = True,
        qualitaet: int = 95,
    ) -> None:
        """Rendert und speichert das Druckbild."""
        bild = self.render(slots, schnittlinien)
        if pfad.lower().endswith(".png"):
            bild.save(pfad, "PNG")
        else:
            bild.save(pfad, "JPEG", quality=qualitaet)

    def _foto_in_hexagon(self, slot: HexSlotData) -> Image.Image:
        """Clippt ein Foto hexagonal mit Zoom und Offset."""
        foto = slot.foto_bild
        bb_w, bb_h = self.hex.bounding_box_px(self.dpi)
        r_px = HexagonGeometry.mm_to_px(self.hex.circumradius_mm, self.dpi)

        # Cover-Fit-Skalierung: Foto fuellt das Hexagon-Bounding-Box
        scale_base = max(bb_w / foto.width, bb_h / foto.height)
        scale = scale_base * slot.zoom

        new_w = max(1, round(foto.width * scale))
        new_h = max(1, round(foto.height * scale))
        foto_skaliert = foto.resize((new_w, new_h), Image.LANCZOS)

        # Offset in Pixel umrechnen
        offset_x_px = HexagonGeometry.mm_to_px(slot.offset_x, self.dpi)
        offset_y_px = HexagonGeometry.mm_to_px(slot.offset_y, self.dpi)

        # Ausschnitt berechnen (zentriert + Offset)
        crop_cx = new_w // 2 - offset_x_px
        crop_cy = new_h // 2 - offset_y_px
        crop_x1 = crop_cx - bb_w // 2
        crop_y1 = crop_cy - bb_h // 2
        crop_x2 = crop_x1 + bb_w
        crop_y2 = crop_y1 + bb_h

        # Sicherstellung, dass der Crop innerhalb des Bildes liegt
        ausschnitt = Image.new("RGB", (bb_w, bb_h), (255, 255, 255))
        paste_x = max(0, -crop_x1)
        paste_y = max(0, -crop_y1)
        src_x1 = max(0, crop_x1)
        src_y1 = max(0, crop_y1)
        src_x2 = min(new_w, crop_x2)
        src_y2 = min(new_h, crop_y2)

        if src_x2 > src_x1 and src_y2 > src_y1:
            teil = foto_skaliert.crop((src_x1, src_y1, src_x2, src_y2))
            ausschnitt.paste(teil, (paste_x, paste_y))

        # Hexagonale Maske erstellen
        maske = self._erstelle_hex_maske(bb_w, bb_h, r_px)

        # Compositing
        ergebnis = Image.new("RGBA", (bb_w, bb_h), (0, 0, 0, 0))
        ergebnis.paste(ausschnitt, (0, 0))
        ergebnis.putalpha(maske)
        return ergebnis

    def _erstelle_hex_maske(self, breite: int, hoehe: int, r_px: int) -> Image.Image:
        """Erstellt eine Hexagon-Maske (L-Mode, weiss = sichtbar)."""
        maske = Image.new("L", (breite, hoehe), 0)
        draw = ImageDraw.Draw(maske)

        cx = breite / 2
        cy = hoehe / 2
        vertices = [
            (
                cx + r_px * math.cos(math.radians(winkel)),
                cy + r_px * math.sin(math.radians(winkel)),
            )
            for winkel in [0, 60, 120, 180, 240, 300]
        ]
        draw.polygon(vertices, fill=255)
        return maske

    def _zeichne_schnittlinien(
        self, canvas: Image.Image, positionen: list[HexSlotPosition]
    ) -> None:
        """Zeichnet duenne graue Schnittlinien um jedes Hexagon."""
        draw = ImageDraw.Draw(canvas)
        r_px = HexagonGeometry.mm_to_px(self.hex.circumradius_mm, self.dpi)

        for pos in positionen:
            cx = HexagonGeometry.mm_to_px(pos.center_x_mm, self.dpi)
            cy = HexagonGeometry.mm_to_px(pos.center_y_mm, self.dpi)

            vertices = [
                (
                    cx + r_px * math.cos(math.radians(winkel)),
                    cy + r_px * math.sin(math.radians(winkel)),
                )
                for winkel in [0, 60, 120, 180, 240, 300]
            ]
            # Geschlossenes Polygon
            draw.polygon(vertices, outline=(180, 180, 180), width=1)
