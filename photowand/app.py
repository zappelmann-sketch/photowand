"""Photowand — Hauptfenster der Anwendung."""

import os
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from photowand.core.hexagon import HexagonGeometry
from photowand.core.image_utils import sammle_bilder_aus_ordner, lade_bild, BILD_ENDUNGEN
from photowand.core.layout import LayoutEngine
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

        self.title("Photowand v1.0.1 — Hexagonale Bildrahmen")
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

        # GUI aufbauen
        self._erstelle_gui()

        # Drag & Drop einrichten
        if DND_VERFUEGBAR:
            self._init_drag_drop()

        # Tastenkuerzel
        self.bind("<Control-s>", lambda e: self._projekt_speichern())
        self.bind("<Control-o>", lambda e: self._projekt_laden())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())

    def _erstelle_gui(self) -> None:
        """Baut die gesamte GUI auf."""
        # Hauptcontainer
        self._main_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self._main_frame.pack(fill="both", expand=True)

        # Toolbar
        self._toolbar = ToolbarFrame(
            self._main_frame,
            callbacks={
                "ordner_laden": self._ordner_laden,
                "auto_fill": self._auto_fill,
                "projekt_speichern": self._projekt_speichern,
                "projekt_laden": self._projekt_laden,
                "vorschau": self._vorschau_anzeigen,
                "exportieren": self._exportieren,
                "drucken": self._drucken,
                "zuruecksetzen": self._zuruecksetzen,
                "format_aendern": self._format_aendern,
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
        self._btn_seite_neu.pack(side="left", padx=(6, 0))

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

    # --- Auto-Fill (Feature 2) ---

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

    # --- Projekt speichern/laden (Feature 1) ---

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
                    ))

        daten = ProjektDaten(
            format_name=self._layout.format_name,
            foto_pfade=foto_pfade,
            slots=slot_zuweisungen,
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

        # Format setzen
        self._layout.setze_format(daten.format_name)
        self._toolbar.format_setzen(daten.format_name)
        self._a4_preview.format_aktualisieren()

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
            }

        # Erste Seite laden
        self._aktuelle_seite = 0
        zustand = self._seiten_daten[0] if self._seiten_daten else {}
        for slot_idx, slot_daten in zustand.items():
            idx = int(slot_idx) if isinstance(slot_idx, str) else slot_idx
            if idx >= len(self._a4_preview.alle_slots()):
                continue
            pfad_slot = slot_daten.get("foto_pfad")
            if not pfad_slot or not os.path.isfile(pfad_slot):
                continue
            try:
                foto = lade_bild(pfad_slot)
                slot = self._a4_preview.slot_abrufen(idx)
                slot.foto_setzen(foto, pfad_slot)
                slot._slot_data.zoom = slot_daten["zoom"]
                slot._slot_data.offset_x = slot_daten["offset_x"]
                slot._slot_data.offset_y = slot_daten["offset_y"]
                slot._vorschau_aktualisieren()
            except Exception:
                fehler_slots += 1

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

        schnittlinien = self._toolbar.schnittlinien_aktiv
        try:
            bild = self._render_seite_bild(self._aktuelle_seite, schnittlinien)
            if bild is None:
                # Aktuelle Seite leer — erste nicht-leere Seite suchen
                bild = self._renderer.render(
                    self._sammle_slot_daten(), schnittlinien=schnittlinien
                )

            VorschauDialog(
                self,
                bild,
                f"Druckvorschau — {self._layout.format_name}",
                seiten_anzahl=len(self._seiten_daten),
                aktuelle_seite=self._aktuelle_seite,
                render_seite=lambda seite: self._render_seite_bild(seite, schnittlinien),
            )
        except Exception as e:
            messagebox.showerror("Fehler", f"Vorschau fehlgeschlagen:\n{e}")

    def _render_seite_bild(self, seiten_nr: int, schnittlinien: bool) -> Image.Image | None:
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
                    except Exception:
                        pass
            slot_daten.append(sd)

        return self._renderer.render(slot_daten, schnittlinien=schnittlinien)

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
        schnittlinien = self._toolbar.schnittlinien_aktiv
        try:
            self._renderer.render_und_speichern(slots, pfad, schnittlinien=schnittlinien)
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
        schnittlinien = self._toolbar.schnittlinien_aktiv
        try:
            temp_dir = tempfile.gettempdir()
            temp_pfad = os.path.join(temp_dir, "photowand_druck.png")
            self._renderer.render_und_speichern(slots, temp_pfad, schnittlinien=schnittlinien)

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

        schnittlinien = self._toolbar.schnittlinien_aktiv
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
                        except Exception:
                            pass
                slot_daten.append(sd)

            dateiname = f"Photowand_{fmt}_Seite{seiten_nr + 1}.png"
            ziel = os.path.join(ordner, dateiname)
            try:
                self._renderer.render_und_speichern(
                    slot_daten, ziel, schnittlinien=schnittlinien
                )
                exportiert += 1
            except Exception:
                pass

        messagebox.showinfo(
            "Export abgeschlossen",
            f"{exportiert} Seite(n) exportiert nach:\n{ordner}",
        )

    def _format_aendern(self, format_name: str) -> None:
        """Wechselt das Papierformat und baut die Vorschau neu auf."""
        self._layout.setze_format(format_name)
        self._a4_preview.format_aktualisieren()
        self._ausgewaehltes_foto = None
        self._status_aktualisieren()

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
        self.title("Photowand v1.0.1 — Hexagonale Bildrahmen")
        self._seiten_navigation_aktualisieren()
        self._status_var.set("Bereit — Ordner mit Fotos laden um zu beginnen")

    # --- Undo/Redo (Feature 8) ---

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
                slot._vorschau_aktualisieren()
            except Exception:
                pass

    # --- Seiten-Navigation (Feature 7) ---

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
                }
        # Seitenliste erweitern falls noetig
        while len(self._seiten_daten) <= self._aktuelle_seite:
            self._seiten_daten.append({})
        self._seiten_daten[self._aktuelle_seite] = zustand

    def _seite_laden(self, seiten_nr: int) -> None:
        """Laedt eine bestimmte Seite."""
        if seiten_nr < 0 or seiten_nr >= len(self._seiten_daten):
            return
        self._seite_sichern()
        self._aktuelle_seite = seiten_nr

        # Alle Slots leeren
        for slot in self._a4_preview.alle_slots():
            slot.foto_entfernen()

        # Gespeicherten Zustand wiederherstellen
        zustand = self._seiten_daten[seiten_nr]
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
                slot.foto_setzen(foto, pfad)
                slot._slot_data.zoom = daten["zoom"]
                slot._slot_data.offset_x = daten["offset_x"]
                slot._slot_data.offset_y = daten["offset_y"]
                slot._vorschau_aktualisieren()
            except Exception:
                pass

        self._seiten_navigation_aktualisieren()
        self._status_aktualisieren()

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

    def _seiten_navigation_aktualisieren(self) -> None:
        """Aktualisiert die Seiten-Anzeige."""
        gesamt = len(self._seiten_daten)
        self._seiten_label_var.set(f"Seite {self._aktuelle_seite + 1}/{gesamt}")

    # --- Hilfsfunktionen ---

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
