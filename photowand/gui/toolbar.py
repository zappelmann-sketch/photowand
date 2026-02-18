"""Werkzeugleiste der Photowand-Anwendung."""

import customtkinter as ctk
from typing import Callable


class ToolbarFrame(ctk.CTkFrame):
    """Horizontale Werkzeugleiste mit den Hauptaktionen."""

    def __init__(self, master, callbacks: dict[str, Callable], **kwargs):
        super().__init__(master, height=50, **kwargs)

        self._callbacks = callbacks

        btn_style = {"height": 35, "corner_radius": 6}

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
        self.btn_alle_exportieren = ctk.CTkButton(
            self,
            text="Alle export.",
            command=callbacks.get("alle_exportieren"),
            fg_color="gray40",
            hover_color="gray30",
            width=90,
            **btn_style,
        )
        self.btn_alle_exportieren.grid(row=0, column=col, padx=3, pady=8)

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
