"""Vorschau-Panel: Zeigt die Seite mit Hexagon-Slots.

Ctrl+Mausrad: Vorschau vergroessern/verkleinern
Mittlere Maustaste + Ziehen: Ansicht verschieben
Mausrad auf Hintergrund: vertikal scrollen
"""

import tkinter as tk
import customtkinter as ctk

from photowand.core.hexagon import HexagonGeometry
from photowand.core.layout import LayoutEngine
from photowand.gui.hex_canvas import HexSlotCanvas


# Maximale Hoehe der Vorschau in Pixeln (bei Zoom 1.0)
MAX_VORSCHAU_HOEHE = 650


class PreviewPanel(ctk.CTkFrame):
    """Zeigt die Seitenvorschau mit interaktiven Hexagon-Slots.

    Unterstuetzt Zoom (Ctrl+Mausrad) und Pan (mittlere Maustaste)
    fuer grosse Formate wie A0.
    """

    def __init__(
        self,
        master,
        hex_geo: HexagonGeometry,
        layout_engine: LayoutEngine,
        on_slot_klick: callable = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.hex_geo = hex_geo
        self.layout = layout_engine
        self._on_slot_klick = on_slot_klick
        self._slots: list[HexSlotCanvas] = []
        self._a4_frame: ctk.CTkFrame | None = None
        self._vorschau_zoom = 1.0
        self._canvas_window_id = None
        self._tausch_quelle: int | None = None  # Slot-Index fuer Tausch
        self._on_zustand_sichern: callable = None  # Callback fuer Undo

        # Scrollbare Flaeche
        self._scroll_canvas = tk.Canvas(
            self, bg="#2b2b2b", highlightthickness=0
        )
        self._v_scroll = tk.Scrollbar(
            self, orient="vertical", command=self._scroll_canvas.yview
        )
        self._h_scroll = tk.Scrollbar(
            self, orient="horizontal", command=self._scroll_canvas.xview
        )
        self._scroll_canvas.configure(
            yscrollcommand=self._v_scroll.set,
            xscrollcommand=self._h_scroll.set,
        )

        # Layout: Canvas + Scrollbars
        self._scroll_canvas.grid(row=0, column=0, sticky="nsew")
        self._v_scroll.grid(row=0, column=1, sticky="ns")
        self._h_scroll.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Event-Bindings auf Canvas-Hintergrund
        self._scroll_canvas.bind("<Control-MouseWheel>", self._on_vorschau_zoom)
        self._scroll_canvas.bind("<MouseWheel>", self._on_scroll_vertikal)
        self._scroll_canvas.bind("<Shift-MouseWheel>", self._on_scroll_horizontal)
        self._scroll_canvas.bind("<ButtonPress-2>", self._on_pan_start)
        self._scroll_canvas.bind("<B2-Motion>", self._on_pan_move)
        self._scroll_canvas.bind("<Configure>", self._on_canvas_groesse)

        self._erstelle_layout()

    # --- Slot-Groesse ---

    def _berechne_basis_slot_groesse(self) -> int:
        """Basis-Slot-Groesse (Zoom=1.0), passend fuer den Bildschirm."""
        zeilen = self.layout.zeilen
        spalten = self.layout.spalten

        verfuegbar_h = MAX_VORSCHAU_HOEHE - 40
        slot_h = int(verfuegbar_h / (zeilen * 1.15))
        verfuegbar_b = 700
        slot_b = int(verfuegbar_b / (spalten * 1.15))

        groesse = min(slot_h, slot_b)
        return max(30, min(160, groesse))

    def _berechne_slot_groesse(self) -> int:
        """Slot-Groesse mit aktuellem Zoom-Faktor."""
        basis = self._berechne_basis_slot_groesse()
        return max(30, int(basis * self._vorschau_zoom))

    # --- Layout ---

    def _erstelle_layout(self) -> None:
        """Erstellt das Raster aus HexSlotCanvas-Widgets."""
        slot_groesse = self._berechne_slot_groesse()

        self._a4_frame = ctk.CTkFrame(
            self._scroll_canvas,
            fg_color="white",
            corner_radius=4,
            border_width=1,
            border_color="gray60",
        )

        spalten = self.layout.spalten
        zeilen = self.layout.zeilen

        grid_pad = max(2, int(slot_groesse * 0.05))
        for col in range(spalten):
            self._a4_frame.grid_columnconfigure(col, weight=1, pad=grid_pad)
        for row in range(zeilen):
            self._a4_frame.grid_rowconfigure(row, weight=1, pad=grid_pad)

        positionen = self.layout.berechne_positionen()
        for pos in positionen:
            slot = HexSlotCanvas(
                self._a4_frame,
                slot_index=pos.index,
                hex_geo=self.hex_geo,
                vorschau_groesse=slot_groesse,
                on_klick=self._slot_klick_handler,
                on_rechtsklick=self._on_slot_rechtsklick,
            )
            slot_pad = max(1, int(slot_groesse * 0.06))
            slot.grid(
                row=pos.row,
                column=pos.col,
                padx=slot_pad,
                pady=slot_pad,
            )
            self._slots.append(slot)

            # Ctrl+Scroll auf Slots → Vorschau-Zoom
            slot.bind("<Control-MouseWheel>", self._on_vorschau_zoom)

        # Bindings auf A4-Frame-Hintergrund (weisse Flaeche zwischen Slots)
        self._a4_frame.bind("<Control-MouseWheel>", self._on_vorschau_zoom)
        self._a4_frame.bind("<MouseWheel>", self._on_scroll_vertikal)
        self._a4_frame.bind("<Shift-MouseWheel>", self._on_scroll_horizontal)

        # Frame in Canvas platzieren
        self._canvas_window_id = self._scroll_canvas.create_window(
            0, 0, window=self._a4_frame, anchor="nw"
        )

        # Scroll-Region nach Idle aktualisieren
        self.after_idle(self._aktualisiere_scroll_region)

    def _aktualisiere_scroll_region(self) -> None:
        """Aktualisiert die Scroll-Region und zentriert das Frame."""
        if self._a4_frame is None or self._canvas_window_id is None:
            return

        self._a4_frame.update_idletasks()
        frame_w = self._a4_frame.winfo_reqwidth()
        frame_h = self._a4_frame.winfo_reqheight()
        canvas_w = max(1, self._scroll_canvas.winfo_width())
        canvas_h = max(1, self._scroll_canvas.winfo_height())

        # Zentrieren wenn Frame kleiner als Canvas
        x = max(20, (canvas_w - frame_w) // 2)
        y = max(20, (canvas_h - frame_h) // 2)
        self._scroll_canvas.coords(self._canvas_window_id, x, y)

        sr_w = max(canvas_w, frame_w + 2 * x)
        sr_h = max(canvas_h, frame_h + 2 * y)
        self._scroll_canvas.configure(scrollregion=(0, 0, sr_w, sr_h))

    def _on_canvas_groesse(self, event) -> None:
        """Canvas-Groesse geaendert → neu zentrieren."""
        self._aktualisiere_scroll_region()

    # --- Vorschau-Zoom (Ctrl+Mausrad) ---

    def _on_vorschau_zoom(self, event) -> str:
        """Ctrl+Mausrad: Vorschau zoomen."""
        alter_zoom = self._vorschau_zoom
        if event.delta > 0:
            self._vorschau_zoom = min(5.0, self._vorschau_zoom * 1.15)
        else:
            self._vorschau_zoom = max(1.0, self._vorschau_zoom / 1.15)

        if abs(self._vorschau_zoom - alter_zoom) < 0.01:
            return "break"

        neue_groesse = self._berechne_slot_groesse()
        slot_pad = max(1, int(neue_groesse * 0.06))
        grid_pad = max(2, int(neue_groesse * 0.05))

        # Alle Slots resizen (ohne Neuaufbau)
        for slot in self._slots:
            slot.groesse_aendern(neue_groesse)
            slot.grid_configure(padx=slot_pad, pady=slot_pad)

        # Grid-Padding aktualisieren
        spalten = self.layout.spalten
        zeilen = self.layout.zeilen
        for col in range(spalten):
            self._a4_frame.grid_columnconfigure(col, pad=grid_pad)
        for row in range(zeilen):
            self._a4_frame.grid_rowconfigure(row, pad=grid_pad)

        self.after_idle(self._aktualisiere_scroll_region)
        return "break"

    # --- Scrolling / Panning ---

    def _on_scroll_vertikal(self, event) -> str:
        """Mausrad auf Hintergrund: vertikal scrollen."""
        self._scroll_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        return "break"

    def _on_scroll_horizontal(self, event) -> str:
        """Shift+Mausrad: horizontal scrollen."""
        self._scroll_canvas.xview_scroll(-1 * (event.delta // 120), "units")
        return "break"

    def _on_pan_start(self, event) -> None:
        """Mittlere Maustaste: Verschieben starten."""
        self._scroll_canvas.scan_mark(event.x, event.y)

    def _on_pan_move(self, event) -> None:
        """Mittlere Maustaste: Ansicht verschieben."""
        self._scroll_canvas.scan_dragto(event.x, event.y, gain=1)

    # --- Kontextmenue / Tausch (Features 3 & 5) ---

    def _slot_klick_handler(self, slot_index: int) -> None:
        """Interner Klick-Handler: entweder Tausch oder normaler Klick."""
        if self._tausch_quelle is not None:
            # Tausch ausfuehren
            self._tausch_ausfuehren(slot_index)
        elif self._on_slot_klick:
            self._on_slot_klick(slot_index)

    def _on_slot_rechtsklick(self, slot_index: int, event) -> None:
        """Zeigt das Kontextmenue fuer einen Slot."""
        slot = self._slots[slot_index]
        menu = tk.Menu(self, tearoff=0)

        if slot.ist_belegt:
            menu.add_command(
                label="Foto entfernen",
                command=lambda: self._slot_foto_entfernen(slot_index),
            )
            menu.add_command(
                label="Zoom/Position zurücksetzen",
                command=lambda: slot.zuruecksetzen(),
            )
            menu.add_separator()
            menu.add_command(
                label="Tauschen mit...",
                command=lambda: self._tausch_starten(slot_index),
            )
        else:
            menu.add_command(label="(Slot leer)", state="disabled")

        menu.tk_popup(event.x_root, event.y_root)

    def _slot_foto_entfernen(self, slot_index: int) -> None:
        """Entfernt das Foto aus einem Slot (mit Undo)."""
        if self._on_zustand_sichern:
            self._on_zustand_sichern()
        self._slots[slot_index].foto_entfernen()

    def _tausch_starten(self, slot_index: int) -> None:
        """Startet den Tausch-Modus: naechster Klick tauscht."""
        self._tausch_quelle = slot_index
        # Alle anderen Slots markieren
        for slot in self._slots:
            if slot.slot_index != slot_index:
                slot.markieren(True)
        self._slots[slot_index].configure(highlightbackground="#FFD700")

    def _tausch_ausfuehren(self, ziel_index: int) -> None:
        """Tauscht die Fotos zweier Slots."""
        quelle_idx = self._tausch_quelle
        self._tausch_quelle = None
        self.markierung_aufheben()

        if quelle_idx == ziel_index:
            return

        if self._on_zustand_sichern:
            self._on_zustand_sichern()

        slot_a = self._slots[quelle_idx]
        slot_b = self._slots[ziel_index]

        # Daten zwischenspeichern
        a_foto = slot_a._foto_original.copy() if slot_a._foto_original else None
        a_pfad = slot_a._slot_data.foto_pfad
        a_zoom = slot_a._slot_data.zoom
        a_ox = slot_a._slot_data.offset_x
        a_oy = slot_a._slot_data.offset_y

        b_foto = slot_b._foto_original.copy() if slot_b._foto_original else None
        b_pfad = slot_b._slot_data.foto_pfad
        b_zoom = slot_b._slot_data.zoom
        b_ox = slot_b._slot_data.offset_x
        b_oy = slot_b._slot_data.offset_y

        # Tauschen
        slot_a.foto_entfernen()
        slot_b.foto_entfernen()

        if b_foto:
            slot_a.foto_setzen(b_foto, b_pfad)
            slot_a._slot_data.zoom = b_zoom
            slot_a._slot_data.offset_x = b_ox
            slot_a._slot_data.offset_y = b_oy
            slot_a._vorschau_aktualisieren()

        if a_foto:
            slot_b.foto_setzen(a_foto, a_pfad)
            slot_b._slot_data.zoom = a_zoom
            slot_b._slot_data.offset_x = a_ox
            slot_b._slot_data.offset_y = a_oy
            slot_b._vorschau_aktualisieren()

    # --- Oeffentliche Methoden ---

    def format_aktualisieren(self) -> None:
        """Zerstoert alle Slots und baut das Layout neu auf."""
        if self._a4_frame is not None:
            self._a4_frame.destroy()
            self._a4_frame = None
        self._slots.clear()
        self._vorschau_zoom = 1.0
        self._erstelle_layout()

    def slot_abrufen(self, index: int) -> HexSlotCanvas:
        """Gibt den Slot am Index zurueck."""
        return self._slots[index]

    def alle_slots(self) -> list[HexSlotCanvas]:
        """Gibt alle Slots zurueck."""
        return self._slots

    def belegte_anzahl(self) -> int:
        """Anzahl der belegten Slots."""
        return sum(1 for s in self._slots if s.ist_belegt)

    def alle_zuruecksetzen(self) -> None:
        """Entfernt alle Fotos aus allen Slots."""
        for slot in self._slots:
            slot.foto_entfernen()

    def markierung_aufheben(self) -> None:
        """Hebt alle Slot-Markierungen auf."""
        for slot in self._slots:
            slot.markieren(False)


# Rueckwaertskompatibilitaet
A4PreviewPanel = PreviewPanel
