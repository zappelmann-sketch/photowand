"""Hilfsfunktionen fuer Bildverarbeitung."""

import os
from PIL import Image, ExifTags

# Pillow-Plugins explizit importieren (noetig fuer PyInstaller-Bundle)
import PIL.JpegImagePlugin  # noqa: F401
import PIL.PngImagePlugin   # noqa: F401
import PIL.GifImagePlugin   # noqa: F401
import PIL.BmpImagePlugin   # noqa: F401
import PIL.TiffImagePlugin  # noqa: F401
import PIL.WebPImagePlugin  # noqa: F401

# Unterstuetzte Bildformate
BILD_ENDUNGEN = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif",
    ".tiff", ".tif", ".webp", ".ico", ".ppm",
}


def lade_bild(pfad: str) -> Image.Image:
    """Laedt ein Bild und korrigiert die EXIF-Orientierung."""
    bild = Image.open(pfad)
    bild.load()  # Pixeldaten sofort laden (Pillow ist sonst lazy)
    bild = exif_orientierung_korrigieren(bild)
    # In RGB konvertieren (fuer Anzeige und Druck)
    if bild.mode not in ("RGB", "RGBA"):
        bild = bild.convert("RGB")
    # Saubere Kopie ohne Metadaten erstellen (verhindert CTkImage-Fehler)
    sauber = Image.new(bild.mode, bild.size)
    sauber.paste(bild)
    return sauber


def sammle_bilder_aus_ordner(ordner_pfad: str) -> list[str]:
    """Gibt alle Bilddateien in einem Ordner zurueck (nicht rekursiv)."""
    pfade = []
    try:
        for dateiname in sorted(os.listdir(ordner_pfad)):
            endung = os.path.splitext(dateiname)[1].lower()
            if endung in BILD_ENDUNGEN:
                pfade.append(os.path.join(ordner_pfad, dateiname))
    except OSError:
        pass
    return pfade


def exif_orientierung_korrigieren(bild: Image.Image) -> Image.Image:
    """Dreht das Bild gemaess EXIF-Orientierungstag."""
    try:
        exif = bild.getexif()
        # EXIF-Tag 274 = Orientation
        orientierung = exif.get(274)
        if orientierung is None:
            return bild

        if orientierung == 2:
            bild = bild.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientierung == 3:
            bild = bild.transpose(Image.ROTATE_180)
        elif orientierung == 4:
            bild = bild.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientierung == 5:
            bild = bild.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientierung == 6:
            bild = bild.transpose(Image.ROTATE_270)
        elif orientierung == 7:
            bild = bild.transpose(Image.ROTATE_90).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientierung == 8:
            bild = bild.transpose(Image.ROTATE_90)
    except (AttributeError, KeyError):
        pass
    return bild


def erstelle_vorschau(bild: Image.Image, max_groesse: tuple[int, int]) -> Image.Image:
    """Erstellt ein verkleinertes Vorschaubild fuer die GUI.

    Verwendet erst draft() fuer schnelles Downsampling bei grossen Bildern,
    dann thumbnail() fuer die finale Groesse.
    """
    vorschau = bild.copy()
    vorschau.info.clear()
    # Bei sehr grossen Bildern erst grob verkleinern (schneller)
    if vorschau.width > max_groesse[0] * 4 or vorschau.height > max_groesse[1] * 4:
        vorschau = vorschau.resize(
            (max(1, vorschau.width // 4), max(1, vorschau.height // 4)),
            Image.BILINEAR,
        )
        vorschau.info.clear()
    vorschau.thumbnail(max_groesse, Image.LANCZOS)
    vorschau.info.clear()
    return vorschau
