"""Werkzeugleiste der Photowand-Anwendung."""

import customtkinter as ctk
from typing import Callable

from photowand.core.layout import PAPIER_FORMATE


class ToolbarFrame(ctk.CTkFrame):
    """Horizontale Werkzeugleiste mit den Hauptaktionen."""

    def __init__(self, master, callbacks: dict[str, Callable], **kwargs):
        super().__init__(master, height=50, **kwargs)

        self._callbacks = callbacks

        # Spacer-Spalte
        self.grid_columnconfigure(20, weight=1)

        btn_style = {"height": 35, "corner_radius": 6}

        # --- Linke Seite: Aktionsbuttons ---

        col = 0
        self.btn_laden = ctk.CTkButton(
            self,
            text="Fotos laden",
            command=callbacks.get("ordner_laden"),
            **btn_style,
        )
        self.btn_laden.grid(row=0, column=col, padx=(10, 3), pady=8)

        col += 1
        self.btn_auto_fill = ctk.CTkButton(
            self,
            text="Auto-Fill",
            command=callbacks.get("auto_fill"),
            fg_color="#2D7D46",
            hover_color="#236B38",
            **btn_style,
        )
        self.btn_auto_fill.grid(row=0, column=col, padx=3, pady=8)

        # Separator
        col += 1
        sep1 = ctk.CTkFrame(self, width=2, height=30, fg_color="gray50")
        sep1.grid(row=0, column=col, padx=6, pady=8)

        col += 1
        self.btn_speichern = ctk.CTkButton(
            self,
            text="Speichern",
            command=callbacks.get("projekt_speichern"),
            fg_color="gray40",
            hover_color="gray30",
            width=90,
            **btn_style,
        )
        self.btn_speichern.grid(row=0, column=col, padx=3, pady=8)

        col += 1
        self.btn_oeffnen = ctk.CTkButton(
            self,
            text="Öffnen",
            command=callbacks.get("projekt_laden"),
            fg_color="gray40",
            hover_color="gray30",
            width=75,
            **btn_style,
        )
        self.btn_oeffnen.grid(row=0, column=col, padx=3, pady=8)

        # Separator
        col += 1
        sep2 = ctk.CTkFrame(self, width=2, height=30, fg_color="gray50")
        sep2.grid(row=0, column=col, padx=6, pady=8)

        col += 1
        self.btn_vorschau = ctk.CTkButton(
            self,
            text="Vorschau",
            command=callbacks.get("vorschau"),
            fg_color="#5B4A8A",
            hover_color="#4A3A73",
            width=80,
            **btn_style,
        )
        self.btn_vorschau.grid(row=0, column=col, padx=3, pady=8)

        col += 1
        self.btn_exportieren = ctk.CTkButton(
            self,
            text="Export (PNG)",
            command=callbacks.get("exportieren"),
            **btn_style,
        )
        self.btn_exportieren.grid(row=0, column=col, padx=3, pady=8)

        col += 1
        self.btn_drucken = ctk.CTkButton(
            self,
            text="Drucken",
            command=callbacks.get("drucken"),
            **btn_style,
        )
        self.btn_drucken.grid(row=0, column=col, padx=3, pady=8)

        # Separator
        col += 1
        sep3 = ctk.CTkFrame(self, width=2, height=30, fg_color="gray50")
        sep3.grid(row=0, column=col, padx=6, pady=8)

        col += 1
        self.btn_zuruecksetzen = ctk.CTkButton(
            self,
            text="Reset",
            command=callbacks.get("zuruecksetzen"),
            fg_color="#8B3A3A",
            hover_color="#6B2A2A",
            width=65,
            **btn_style,
        )
        self.btn_zuruecksetzen.grid(row=0, column=col, padx=3, pady=8)

        # --- Rechte Seite (nach Spacer) ---

        # Schnittlinien-Toggle
        self._schnittlinien_var = ctk.BooleanVar(value=True)
        self.schnittlinien_switch = ctk.CTkSwitch(
            self,
            text="Schnittlinien",
            variable=self._schnittlinien_var,
            font=("Segoe UI", 12),
            width=40,
        )
        self.schnittlinien_switch.grid(row=0, column=21, padx=(10, 5), pady=8)

        # Papierformat-Auswahl
        format_label = ctk.CTkLabel(
            self,
            text="Format:",
            font=("Segoe UI", 13),
        )
        format_label.grid(row=0, column=22, padx=(10, 2), pady=8)

        format_namen = list(PAPIER_FORMATE.keys())
        self._format_var = ctk.StringVar(value="A4")
        self.format_dropdown = ctk.CTkComboBox(
            self,
            values=format_namen,
            variable=self._format_var,
            width=80,
            height=35,
            state="readonly",
            command=lambda val: callbacks.get("format_aendern", lambda v: None)(val),
        )
        self.format_dropdown.grid(row=0, column=23, padx=(2, 10), pady=8)

    @property
    def schnittlinien_aktiv(self) -> bool:
        """Gibt zurueck ob Schnittlinien aktiviert sind."""
        return self._schnittlinien_var.get()

    def format_setzen(self, format_name: str) -> None:
        """Setzt das Format im Dropdown (ohne Callback auszuloesen)."""
        self._format_var.set(format_name)
