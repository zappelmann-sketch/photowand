"""Druck-Vorschau-Dialog: Zeigt das gerenderte Druckbild vor dem Export."""

import tkinter as tk
import customtkinter as ctk
from typing import Callable
from PIL import Image, ImageTk


class VorschauDialog(ctk.CTkToplevel):
    """Modaler Dialog mit Vorschau des gerenderten Druckbildes.

    Unterstuetzt Blaettern zwischen mehreren Seiten ueber
    Links/Rechts-Pfeile oder Tastatur.
    """

    def __init__(
        self,
        master,
        bild: Image.Image,
        titel: str = "Druckvorschau",
        seiten_anzahl: int = 1,
        aktuelle_seite: int = 0,
        render_seite: Callable[[int], Image.Image | None] = None,
    ):
        super().__init__(master)
        self.title(titel)
        self.transient(master)

        self._seiten_anzahl = seiten_anzahl
        self._aktuelle_seite = aktuelle_seite
        self._render_seite = render_seite
        self._titel_basis = titel

        # Bildschirmgroesse ermitteln
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self._max_w = int(screen_w * 0.8)
        self._max_h = int(screen_h * 0.8) - 100  # Platz fuer Buttons + Nav

        # Bild auf Vorschaugroesse skalieren
        self._original = bild
        scale = min(self._max_w / bild.width, self._max_h / bild.height, 1.0)
        preview_w = int(bild.width * scale)
        preview_h = int(bild.height * scale)
        self._vorschau = bild.resize((preview_w, preview_h), Image.LANCZOS)

        # Fenstergroesse setzen
        win_w = max(preview_w + 40, 400)
        win_h = preview_h + 130
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.resizable(False, False)

        # Bild anzeigen
        self._tk_bild = ImageTk.PhotoImage(self._vorschau)
        self._canvas = tk.Canvas(
            self,
            width=preview_w,
            height=preview_h,
            bg="gray20",
            highlightthickness=0,
        )
        self._canvas.pack(padx=10, pady=(10, 5))
        self._bild_id = self._canvas.create_image(0, 0, anchor="nw", image=self._tk_bild)

        # Info-Label
        self._info_var = tk.StringVar()
        self._info_aktualisieren(bild)
        self._info_label = ctk.CTkLabel(
            self,
            textvariable=self._info_var,
            text_color="gray60",
            font=("Segoe UI", 11),
        )
        self._info_label.pack(pady=(0, 5))

        # Seiten-Navigation (nur bei mehreren Seiten)
        if seiten_anzahl > 1 and render_seite is not None:
            nav_frame = ctk.CTkFrame(self, fg_color="transparent")
            nav_frame.pack(pady=(0, 5))

            self._btn_zurueck = ctk.CTkButton(
                nav_frame,
                text="◀",
                width=35,
                height=30,
                corner_radius=4,
                command=self._seite_zurueck,
                fg_color="gray40",
                hover_color="gray30",
            )
            self._btn_zurueck.pack(side="left", padx=5)

            self._seiten_var = tk.StringVar()
            self._seiten_label = ctk.CTkLabel(
                nav_frame,
                textvariable=self._seiten_var,
                font=("Segoe UI", 13, "bold"),
                text_color="gray70",
            )
            self._seiten_label.pack(side="left", padx=10)

            self._btn_vor = ctk.CTkButton(
                nav_frame,
                text="▶",
                width=35,
                height=30,
                corner_radius=4,
                command=self._seite_vor,
                fg_color="gray40",
                hover_color="gray30",
            )
            self._btn_vor.pack(side="left", padx=5)

            self._seiten_anzeige_aktualisieren()

            # Tastatur-Navigation
            self.bind("<Left>", lambda e: self._seite_zurueck())
            self.bind("<Right>", lambda e: self._seite_vor())

        # Button-Leiste
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="Schließen",
            command=self.destroy,
            fg_color="gray40",
            hover_color="gray30",
            width=100,
        ).pack(side="left", padx=5)

        # Fokus setzen
        self.focus_set()
        self.grab_set()

    def _info_aktualisieren(self, bild: Image.Image) -> None:
        """Aktualisiert das Info-Label mit Bildgroesse."""
        self._info_var.set(
            f"{bild.width} x {bild.height} px | "
            f"{bild.width / 300:.0f} x {bild.height / 300:.0f} Zoll bei 300 DPI"
        )

    def _seiten_anzeige_aktualisieren(self) -> None:
        """Aktualisiert die Seitenanzeige und Button-States."""
        self._seiten_var.set(
            f"Seite {self._aktuelle_seite + 1} / {self._seiten_anzahl}"
        )
        # Buttons aktivieren/deaktivieren
        if hasattr(self, "_btn_zurueck"):
            self._btn_zurueck.configure(
                state="normal" if self._aktuelle_seite > 0 else "disabled"
            )
        if hasattr(self, "_btn_vor"):
            self._btn_vor.configure(
                state="normal" if self._aktuelle_seite < self._seiten_anzahl - 1 else "disabled"
            )

    def _seite_zurueck(self) -> None:
        """Blaettert zur vorherigen Seite."""
        if self._aktuelle_seite > 0:
            self._seite_wechseln(self._aktuelle_seite - 1)

    def _seite_vor(self) -> None:
        """Blaettert zur naechsten Seite."""
        if self._aktuelle_seite < self._seiten_anzahl - 1:
            self._seite_wechseln(self._aktuelle_seite + 1)

    def _seite_wechseln(self, neue_seite: int) -> None:
        """Rendert und zeigt eine andere Seite an."""
        if self._render_seite is None:
            return

        bild = self._render_seite(neue_seite)
        if bild is None:
            return

        self._aktuelle_seite = neue_seite
        self._original = bild

        # Bild skalieren
        scale = min(self._max_w / bild.width, self._max_h / bild.height, 1.0)
        preview_w = int(bild.width * scale)
        preview_h = int(bild.height * scale)
        self._vorschau = bild.resize((preview_w, preview_h), Image.LANCZOS)

        # Canvas aktualisieren
        self._tk_bild = ImageTk.PhotoImage(self._vorschau)
        self._canvas.itemconfig(self._bild_id, image=self._tk_bild)

        self._info_aktualisieren(bild)
        self._seiten_anzeige_aktualisieren()
