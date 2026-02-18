"""Photowand — Hauptfenster der Anwendung."""

import os
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
from PIL import Image

from photowand.core.hexagon import HexagonGeometry
from photowand.core.image_utils import sammle_bilder_aus_ordner, lade_bild, BILD_ENDUNGEN
from photowand.core.layout import LayoutEngine, PAPIER_FORMATE
from photowand.core.project import ProjektDaten, SlotZuweisung, projekt_speichern, projekt_laden
from photowand.core.renderer import A4Renderer
from photowand.gui.a4_preview import PreviewPanel
from photowand.gui.photo_strip import PhotoStripFrame
from photowand.gui.toolbar import ToolbarFrame
from photowand.gui.vorschau_dialog import VorschauDialog
from photowand.models import HexSlotData

# Drag & Drop (optional, falls tkinterdnd2 verfuegbar)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES

    DND_VERFUEGBAR = True
except ImportError:
    DND_VERFUEGBAR = False


class PhotowandApp(TkinterDnD.Tk if DND_VERFUEGBAR else tk.Tk):
    """Hauptfenster der Photowand-Anwendung."""

    def __init__(self):
        super().__init__()

        self.title("Photowand v1.0.3 — Hexagonale Bildrahmen")
        self.geometry("1100x800")
        self.minsize(900, 650)
        self.configure(bg="#2b2b2b")

        # Sauberes Beenden per X-Button
        self.protocol("WM_DELETE_WINDOW", self._beenden)

        # CustomTkinter Einstellungen
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Core-Komponenten
        self._hex_geo = HexagonGeometry()
        self._layout = LayoutEngine(self._hex_geo)
        self._renderer = A4Renderer(self._layout, self._hex_geo)

        # Zustand
        self._ausgewaehltes_foto: int | None = None
        self._projekt_pfad: str | None = None

        # Mehrseitig
        self._aktuelle_seite = 0
        self._seiten_daten: list[dict] = [{}]  # Liste von Slot-Zustaenden pro Seite

        # Undo-History
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

        # Ansicht-Variablen (fuer Menuleiste)
        self._schnittlinien_var = tk.BooleanVar(value=True)
        self._beschriftung_var = tk.BooleanVar(value=False)
        self._pointy_top_var = tk.BooleanVar(value=False)
        self._format_var = tk.StringVar(value="A4")

        # GUI aufbauen
        self._erstelle_menuleiste()
        self._erstelle_gui()

        # Drag & Drop einrichten
        if DND_VERFUEGBAR:
            self._init_drag_drop()

        # Tastenkuerzel
        self.bind("<Control-s>", lambda e: self._projekt_speichern())
        self.bind("<Control-o>", lambda e: self._projekt_laden())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())

    def _erstelle_menuleiste(self) -> None:
        """Erstellt die native Windows-Menuleiste."""
        self._menubar = tk.Menu(self)
        self.configure(menu=self._menubar)

        # --- Datei ---
        datei_menu = tk.Menu(self._menubar, tearoff=0)
        datei_menu.add_command(label="Fotos laden...", command=self._ordner_laden)
        datei_menu.add_separator()
        datei_menu.add_command(
            label="Projekt speichern...", command=self._projekt_speichern,
            accelerator="Strg+S",
        )
        datei_menu.add_command(
            label="Projekt öffnen...", command=self._projekt_laden,
            accelerator="Strg+O",
        )
        datei_menu.add_separator()
        datei_menu.add_command(label="Exportieren (PNG)...", command=self._exportieren)
        datei_menu.add_command(
            label="Alle Seiten exportieren...", command=self._alle_seiten_exportieren,
        )
        datei_menu.add_separator()
        datei_menu.add_command(label="Drucken", command=self._drucken)
        datei_menu.add_separator()
        datei_menu.add_command(label="Beenden", command=self._beenden)
        self._menubar.add_cascade(label="Datei", menu=datei_menu)

        # --- Bearbeiten ---
        bearbeiten_menu = tk.Menu(self._menubar, tearoff=0)
        bearbeiten_menu.add_command(
            label="Rückgängig", command=self._undo, accelerator="Strg+Z",
        )
        bearbeiten_menu.add_command(
            label="Wiederherstellen", command=self._redo, accelerator="Strg+Y",
        )
        bearbeiten_menu.add_separator()
        bearbeiten_menu.add_command(label="Auto-Fill", command=self._auto_fill)
        bearbeiten_menu.add_command(
            label="Alles zurücksetzen", command=self._zuruecksetzen,
        )
        self._menubar.add_cascade(label="Bearbeiten", menu=bearbeiten_menu)

        # --- Ansicht ---
        ansicht_menu = tk.Menu(self._menubar, tearoff=0)
        ansicht_menu.add_command(label="Vorschau", command=self._vorschau_anzeigen)
        ansicht_menu.add_separator()
        ansicht_menu.add_checkbutton(
            label="Schnittlinien", variable=self._schnittlinien_var,
        )
        ansicht_menu.add_checkbutton(
            label="Beschriftung", variable=self._beschriftung_var,
            command=self._beschriftung_umschalten,
        )
        ansicht_menu.add_separator()
        ansicht_menu.add_checkbutton(
            label="Pointy-Top Orientierung", variable=self._pointy_top_var,
            command=self._orientierung_aendern,
        )
        ansicht_menu.add_separator()

        # Format-Untermenu
        format_menu = tk.Menu(ansicht_menu, tearoff=0)
        for fmt in PAPIER_FORMATE:
            format_menu.add_radiobutton(
                label=fmt,
                variable=self._format_var,
                value=fmt,
                command=self._format_aendern_menu,
            )
        ansicht_menu.add_cascade(label="Papierformat", menu=format_menu)
        self._menubar.add_cascade(label="Ansicht", menu=ansicht_menu)

        # --- Seite ---
        seite_menu = tk.Menu(self._menubar, tearoff=0)
        seite_menu.add_command(label="Neue Seite", command=self._seite_hinzufuegen)
        seite_menu.add_command(label="Seite löschen", command=self._seite_loeschen)
        seite_menu.add_separator()
        seite_menu.add_command(label="Vorherige Seite", command=self._seite_zurueck)
        seite_menu.add_command(label="Nächste Seite", command=self._seite_vor)
        self._menubar.add_cascade(label="Seite", menu=seite_menu)

        # --- Hilfe ---
        hilfe_menu = tk.Menu(self._menubar, tearoff=0)
        hilfe_menu.add_command(label="Anleitung...", command=self._anleitung_anzeigen)
        hilfe_menu.add_separator()
        hilfe_menu.add_command(label="Über Photowand", command=self._ueber_anzeigen)
        self._menubar.add_cascade(label="Hilfe", menu=hilfe_menu)

    def _erstelle_gui(self) -> None:
        """Baut die gesamte GUI auf."""
        # Hauptcontainer
        self._main_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self._main_frame.pack(fill="both", expand=True)

        # Toolbar (nur Aktionsbuttons — Optionen sind im Menue)
        self._toolbar = ToolbarFrame(
            self._main_frame,
            callbacks={
                "ordner_laden": self._ordner_laden,
                "auto_fill": self._auto_fill,
                "projekt_speichern": self._projekt_speichern,
                "projekt_laden": self._projekt_laden,
                "vorschau": self._vorschau_anzeigen,
                "exportieren": self._exportieren,
                "alle_exportieren": self._alle_seiten_exportieren,
                "drucken": self._drucken,
                "zuruecksetzen": self._zuruecksetzen,
            },
        )
        self._toolbar.pack(fill="x", padx=0, pady=0)

        # Inhaltsbereich (Seitenleiste + Vorschau)
        self._content_frame = ctk.CTkFrame(
            self._main_frame, fg_color="transparent"
        )
        self._content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Foto-Seitenleiste (links)
        self._photo_strip = PhotoStripFrame(
            self._content_frame,
            on_foto_ausgewaehlt=self._on_foto_ausgewaehlt,
            fg_color=("#e0e0e0", "#333333"),
        )
        self._photo_strip.pack(side="left", fill="y", padx=(5, 0), pady=5)

        # Seitenvorschau (Mitte)
        self._a4_preview = PreviewPanel(
            self._content_frame,
            hex_geo=self._hex_geo,
            layout_engine=self._layout,
            on_slot_klick=self._on_slot_klick,
        )
        self._a4_preview.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self._a4_preview._on_zustand_sichern = self._zustand_sichern

        # Statusleiste mit Seiten-Navigation
        self._status_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent", height=30)
        self._status_frame.pack(fill="x", padx=10, pady=(0, 5))

        self._status_var = tk.StringVar(value="Bereit — Ordner mit Fotos laden um zu beginnen")
        self._statusbar = ctk.CTkLabel(
            self._status_frame,
            textvariable=self._status_var,
            anchor="w",
            text_color="gray60",
            font=("Segoe UI", 12),
        )
        self._statusbar.pack(side="left", fill="x", expand=True)

        # Seiten-Navigation (rechts in Statusleiste)
        self._seiten_frame = ctk.CTkFrame(self._status_frame, fg_color="transparent")
        self._seiten_frame.pack(side="right")

        self._btn_seite_zurueck = ctk.CTkButton(
            self._seiten_frame,
            text="◀",
            width=30,
            height=24,
            corner_radius=4,
            command=self._seite_zurueck,
            fg_color="gray40",
            hover_color="gray30",
        )
        self._btn_seite_zurueck.pack(side="left", padx=2)

        self._seiten_label_var = tk.StringVar(value="Seite 1/1")
        self._seiten_label = ctk.CTkLabel(
            self._seiten_frame,
            textvariable=self._seiten_label_var,
            font=("Segoe UI", 12),
            text_color="gray60",
        )
        self._seiten_label.pack(side="left", padx=4)

        self._btn_seite_vor = ctk.CTkButton(
            self._seiten_frame,
            text="▶",
            width=30,
            height=24,
            corner_radius=4,
            command=self._seite_vor,
            fg_color="gray40",
            hover_color="gray30",
        )
        self._btn_seite_vor.pack(side="left", padx=2)

        self._btn_seite_neu = ctk.CTkButton(
            self._seiten_frame,
            text="+ Seite",
            width=60,
            height=24,
            corner_radius=4,
            command=self._seite_hinzufuegen,
            fg_color="#2D7D46",
            hover_color="#236B38",
        )
        self._btn_seite_neu.pack(side="left", padx=(6, 2))

        self._btn_seite_loeschen = ctk.CTkButton(
            self._seiten_frame,
            text="− Seite",
            width=60,
            height=24,
            corner_radius=4,
            command=self._seite_loeschen,
            fg_color="#8B3A3A",
            hover_color="#6B2A2A",
        )
        self._btn_seite_loeschen.pack(side="left", padx=(2, 0))

    def _init_drag_drop(self) -> None:
        """Richtet Drag & Drop fuer Dateien ein."""
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_datei_drop)

    # --- Foto laden ---

    def _ordner_laden(self) -> None:
        """Oeffnet einen Ordner-Dialog und laedt alle Bilder daraus."""
        ordner = filedialog.askdirectory(
            title="Ordner mit Fotos auswählen",
        )
        if not ordner:
            return

        pfade = sammle_bilder_aus_ordner(ordner)
        if not pfade:
            messagebox.showinfo(
                "Keine Bilder",
                f"Im Ordner wurden keine Bilddateien gefunden.\n\n"
                f"Unterstützte Formate: {', '.join(sorted(BILD_ENDUNGEN))}",
            )
            return

        self._fotos_importieren(pfade)

    def _fotos_importieren(self, pfade: list[str]) -> None:
        """Importiert Fotos — erstellt nur Thumbnails, Originale on-demand."""
        def fortschritt(geladen: int, gesamt: int) -> None:
            self._status_var.set(f"Lade Vorschau {geladen}/{gesamt}...")

        fehler = self._photo_strip.fotos_hinzufuegen(pfade, fortschritt)

        if fehler:
            details = "\n".join(
                f"{os.path.basename(pfad)}: {grund}" for pfad, grund in fehler[:5]
            )
            messagebox.showwarning(
                "Fehler beim Laden",
                f"{len(fehler)} Datei(en) konnten nicht geladen werden:\n\n{details}",
            )

        self._status_aktualisieren()

    def _on_datei_drop(self, event) -> None:
        """Handler fuer Drag & Drop aus dem Explorer."""
        daten = event.data
        pfade = self._parse_drop_daten(daten)

        bild_pfade = [
            p for p in pfade
            if os.path.splitext(p)[1].lower() in BILD_ENDUNGEN
        ]

        ordner_pfade = [p for p in pfade if os.path.isdir(p)]
        for ordner in ordner_pfade:
            bild_pfade.extend(sammle_bilder_aus_ordner(ordner))

        if bild_pfade:
            self._fotos_importieren(bild_pfade)

    def _parse_drop_daten(self, daten: str) -> list[str]:
        """Parst die Drop-Daten von tkinterdnd2."""
        pfade = []
        aktuell = ""
        in_klammern = False

        for zeichen in daten:
            if zeichen == "{":
                in_klammern = True
            elif zeichen == "}":
                in_klammern = False
                if aktuell:
                    pfade.append(aktuell)
                    aktuell = ""
            elif zeichen == " " and not in_klammern:
                if aktuell:
                    pfade.append(aktuell)
                    aktuell = ""
            else:
                aktuell += zeichen

        if aktuell:
            pfade.append(aktuell)

        return pfade

    # --- Auto-Fill ---

    def _auto_fill(self) -> None:
        """Weist Fotos automatisch der Reihe nach auf leere Slots zu.

        Ueberspringt Fotos, die bereits auf anderen Seiten oder der
        aktuellen Seite zugewiesen sind, damit jede Seite neue Fotos
        bekommt (z.B. Seite 1 → Fotos 1-6, Seite 2 → Fotos 7-12).
        """
        foto_anz = self._photo_strip.foto_anzahl
        if foto_anz == 0:
            messagebox.showinfo(
                "Keine Fotos",
                "Bitte lade zuerst Fotos (Ordner laden oder Drag & Drop).",
            )
            return

        self._zustand_sichern()

        slots = self._a4_preview.alle_slots()
        leere_slots = [s for s in slots if not s.ist_belegt]
        if not leere_slots:
            messagebox.showinfo(
                "Alle belegt",
                "Alle Hexagon-Slots sind bereits belegt.",
            )
            return

        # Bereits verwendete Fotos sammeln (alle Seiten)
        self._seite_sichern()
        verwendete_pfade: set[str] = set()
        for seiten_nr, seiten_zustand in enumerate(self._seiten_daten):
            # Andere Seiten: gespeicherten Zustand nutzen
            if seiten_nr != self._aktuelle_seite:
                for daten_dict in seiten_zustand.values():
                    pfad = daten_dict.get("foto_pfad")
                    if pfad:
                        verwendete_pfade.add(os.path.normpath(pfad))

        # Aktuelle Seite: belegte Slots direkt pruefen
        for slot in slots:
            if slot.ist_belegt:
                pfad = slot._slot_data.foto_pfad
                if pfad:
                    verwendete_pfade.add(os.path.normpath(pfad))

        # Unbenutzte Fotos der Reihe nach zuweisen
        zugewiesen = 0
        foto_idx = 0
        for slot in leere_slots:
            # Naechstes unbenutztes Foto finden
            while foto_idx < foto_anz:
                kandidat_pfad = self._photo_strip.pfad_abrufen(foto_idx)
                if os.path.normpath(kandidat_pfad) not in verwendete_pfade:
                    break
                foto_idx += 1

            if foto_idx >= foto_anz:
                break

            try:
                foto = self._photo_strip.foto_laden(foto_idx)
                pfad = self._photo_strip.pfad_abrufen(foto_idx)
                slot.foto_setzen(foto, pfad)
                verwendete_pfade.add(os.path.normpath(pfad))
                zugewiesen += 1
            except Exception:
                pass
            foto_idx += 1

        if zugewiesen == 0:
            messagebox.showinfo(
                "Keine neuen Fotos",
                "Alle Fotos sind bereits auf Seiten zugewiesen.",
            )
        else:
            self._status_var.set(f"Auto-Fill: {zugewiesen} Fotos zugewiesen")
            self.after(2000, self._status_aktualisieren)

    # --- Slot-Interaktion ---

    def _on_foto_ausgewaehlt(self, foto_index: int) -> None:
        """Wird aufgerufen, wenn ein Foto in der Seitenleiste ausgewaehlt wird."""
        self._ausgewaehltes_foto = foto_index
        self._status_var.set(
            "Foto ausgewählt — Klicke auf ein Hexagon zum Zuweisen"
        )
        for slot in self._a4_preview.alle_slots():
            if not slot.ist_belegt:
                slot.markieren(True)

    def _on_slot_klick(self, slot_index: int) -> None:
        """Wird aufgerufen, wenn ein Hexagon-Slot angeklickt wird."""
        if self._ausgewaehltes_foto is not None:
            self._zustand_sichern()
            try:
                foto = self._photo_strip.foto_laden(self._ausgewaehltes_foto)
                pfad = self._photo_strip.pfad_abrufen(self._ausgewaehltes_foto)
                slot = self._a4_preview.slot_abrufen(slot_index)
                slot.foto_setzen(foto, pfad)
            except Exception as e:
                messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden:\n{e}")

            self._ausgewaehltes_foto = None
            self._photo_strip.auswahl_aufheben()
            self._a4_preview.markierung_aufheben()
            self._status_aktualisieren()

    # --- Beschriftung / Orientierung ---

    def _beschriftung_umschalten(self) -> None:
        """Schaltet die Beschriftung fuer alle Slots um."""
        aktiv = self._beschriftung_var.get()
        for slot in self._a4_preview.alle_slots():
            slot.beschriftung_sichtbar = aktiv
            slot._vorschau_aktualisieren()

    def _orientierung_aendern(self) -> None:
        """Wechselt zwischen Flat-Top und Pointy-Top Hexagon-Orientierung."""
        pointy = self._pointy_top_var.get()

        # Aktuelle Seite sichern
        self._seite_sichern()

        # Neue Geometrie erstellen
        self._hex_geo = HexagonGeometry(pointy_top=pointy)
        self._layout = LayoutEngine(self._hex_geo)
        self._renderer = A4Renderer(self._layout, self._hex_geo)

        # Format beibehalten
        fmt = self._format_var.get()
        self._layout.setze_format(fmt)

        # Preview komplett neu aufbauen
        self._a4_preview.hex_geo = self._hex_geo
        self._a4_preview.layout = self._layout
        self._a4_preview.format_aktualisieren()
        self._a4_preview._on_zustand_sichern = self._zustand_sichern

        # Aktuelle Seite wiederherstellen
        self._seite_laden_intern(self._aktuelle_seite)
        self._status_aktualisieren()

    def _format_aendern(self, format_name: str) -> None:
        """Wechselt das Papierformat und baut die Vorschau neu auf."""
        self._format_var.set(format_name)
        self._layout.setze_format(format_name)
        self._a4_preview.format_aktualisieren()
        self._ausgewaehltes_foto = None
        self._status_aktualisieren()

    def _format_aendern_menu(self) -> None:
        """Callback wenn Format im Menue geaendert wird."""
        self._format_aendern(self._format_var.get())

    # --- Projekt speichern/laden ---

    def _projekt_speichern(self) -> None:
        """Speichert das aktuelle Projekt als .photowand Datei."""
        speicher_pfad = filedialog.asksaveasfilename(
            title="Projekt speichern",
            defaultextension=".photowand",
            filetypes=[("Photowand-Projekt", "*.photowand")],
        )
        if not speicher_pfad:
            return

        # Foto-Pfade sammeln
        foto_pfade = [
            self._photo_strip.pfad_abrufen(i)
            for i in range(self._photo_strip.foto_anzahl)
        ]

        # Aktuelle Seite sichern
        self._seite_sichern()

        # Alle Slot-Zuweisungen aller Seiten sammeln
        slot_zuweisungen = []
        for seiten_nr, seiten_zustand in enumerate(self._seiten_daten):
            for slot_idx, daten_dict in seiten_zustand.items():
                idx = int(slot_idx) if isinstance(slot_idx, str) else slot_idx
                foto_pfad = daten_dict.get("foto_pfad")
                if foto_pfad:
                    slot_zuweisungen.append(SlotZuweisung(
                        slot_index=idx,
                        foto_pfad=foto_pfad,
                        zoom=daten_dict.get("zoom", 1.0),
                        offset_x=daten_dict.get("offset_x", 0.0),
                        offset_y=daten_dict.get("offset_y", 0.0),
                        seite=seiten_nr,
                        rotation=daten_dict.get("rotation", 0),
                        beschriftung=daten_dict.get("beschriftung", ""),
                    ))

        daten = ProjektDaten(
            format_name=self._layout.format_name,
            foto_pfade=foto_pfade,
            slots=slot_zuweisungen,
            pointy_top=self._hex_geo.pointy_top,
        )

        try:
            projekt_speichern(speicher_pfad, daten)
            self._projekt_pfad = speicher_pfad
            name = os.path.basename(speicher_pfad)
            self.title(f"Photowand — {name}")
            self._status_var.set(f"Projekt gespeichert: {name}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")

    def _projekt_laden(self) -> None:
        """Laedt ein Projekt aus einer .photowand Datei."""
        pfad = filedialog.askopenfilename(
            title="Projekt öffnen",
            filetypes=[("Photowand-Projekt", "*.photowand")],
        )
        if not pfad:
            return

        try:
            daten = projekt_laden(pfad)
        except Exception as e:
            messagebox.showerror("Fehler", f"Projekt konnte nicht geladen werden:\n{e}")
            return

        # Alles zuruecksetzen
        self._a4_preview.alle_zuruecksetzen()
        self._photo_strip.alle_entfernen()
        self._ausgewaehltes_foto = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._aktuelle_seite = 0
        self._seiten_daten = [{}]

        # Pointy-Top setzen
        if daten.pointy_top != self._hex_geo.pointy_top:
            self._hex_geo = HexagonGeometry(pointy_top=daten.pointy_top)
            self._layout = LayoutEngine(self._hex_geo)
            self._renderer = A4Renderer(self._layout, self._hex_geo)
            self._pointy_top_var.set(daten.pointy_top)
            self._a4_preview.hex_geo = self._hex_geo
            self._a4_preview.layout = self._layout

        # Format setzen
        self._format_aendern(daten.format_name)

        # Fotos laden (nur existierende)
        existierende = [p for p in daten.foto_pfade if os.path.isfile(p)]
        fehlende = len(daten.foto_pfade) - len(existierende)
        if existierende:
            self._fotos_importieren(existierende)

        # Slots nach Seiten gruppieren
        max_seite = max((sz.seite for sz in daten.slots), default=0)
        self._seiten_daten = [{} for _ in range(max_seite + 1)]

        fehler_slots = 0
        for sz in daten.slots:
            if not os.path.isfile(sz.foto_pfad):
                fehler_slots += 1
                continue
            seite = sz.seite
            while len(self._seiten_daten) <= seite:
                self._seiten_daten.append({})
            self._seiten_daten[seite][sz.slot_index] = {
                "foto_pfad": sz.foto_pfad,
                "zoom": sz.zoom,
                "offset_x": sz.offset_x,
                "offset_y": sz.offset_y,
                "rotation": sz.rotation,
                "beschriftung": sz.beschriftung,
            }

        # Erste Seite laden
        self._aktuelle_seite = 0
        self._seite_laden_intern(0)

        self._projekt_pfad = pfad
        name = os.path.basename(pfad)
        self.title(f"Photowand — {name}")
        self._seiten_navigation_aktualisieren()

        if fehlende > 0 or fehler_slots > 0:
            messagebox.showwarning(
                "Hinweis",
                f"Projekt geladen, aber {fehlende + fehler_slots} Datei(en) "
                f"konnten nicht gefunden werden.",
            )

        self._status_aktualisieren()

    # --- Vorschau / Export / Druck ---

    def _vorschau_anzeigen(self) -> None:
        """Zeigt eine Druck-Vorschau des gerenderten Bildes mit Seiten-Navigation."""
        self._seite_sichern()

        # Pruefen ob irgendeine Seite Inhalt hat
        hat_inhalt = any(s for s in self._seiten_daten if s)
        if not hat_inhalt and self._a4_preview.belegte_anzahl() == 0:
            messagebox.showinfo(
                "Keine Fotos",
                "Bitte weise zuerst Fotos den Hexagon-Slots zu.",
            )
            return

        schnittlinien = self._schnittlinien_var.get()
        beschriftung = self._beschriftung_var.get()
        try:
            bild = self._render_seite_bild(self._aktuelle_seite, schnittlinien, beschriftung)
            if bild is None:
                # Aktuelle Seite leer — erste nicht-leere Seite suchen
                bild = self._renderer.render(
                    self._sammle_slot_daten(),
                    schnittlinien=schnittlinien,
                    beschriftung=beschriftung,
                )

            VorschauDialog(
                self,
                bild,
                f"Druckvorschau — {self._layout.format_name}",
                seiten_anzahl=len(self._seiten_daten),
                aktuelle_seite=self._aktuelle_seite,
                render_seite=lambda seite: self._render_seite_bild(seite, schnittlinien, beschriftung),
            )
        except Exception as e:
            messagebox.showerror("Fehler", f"Vorschau fehlgeschlagen:\n{e}")

    def _render_seite_bild(
        self, seiten_nr: int, schnittlinien: bool, beschriftung: bool = False
    ) -> Image.Image | None:
        """Rendert das Druckbild fuer eine bestimmte Seite."""
        if seiten_nr < 0 or seiten_nr >= len(self._seiten_daten):
            return None

        zustand = self._seiten_daten[seiten_nr]
        if not zustand:
            return None

        slot_daten = []
        for slot in self._a4_preview.alle_slots():
            sd = HexSlotData(slot_index=slot.slot_index)
            slot_info = zustand.get(slot.slot_index)
            if slot_info and slot_info.get("foto_pfad"):
                pfad = slot_info["foto_pfad"]
                if os.path.isfile(pfad):
                    try:
                        sd.foto_bild = lade_bild(pfad)
                        sd.foto_pfad = pfad
                        sd.zoom = slot_info.get("zoom", 1.0)
                        sd.offset_x = slot_info.get("offset_x", 0.0)
                        sd.offset_y = slot_info.get("offset_y", 0.0)
                        sd.rotation = slot_info.get("rotation", 0)
                        sd.beschriftung = slot_info.get("beschriftung", "")
                    except Exception:
                        pass
            slot_daten.append(sd)

        return self._renderer.render(
            slot_daten, schnittlinien=schnittlinien, beschriftung=beschriftung
        )

    def _exportieren(self) -> None:
        """Exportiert das Druckbild als PNG."""
        if self._a4_preview.belegte_anzahl() == 0:
            messagebox.showinfo(
                "Keine Fotos",
                "Bitte weise zuerst Fotos den Hexagon-Slots zu.",
            )
            return

        pfad = filedialog.asksaveasfilename(
            title="Druckbild exportieren",
            defaultextension=".png",
            filetypes=[
                ("PNG-Bild", "*.png"),
                ("JPEG-Bild", "*.jpg"),
            ],
        )
        if not pfad:
            return

        slots = self._sammle_slot_daten()
        schnittlinien = self._schnittlinien_var.get()
        beschriftung = self._beschriftung_var.get()
        try:
            self._renderer.render_und_speichern(
                slots, pfad,
                schnittlinien=schnittlinien,
                beschriftung=beschriftung,
            )
            messagebox.showinfo(
                "Exportiert",
                f"Druckbild gespeichert:\n{pfad}",
            )
        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")

    def _drucken(self) -> None:
        """Druckt die aktuelle Seite ueber den Windows-Druckdialog."""
        if self._a4_preview.belegte_anzahl() == 0:
            messagebox.showinfo(
                "Keine Fotos",
                "Bitte weise zuerst Fotos den Hexagon-Slots zu.",
            )
            return

        slots = self._sammle_slot_daten()
        schnittlinien = self._schnittlinien_var.get()
        beschriftung = self._beschriftung_var.get()
        try:
            temp_dir = tempfile.gettempdir()
            temp_pfad = os.path.join(temp_dir, "photowand_druck.png")
            self._renderer.render_und_speichern(
                slots, temp_pfad,
                schnittlinien=schnittlinien,
                beschriftung=beschriftung,
            )

            os.startfile(temp_pfad, "print")
            self._status_var.set("Druckdialog geöffnet...")
        except Exception as e:
            messagebox.showerror("Fehler", f"Drucken fehlgeschlagen:\n{e}")

    def _alle_seiten_exportieren(self) -> None:
        """Exportiert alle Seiten als separate PNG-Dateien."""
        self._seite_sichern()
        seiten_mit_inhalt = [
            (i, s) for i, s in enumerate(self._seiten_daten) if s
        ]
        if not seiten_mit_inhalt:
            messagebox.showinfo("Keine Fotos", "Keine Seiten mit Fotos vorhanden.")
            return

        ordner = filedialog.askdirectory(title="Ordner für Export aller Seiten")
        if not ordner:
            return

        schnittlinien = self._schnittlinien_var.get()
        beschriftung = self._beschriftung_var.get()
        fmt = self._layout.format_name
        exportiert = 0

        for seiten_nr, zustand in seiten_mit_inhalt:
            # Slots fuer diese Seite aufbauen
            slot_daten = []
            for slot in self._a4_preview.alle_slots():
                sd = HexSlotData(slot_index=slot.slot_index)
                slot_info = zustand.get(slot.slot_index)
                if slot_info and slot_info.get("foto_pfad"):
                    pfad = slot_info["foto_pfad"]
                    if os.path.isfile(pfad):
                        try:
                            sd.foto_bild = lade_bild(pfad)
                            sd.foto_pfad = pfad
                            sd.zoom = slot_info.get("zoom", 1.0)
                            sd.offset_x = slot_info.get("offset_x", 0.0)
                            sd.offset_y = slot_info.get("offset_y", 0.0)
                            sd.rotation = slot_info.get("rotation", 0)
                            sd.beschriftung = slot_info.get("beschriftung", "")
                        except Exception:
                            pass
                slot_daten.append(sd)

            dateiname = f"Photowand_{fmt}_Seite{seiten_nr + 1}.png"
            ziel = os.path.join(ordner, dateiname)
            try:
                self._renderer.render_und_speichern(
                    slot_daten, ziel,
                    schnittlinien=schnittlinien,
                    beschriftung=beschriftung,
                )
                exportiert += 1
            except Exception:
                pass

        messagebox.showinfo(
            "Export abgeschlossen",
            f"{exportiert} Seite(n) exportiert nach:\n{ordner}",
        )

    def _zuruecksetzen(self) -> None:
        """Setzt alles zurueck."""
        self._a4_preview.alle_zuruecksetzen()
        self._photo_strip.alle_entfernen()
        self._ausgewaehltes_foto = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._aktuelle_seite = 0
        self._seiten_daten = [{}]
        self._projekt_pfad = None

        # Pointy-Top zuruecksetzen
        if self._hex_geo.pointy_top:
            self._hex_geo = HexagonGeometry(pointy_top=False)
            self._layout = LayoutEngine(self._hex_geo)
            self._renderer = A4Renderer(self._layout, self._hex_geo)
            self._pointy_top_var.set(False)
            self._a4_preview.hex_geo = self._hex_geo
            self._a4_preview.layout = self._layout
            self._a4_preview.format_aktualisieren()

        # Format zuruecksetzen
        self._format_aendern("A4")

        self.title("Photowand v1.0.3 — Hexagonale Bildrahmen")
        self._seiten_navigation_aktualisieren()
        self._status_var.set("Bereit — Ordner mit Fotos laden um zu beginnen")

    # --- Undo/Redo ---

    def _zustand_sichern(self) -> None:
        """Sichert den aktuellen Slot-Zustand fuer Undo."""
        zustand = {}
        for slot in self._a4_preview.alle_slots():
            data = slot.get_slot_data()
            if data.ist_belegt:
                zustand[data.slot_index] = {
                    "foto_pfad": data.foto_pfad,
                    "zoom": data.zoom,
                    "offset_x": data.offset_x,
                    "offset_y": data.offset_y,
                    "rotation": data.rotation,
                    "beschriftung": data.beschriftung,
                }
        self._undo_stack.append(zustand)
        # Maximal 30 Undo-Schritte
        if len(self._undo_stack) > 30:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self) -> None:
        """Stellt den vorherigen Zustand wieder her."""
        if not self._undo_stack:
            return

        # Aktuellen Zustand fuer Redo sichern
        aktuell = {}
        for slot in self._a4_preview.alle_slots():
            data = slot.get_slot_data()
            if data.ist_belegt:
                aktuell[data.slot_index] = {
                    "foto_pfad": data.foto_pfad,
                    "zoom": data.zoom,
                    "offset_x": data.offset_x,
                    "offset_y": data.offset_y,
                    "rotation": data.rotation,
                    "beschriftung": data.beschriftung,
                }
        self._redo_stack.append(aktuell)

        alter_zustand = self._undo_stack.pop()
        self._zustand_wiederherstellen(alter_zustand)
        self._status_var.set("Rückgängig")
        self.after(1500, self._status_aktualisieren)

    def _redo(self) -> None:
        """Stellt den naechsten Zustand wieder her (nach Undo)."""
        if not self._redo_stack:
            return

        # Aktuellen Zustand fuer Undo sichern
        aktuell = {}
        for slot in self._a4_preview.alle_slots():
            data = slot.get_slot_data()
            if data.ist_belegt:
                aktuell[data.slot_index] = {
                    "foto_pfad": data.foto_pfad,
                    "zoom": data.zoom,
                    "offset_x": data.offset_x,
                    "offset_y": data.offset_y,
                    "rotation": data.rotation,
                    "beschriftung": data.beschriftung,
                }
        self._undo_stack.append(aktuell)

        neuer_zustand = self._redo_stack.pop()
        self._zustand_wiederherstellen(neuer_zustand)
        self._status_var.set("Wiederherstellen")
        self.after(1500, self._status_aktualisieren)

    def _zustand_wiederherstellen(self, zustand: dict) -> None:
        """Stellt einen gespeicherten Slot-Zustand wieder her."""
        # Alle Slots zuruecksetzen
        for slot in self._a4_preview.alle_slots():
            slot.foto_entfernen()

        # Gespeicherte Slots wiederherstellen
        for slot_idx, daten in zustand.items():
            idx = int(slot_idx) if isinstance(slot_idx, str) else slot_idx
            if idx >= len(self._a4_preview.alle_slots()):
                continue
            pfad = daten["foto_pfad"]
            if not pfad or not os.path.isfile(pfad):
                continue
            try:
                foto = lade_bild(pfad)
                slot = self._a4_preview.slot_abrufen(idx)
                slot.foto_setzen(foto, pfad)
                slot._slot_data.zoom = daten["zoom"]
                slot._slot_data.offset_x = daten["offset_x"]
                slot._slot_data.offset_y = daten["offset_y"]
                slot._slot_data.rotation = daten.get("rotation", 0)
                slot._slot_data.beschriftung = daten.get("beschriftung", "")
                slot._vorschau_aktualisieren()
            except Exception:
                pass

    # --- Seiten-Navigation ---

    def _seite_sichern(self) -> None:
        """Sichert den aktuellen Seitenzustand."""
        zustand = {}
        for slot in self._a4_preview.alle_slots():
            data = slot.get_slot_data()
            if data.ist_belegt:
                zustand[data.slot_index] = {
                    "foto_pfad": data.foto_pfad,
                    "zoom": data.zoom,
                    "offset_x": data.offset_x,
                    "offset_y": data.offset_y,
                    "rotation": data.rotation,
                    "beschriftung": data.beschriftung,
                }
        # Seitenliste erweitern falls noetig
        while len(self._seiten_daten) <= self._aktuelle_seite:
            self._seiten_daten.append({})
        self._seiten_daten[self._aktuelle_seite] = zustand

    def _seite_laden(self, seiten_nr: int) -> None:
        """Laedt eine bestimmte Seite (sichert vorher die aktuelle)."""
        if seiten_nr < 0 or seiten_nr >= len(self._seiten_daten):
            return
        self._seite_sichern()
        self._aktuelle_seite = seiten_nr
        self._seite_laden_intern(seiten_nr)
        self._seiten_navigation_aktualisieren()
        self._status_aktualisieren()

    def _seite_laden_intern(self, seiten_nr: int) -> None:
        """Laedt eine Seite ohne vorher zu sichern (intern)."""
        # Alle Slots leeren
        for slot in self._a4_preview.alle_slots():
            slot.foto_entfernen()

        # Beschriftungszustand uebernehmen
        beschriftung_aktiv = self._beschriftung_var.get()

        # Gespeicherten Zustand wiederherstellen
        zustand = self._seiten_daten[seiten_nr] if seiten_nr < len(self._seiten_daten) else {}
        for slot_idx, daten in zustand.items():
            idx = int(slot_idx) if isinstance(slot_idx, str) else slot_idx
            if idx >= len(self._a4_preview.alle_slots()):
                continue
            pfad = daten.get("foto_pfad")
            if not pfad or not os.path.isfile(pfad):
                continue
            try:
                foto = lade_bild(pfad)
                slot = self._a4_preview.slot_abrufen(idx)
                slot.beschriftung_sichtbar = beschriftung_aktiv
                slot.foto_setzen(foto, pfad)
                slot._slot_data.zoom = daten["zoom"]
                slot._slot_data.offset_x = daten["offset_x"]
                slot._slot_data.offset_y = daten["offset_y"]
                slot._slot_data.rotation = daten.get("rotation", 0)
                slot._slot_data.beschriftung = daten.get("beschriftung", "")
                slot._vorschau_aktualisieren()
            except Exception:
                pass

    def _seite_zurueck(self) -> None:
        """Geht zur vorherigen Seite."""
        if self._aktuelle_seite > 0:
            self._seite_laden(self._aktuelle_seite - 1)

    def _seite_vor(self) -> None:
        """Geht zur naechsten Seite."""
        if self._aktuelle_seite < len(self._seiten_daten) - 1:
            self._seite_laden(self._aktuelle_seite + 1)

    def _seite_hinzufuegen(self) -> None:
        """Fuegt eine neue leere Seite hinzu und wechselt dorthin."""
        self._seite_sichern()
        self._seiten_daten.append({})
        self._seite_laden(len(self._seiten_daten) - 1)

    def _seite_loeschen(self) -> None:
        """Loescht die aktuelle Seite nach Bestaetigung."""
        if len(self._seiten_daten) <= 1:
            messagebox.showinfo(
                "Nicht möglich",
                "Die letzte Seite kann nicht gelöscht werden.",
            )
            return

        antwort = messagebox.askyesno(
            "Seite löschen",
            f"Seite {self._aktuelle_seite + 1} löschen?\n"
            f"Alle Fotozuweisungen dieser Seite gehen verloren.",
        )
        if not antwort:
            return

        # Seite entfernen
        self._seiten_daten.pop(self._aktuelle_seite)

        # Zur vorherigen Seite wechseln (oder bleiben wenn erste)
        if self._aktuelle_seite >= len(self._seiten_daten):
            self._aktuelle_seite = len(self._seiten_daten) - 1

        self._seite_laden_intern(self._aktuelle_seite)
        self._seiten_navigation_aktualisieren()
        self._status_aktualisieren()

    def _seiten_navigation_aktualisieren(self) -> None:
        """Aktualisiert die Seiten-Anzeige."""
        gesamt = len(self._seiten_daten)
        self._seiten_label_var.set(f"Seite {self._aktuelle_seite + 1}/{gesamt}")

    # --- Hilfsfunktionen ---

    def _anleitung_anzeigen(self) -> None:
        """Zeigt die Anleitung in einem scrollbaren Dialog."""
        fenster = tk.Toplevel(self)
        fenster.title("Photowand — Anleitung")
        fenster.geometry("620x520")
        fenster.resizable(True, True)
        fenster.transient(self)
        fenster.grab_set()

        text = tk.Text(
            fenster,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#2b2b2b",
            fg="#e0e0e0",
            padx=14,
            pady=10,
            borderwidth=0,
            highlightthickness=0,
        )
        scrollbar = tk.Scrollbar(fenster, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        # Tags fuer Formatierung
        text.tag_configure("h1", font=("Segoe UI", 16, "bold"), spacing3=6)
        text.tag_configure("h2", font=("Segoe UI", 12, "bold"), spacing1=12, spacing3=4)
        text.tag_configure("bold", font=("Segoe UI", 10, "bold"))

        anleitung = [
            ("h1", "Photowand — Anleitung\n"),
            ("", "Photowand erstellt Druckvorlagen fuer sechseckige "
             "Bilderrahmen. Die Rahmen werden per 3D-Druck hergestellt "
             "und zu einer Fotowand zusammengesteckt.\n\n"),
            ("h2", "Fotos laden\n"),
            ("", "Klicke auf \"Fotos laden\" in der Werkzeugleiste oder "
             "waehle Datei > Fotos laden im Menue. Es oeffnet sich ein "
             "Ordner-Dialog — alle Bilder im gewaehlten Ordner werden als "
             "Thumbnails in der linken Seitenleiste angezeigt.\n"
             "Alternativ: Ziehe Dateien oder Ordner per Drag & Drop direkt "
             "ins Programmfenster.\n\n"),
            ("h2", "Fotos zuweisen\n"),
            ("", "1. Klicke auf ein Thumbnail in der Seitenleiste — freie "
             "Hexagone werden markiert.\n"
             "2. Klicke auf ein markiertes Hexagon, um das Foto zuzuweisen.\n"
             "Oder nutze \"Auto-Fill\" um alle Fotos automatisch der Reihe "
             "nach einzufuellen.\n\n"),
            ("h2", "Foto anpassen\n"),
            ("", "Mausrad: Zoom rein/raus im Hexagon.\n"
             "Linke Maustaste ziehen: Bildausschnitt verschieben.\n"
             "Rechtsklick auf ein belegtes Hexagon oeffnet ein Kontextmenue:\n"
             "  - Foto entfernen\n"
             "  - Foto ersetzen\n"
             "  - Drehen (90 grad rechts / 180 grad / 90 grad links)\n"
             "  - Zoom zuruecksetzen\n"
             "  - Beschriftung bearbeiten\n"
             "  - Tauschen mit einem anderen Slot\n\n"),
            ("h2", "Drag & Drop zwischen Slots\n"),
            ("", "Ziehe ein belegtes Hexagon mit der Maus auf ein anderes "
             "Hexagon, um die Fotos zu tauschen. Der Ziel-Slot wird "
             "hervorgehoben.\n\n"),
            ("h2", "Seiten-Verwaltung\n"),
            ("", "Unten rechts findest du die Seiten-Navigation:\n"
             "  - \"+ Seite\" fuegt eine leere Seite hinzu.\n"
             "  - \"- Seite\" loescht die aktuelle Seite.\n"
             "  - Pfeile zum Blaettern zwischen den Seiten.\n"
             "Auch ueber das Menue \"Seite\" erreichbar.\n\n"),
            ("h2", "Ansicht-Optionen (Menue \"Ansicht\")\n"),
            ("", "Schnittlinien: Zeigt gestrichelte Schnittlinien um die "
             "Hexagone im Druckbild an.\n"
             "Beschriftung: Zeigt Dateinamen unter den Hexagonen an (im "
             "Druckbild und in der Vorschau).\n"
             "Pointy-Top: Wechselt die Hexagon-Orientierung (Ecken oben "
             "statt flache Seite oben).\n"
             "Papierformat: Wechselt zwischen A5, A4, A3, A2, A1 und A0.\n\n"),
            ("h2", "Vorschau\n"),
            ("", "Klicke auf \"Vorschau\" um das finale Druckbild in einem "
             "separaten Fenster anzuzeigen. In der Vorschau kannst du mit "
             "Pfeiltasten zwischen den Seiten blaettern.\n\n"),
            ("h2", "Exportieren & Drucken\n"),
            ("", "\"Export (PNG)\": Speichert die aktuelle Seite als "
             "hochaufloesende PNG-Datei (300 DPI).\n"
             "\"Alle export.\": Exportiert alle Seiten als separate "
             "PNG-Dateien in einen Ordner.\n"
             "\"Drucken\": Oeffnet den Windows-Druckdialog mit der "
             "aktuellen Seite.\n\n"),
            ("h2", "Projekt speichern & laden\n"),
            ("", "Speichere dein Projekt als .photowand Datei, um es "
             "spaeter weiterzubearbeiten. Alle Foto-Zuweisungen, Zoom-"
             "Einstellungen, Rotationen und Beschriftungen werden "
             "gesichert.\n\n"),
            ("h2", "Rueckgaengig / Wiederherstellen\n"),
            ("", "Strg+Z: Letzten Schritt rueckgaengig machen.\n"
             "Strg+Y: Rueckgaengig gemachten Schritt wiederherstellen.\n"
             "Bis zu 30 Undo-Schritte werden gespeichert.\n\n"),
            ("h2", "Tastenkuerzel\n"),
            ("", "Strg+S: Projekt speichern\n"
             "Strg+O: Projekt oeffnen\n"
             "Strg+Z: Rueckgaengig\n"
             "Strg+Y: Wiederherstellen\n"),
        ]

        for tag, zeile in anleitung:
            if tag:
                text.insert("end", zeile, tag)
            else:
                text.insert("end", zeile)

        text.configure(state="disabled")

    def _ueber_anzeigen(self) -> None:
        """Zeigt den Ueber-Dialog."""
        messagebox.showinfo(
            "Über Photowand",
            "Photowand v1.0.3\n"
            "Hexagonale Bildrahmen — Druckvorlagen-Generator\n\n"
            "Erstellt Druckvorlagen fuer sechseckige Bilderrahmen,\n"
            "die per 3D-Druck hergestellt und zu einer Fotowand\n"
            "zusammengesteckt werden.\n\n"
            "Hexagon-Masse (innere Oeffnung):\n"
            "  Umkreisradius: 50.9 mm\n"
            "  Flat-to-Flat: 88.2 mm\n"
            "  Ecke-zu-Ecke: 101.8 mm\n\n"
            "Python · CustomTkinter · Pillow\n"
            "© 2025-2026",
        )

    def _beenden(self) -> None:
        """Beendet die Anwendung sauber."""
        self.quit()
        self.destroy()

    def _sammle_slot_daten(self) -> list[HexSlotData]:
        """Sammelt die Daten aller Slots fuer den Renderer."""
        return [slot.get_slot_data() for slot in self._a4_preview.alle_slots()]

    def _status_aktualisieren(self) -> None:
        """Aktualisiert die Statusleiste."""
        foto_anz = self._photo_strip.foto_anzahl
        belegt = self._a4_preview.belegte_anzahl()
        gesamt = self._layout.slot_anzahl
        fmt = self._layout.format_name
        self._status_var.set(
            f"{foto_anz} Foto(s) geladen | {belegt} von {gesamt} Hexagonen belegt | {fmt}"
        )
