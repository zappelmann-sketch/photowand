"""Foto-Seitenleiste: Zeigt importierte Fotos als Thumbnails."""

import customtkinter as ctk
from PIL import Image
from typing import Callable

from photowand.core.image_utils import lade_bild, erstelle_vorschau


THUMBNAIL_GROESSE = 130


class PhotoStripFrame(ctk.CTkScrollableFrame):
    """Scrollbare Seitenleiste mit Foto-Thumbnails.

    Speichert nur Dateipfade und Thumbnails — Originalbilder werden
    erst bei Bedarf (Slot-Zuweisung) von Disk geladen.
    """

    def __init__(
        self,
        master,
        on_foto_ausgewaehlt: Callable[[int], None],
        **kwargs,
    ):
        super().__init__(master, width=170, **kwargs)

        self._on_foto_ausgewaehlt = on_foto_ausgewaehlt
        self._pfade: list[str] = []
        self._thumbnail_widgets: list[ctk.CTkButton] = []
        self._ctk_bilder: list[ctk.CTkImage] = []
        self._ausgewaehlt: int | None = None

        self._label_leer = ctk.CTkLabel(
            self,
            text="Keine Fotos\ngeladen",
            text_color="gray50",
        )
        self._label_leer.pack(pady=40)

    @property
    def foto_anzahl(self) -> int:
        return len(self._pfade)

    def foto_laden(self, index: int) -> Image.Image:
        """Laedt das Originalbild vom Dateipfad (on-demand)."""
        return lade_bild(self._pfade[index])

    def pfad_abrufen(self, index: int) -> str:
        """Gibt den Dateipfad am Index zurueck."""
        return self._pfade[index]

    def fotos_hinzufuegen(
        self,
        pfade: list[str],
        status_callback: Callable[[int, int], None] | None = None,
    ) -> list[tuple[str, str]]:
        """Fuegt Fotos hinzu. Gibt Liste von (pfad, fehler) Tupeln zurueck.

        Erstellt nur Thumbnails — Originalbilder werden nicht im Speicher gehalten.
        """
        if self._label_leer.winfo_ismapped():
            self._label_leer.pack_forget()

        fehler = []
        for i, pfad in enumerate(pfade):
            try:
                # Nur Thumbnail laden (kleines Bild)
                bild = lade_bild(pfad)
                vorschau = erstelle_vorschau(bild, (THUMBNAIL_GROESSE, THUMBNAIL_GROESSE))
                del bild  # Originalbild sofort freigeben

                index = len(self._pfade)
                self._pfade.append(pfad)

                ctk_bild = ctk.CTkImage(
                    light_image=vorschau,
                    dark_image=vorschau,
                    size=(vorschau.width, vorschau.height),
                )
                self._ctk_bilder.append(ctk_bild)

                btn = ctk.CTkButton(
                    self,
                    image=ctk_bild,
                    text="",
                    width=THUMBNAIL_GROESSE + 10,
                    height=THUMBNAIL_GROESSE + 10,
                    corner_radius=8,
                    fg_color="transparent",
                    hover_color=("gray75", "gray25"),
                    border_width=0,
                    command=lambda idx=index: self._on_klick(idx),
                )
                btn.pack(pady=4, padx=5)
                self._thumbnail_widgets.append(btn)

            except Exception as e:
                fehler.append((pfad, str(e)))

            # Fortschritt melden und GUI aktualisieren
            if status_callback:
                status_callback(i + 1, len(pfade))
            if (i + 1) % 3 == 0:
                self.winfo_toplevel().update_idletasks()

        return fehler

    def auswahl_aufheben(self) -> None:
        """Hebt die aktuelle Auswahl auf."""
        if self._ausgewaehlt is not None and self._ausgewaehlt < len(self._thumbnail_widgets):
            self._thumbnail_widgets[self._ausgewaehlt].configure(
                border_width=0
            )
        self._ausgewaehlt = None

    def alle_entfernen(self) -> None:
        """Entfernt alle Fotos."""
        for widget in self._thumbnail_widgets:
            widget.destroy()
        self._pfade.clear()
        self._thumbnail_widgets.clear()
        self._ctk_bilder.clear()
        self._ausgewaehlt = None

        self._label_leer.pack(pady=40)

    def _on_klick(self, index: int) -> None:
        """Handler fuer Thumbnail-Klick."""
        self.auswahl_aufheben()

        self._ausgewaehlt = index
        self._thumbnail_widgets[index].configure(
            border_width=2,
            border_color=("#3B8ED0", "#1F6AA5"),
        )

        self._on_foto_ausgewaehlt(index)
