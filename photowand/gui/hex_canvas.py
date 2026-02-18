"""Interaktives Hexagon-Slot-Widget mit Zoom und Pan."""

import math
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

from photowand.core.hexagon import HexagonGeometry
from photowand.models import HexSlotData


class HexSlotCanvas(tk.Canvas):
    """Canvas-Widget fuer einen einzelnen Hexagon-Slot.

    Unterstuetzt:
    - Mausrad: Zoom
    - Linke Maustaste + Ziehen: Pan
    - Doppelklick: Zuruecksetzen
    """

    def __init__(
        self,
        master,
        slot_index: int,
        hex_geo: HexagonGeometry,
        vorschau_groesse: int = 160,
        on_klick: callable = None,
        on_rechtsklick: callable = None,
        **kwargs,
    ):
        self._groesse = vorschau_groesse
        hl_thick = 2 if vorschau_groesse >= 60 else 1
        super().__init__(
            master,
            width=vorschau_groesse,
            height=vorschau_groesse,
            bg="#2b2b2b",
            highlightthickness=hl_thick,
            highlightbackground="#555555",
            **kwargs,
        )

        self.slot_index = slot_index
        self.hex_geo = hex_geo
        self._on_klick = on_klick
        self._on_rechtsklick = on_rechtsklick

        # Slot-Daten
        self._slot_data = HexSlotData(slot_index=slot_index)
        self._foto_original: Image.Image | None = None
        self._tk_bild: ImageTk.PhotoImage | None = None

        # Pan-Zustand
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Skalierungsfaktor: Vorschau-Pixel pro mm
        # Hexagon fuellt 85% des Widgets, Rand drumherum
        self._padding = 0.85
        self._scale = vorschau_groesse * self._padding / self.hex_geo.breite_mm
        self._r_preview = self.hex_geo.circumradius_mm * self._scale

        # Events binden
        self.bind("<Button-1>", self._on_maus_klick)
        self.bind("<B1-Motion>", self._on_ziehen)
        self.bind("<ButtonRelease-1>", self._on_ziehen_ende)
        self.bind("<Double-Button-1>", self._on_doppelklick)
        self.bind("<MouseWheel>", self._on_mausrad)
        self.bind("<Button-3>", self._on_rechtsklick_event)

        # Initial: leeren Slot zeichnen
        self._zeichne_leer()

    @property
    def ist_belegt(self) -> bool:
        return self._slot_data.ist_belegt

    def get_slot_data(self) -> HexSlotData:
        """Gibt die aktuellen Slot-Daten zurueck."""
        return self._slot_data

    def foto_setzen(self, bild: Image.Image, pfad: str | None = None) -> None:
        """Setzt ein Foto in diesen Slot."""
        self._foto_original = bild.copy()
        self._slot_data.foto_bild = bild
        self._slot_data.foto_pfad = pfad
        self._slot_data.zoom = 1.0
        self._slot_data.offset_x = 0.0
        self._slot_data.offset_y = 0.0
        self._vorschau_aktualisieren()

    def foto_entfernen(self) -> None:
        """Entfernt das Foto aus diesem Slot."""
        self._foto_original = None
        self._slot_data.foto_bild = None
        self._slot_data.foto_pfad = None
        self._slot_data.zoom = 1.0
        self._slot_data.offset_x = 0.0
        self._slot_data.offset_y = 0.0
        self._tk_bild = None
        self._zeichne_leer()

    def zuruecksetzen(self) -> None:
        """Setzt Zoom und Offset zurueck, behält aber das Foto."""
        if self._foto_original is not None:
            self._slot_data.zoom = 1.0
            self._slot_data.offset_x = 0.0
            self._slot_data.offset_y = 0.0
            self._vorschau_aktualisieren()

    def groesse_aendern(self, neue_groesse: int) -> None:
        """Aendert die Anzeigegröße des Slots dynamisch (fuer Vorschau-Zoom)."""
        self._groesse = neue_groesse
        self._scale = neue_groesse * self._padding / self.hex_geo.breite_mm
        self._r_preview = self.hex_geo.circumradius_mm * self._scale
        hl_thick = 2 if neue_groesse >= 60 else 1
        self.configure(
            width=neue_groesse, height=neue_groesse, highlightthickness=hl_thick
        )
        if self._foto_original is not None:
            self._vorschau_aktualisieren()
        else:
            self._zeichne_leer()

    def markieren(self, aktiv: bool) -> None:
        """Markiert/demarkiert den Slot visuell."""
        farbe = "#1F6AA5" if aktiv else "#555555"
        self.configure(highlightbackground=farbe)

    def _zeichne_leer(self) -> None:
        """Zeichnet einen leeren Slot mit Hexagon-Umriss."""
        self.delete("all")

        cx = self._groesse / 2
        cy = self._groesse / 2
        r = self._r_preview

        vertices = [
            (
                cx + r * math.cos(math.radians(w)),
                cy + r * math.sin(math.radians(w)),
            )
            for w in [0, 60, 120, 180, 240, 300]
        ]

        self.create_polygon(
            vertices,
            outline="#666666",
            fill="",
            width=2,
            dash=(5, 3),
        )

        font_size = max(8, int(self._groesse * 0.12))
        self.create_text(
            cx,
            cy,
            text=f"{self.slot_index + 1}",
            fill="#666666",
            font=("Segoe UI", font_size, "bold"),
        )

    def _vorschau_aktualisieren(self) -> None:
        """Aktualisiert die Vorschau-Anzeige.

        Algorithmus ist identisch zum Renderer (renderer.py),
        nur auf Vorschau-Pixelgroesse skaliert statt 300 DPI.
        """
        if self._foto_original is None:
            self._zeichne_leer()
            return

        groesse = self._groesse
        foto = self._foto_original
        r = self._r_preview

        # Hex-Bounding-Box in Vorschau-Pixel (identisch zum Renderer)
        hex_bb_w = round(self.hex_geo.breite_mm * self._scale)
        hex_bb_h = round(self.hex_geo.hoehe_mm * self._scale)

        # Cover-Fit auf Hex-Bounding-Box (nicht auf Quadrat!)
        scale_base = max(hex_bb_w / foto.width, hex_bb_h / foto.height)
        scale = scale_base * self._slot_data.zoom

        new_w = max(1, round(foto.width * scale))
        new_h = max(1, round(foto.height * scale))
        foto_skaliert = foto.resize((new_w, new_h), Image.LANCZOS)

        # Offset in Vorschau-Pixel umrechnen
        offset_x_px = round(self._slot_data.offset_x * self._scale)
        offset_y_px = round(self._slot_data.offset_y * self._scale)

        # Ausschnitt in Hex-BB-Groesse berechnen (zentriert + Offset)
        crop_cx = new_w // 2 - offset_x_px
        crop_cy = new_h // 2 - offset_y_px
        crop_x1 = crop_cx - hex_bb_w // 2
        crop_y1 = crop_cy - hex_bb_h // 2

        ausschnitt = Image.new("RGB", (hex_bb_w, hex_bb_h), (43, 43, 43))
        paste_x = max(0, -crop_x1)
        paste_y = max(0, -crop_y1)
        src_x1 = max(0, crop_x1)
        src_y1 = max(0, crop_y1)
        src_x2 = min(new_w, crop_x1 + hex_bb_w)
        src_y2 = min(new_h, crop_y1 + hex_bb_h)

        if src_x2 > src_x1 and src_y2 > src_y1:
            teil = foto_skaliert.crop((src_x1, src_y1, src_x2, src_y2))
            ausschnitt.paste(teil, (paste_x, paste_y))

        # Hexagonale Maske innerhalb Bounding-Box
        cx_hex = hex_bb_w / 2
        cy_hex = hex_bb_h / 2
        maske = Image.new("L", (hex_bb_w, hex_bb_h), 0)
        draw = ImageDraw.Draw(maske)
        hex_vertices = [
            (
                cx_hex + r * math.cos(math.radians(w)),
                cy_hex + r * math.sin(math.radians(w)),
            )
            for w in [0, 60, 120, 180, 240, 300]
        ]
        draw.polygon(hex_vertices, fill=255)

        # Maskiertes Hex-Bild
        hex_bild = Image.new("RGB", (hex_bb_w, hex_bb_h), (43, 43, 43))
        hex_bild.paste(ausschnitt, (0, 0), maske)

        # Auf Canvas zentrieren
        hintergrund = Image.new("RGB", (groesse, groesse), (43, 43, 43))
        ox = (groesse - hex_bb_w) // 2
        oy = (groesse - hex_bb_h) // 2
        hintergrund.paste(hex_bild, (ox, oy))

        # Hexagon-Umriss zeichnen
        draw_bg = ImageDraw.Draw(hintergrund)
        canvas_vertices = [
            (
                ox + cx_hex + r * math.cos(math.radians(w)),
                oy + cy_hex + r * math.sin(math.radians(w)),
            )
            for w in [0, 60, 120, 180, 240, 300]
        ]
        draw_bg.polygon(canvas_vertices, outline="#888888", width=1)

        self._tk_bild = ImageTk.PhotoImage(hintergrund)
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._tk_bild)

    def _on_maus_klick(self, event: tk.Event) -> None:
        """Start des Ziehens oder Slot-Auswahl."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        if self._on_klick:
            self._on_klick(self.slot_index)

    def _on_ziehen(self, event: tk.Event) -> None:
        """Pan: Foto im Hexagon verschieben."""
        if self._foto_original is None:
            return

        dx_px = event.x - self._drag_start_x
        dy_px = event.y - self._drag_start_y
        self._drag_start_x = event.x
        self._drag_start_y = event.y

        # Pixel-Delta in mm umrechnen
        self._slot_data.offset_x += dx_px / self._scale
        self._slot_data.offset_y += dy_px / self._scale

        self._vorschau_aktualisieren()

    def _on_ziehen_ende(self, event: tk.Event) -> None:
        """Ende des Ziehens."""
        pass

    def _on_doppelklick(self, event: tk.Event) -> None:
        """Zoom und Offset zuruecksetzen."""
        self.zuruecksetzen()

    def _on_mausrad(self, event: tk.Event) -> None:
        """Zoom per Mausrad (nur ohne Ctrl — Ctrl ist Vorschau-Zoom)."""
        if event.state & 0x4:  # Ctrl gehalten → Vorschau-Zoom
            return
        if self._foto_original is None:
            return

        if event.delta > 0:
            self._slot_data.zoom *= 1.1
        else:
            self._slot_data.zoom /= 1.1

        # Zoom begrenzen
        self._slot_data.zoom = max(0.3, min(5.0, self._slot_data.zoom))
        self._vorschau_aktualisieren()

    def _on_rechtsklick_event(self, event: tk.Event) -> None:
        """Rechtsklick → Kontextmenue anzeigen."""
        if self._on_rechtsklick:
            self._on_rechtsklick(self.slot_index, event)
