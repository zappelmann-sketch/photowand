# Photowand

**Portable Windows-Anwendung zum Erstellen von Foto-Einsätzen für 3D-gedruckte hexagonale Bilderrahmen.**

Photowand wurde entwickelt, um Fotos passgenau in sechseckige (Flat-Top) Bilderrahmen einzusetzen, die per 3D-Drucker hergestellt werden. Die Fotos werden hexagonal zugeschnitten, auf einem Druckblatt (A5 bis A0) angeordnet und können direkt ausgedruckt oder als 300-DPI-PNG exportiert werden — zum Ausschneiden und Einsetzen in die physischen Rahmen.

![Photowand GUI](pictures/GUI.png)

---

## Für welchen Rahmen?

Photowand ist auf den mitgelieferten **Hex Picture Frame** (`Hex_Picture_Frame.stl`) ausgelegt:

| Eigenschaft | Wert |
|---|---|
| Orientierung | Flat-Top (flache Seiten oben/unten) |
| Umkreisradius | ~50 mm (Mitte → Ecke) |
| Apothem | ~43,2 mm (Mitte → Seitenmitte) |
| Flat-to-Flat | ~86,4 mm |
| Ecke-zu-Ecke | ~100 mm |

### 3D-Modell

<p align="center">
  <img src="pictures/stl.png" alt="Hex Picture Frame STL" width="400">
</p>

<p align="center">
  <a href="Hex_Picture_Frame.stl">
    <code>Hex_Picture_Frame.stl</code> herunterladen
  </a>
</p>

> Die STL-Datei kann direkt im GitHub-Repository per 3D-Viewer betrachtet werden: Einfach auf [`Hex_Picture_Frame.stl`](Hex_Picture_Frame.stl) klicken.

---

## Features

- **Foto-Import** — Ordner laden oder Drag & Drop aus dem Explorer
- **Interaktive Hexagon-Slots** — Fotos per Klick zuweisen
- **Zoom & Pan** — Mausrad = Foto-Zoom, Ziehen = Foto-Verschieben, Doppelklick = Reset
- **Vorschau-Zoom** — Ctrl+Mausrad zum Vergrößern der gesamten Vorlage
- **Auto-Fill** — Fotos automatisch der Reihe nach zuweisen (seitenübergreifend ohne Duplikate)
- **Mehrseitig** — Beliebig viele Seiten für große Foto-Sammlungen
- **Papierformate** — A5, A4, A3, A2, A1, A0 (automatische Slot-Berechnung)
- **Schnittlinien** — Ein-/ausschaltbare Schnittmarkierungen zum Ausschneiden
- **Druck-Vorschau** — Vorschau mit Seitennavigation vor dem Drucken
- **Export (300 DPI)** — PNG-Export in Druckqualität
- **Drucken** — Direkter Windows-Druckdialog
- **Projekt speichern/laden** — `.photowand`-Dateien zum Weitermachen
- **Undo/Redo** — Ctrl+Z / Ctrl+Y (bis zu 30 Schritte)
- **Rechtsklick-Menü** — Foto entfernen, Zoom zurücksetzen, Slots tauschen

---

## Anleitung

### 1. Fotos laden
Klicke auf **Fotos laden** und wähle einen Ordner mit Bildern. Alternativ: Dateien oder Ordner per Drag & Drop in das Fenster ziehen.

### 2. Fotos zuweisen
**Manuell:** Klicke auf ein Foto in der Seitenleiste, dann auf einen Hexagon-Slot.
**Automatisch:** Klicke auf **Auto-Fill** — die Fotos werden der Reihe nach in leere Slots eingefügt.

### 3. Fotos anpassen
- **Mausrad** auf einem Slot → Foto hinein-/herauszoomen
- **Linke Maustaste + Ziehen** → Foto innerhalb des Hexagons verschieben
- **Doppelklick** → Zoom und Position zurücksetzen
- **Rechtsklick** → Kontextmenü (Entfernen, Reset, Tauschen)

### 4. Vorschau zoomen (für große Formate)
- **Ctrl + Mausrad** → Gesamte Vorlage vergrößern/verkleinern
- **Mittlere Maustaste + Ziehen** → Ansicht verschieben
- **Scrollbars** → Navigation bei großen Formaten

### 5. Mehrere Seiten
Klicke auf **+ Seite** in der Statusleiste für eine neue Seite. Mit **◀ ▶** zwischen Seiten wechseln. Auto-Fill überspringt automatisch bereits verwendete Fotos.

### 6. Exportieren / Drucken
- **Vorschau** → Druckvorschau mit Seitenblätterung
- **Export (PNG)** → 300-DPI-PNG speichern
- **Drucken** → Öffnet den Windows-Druckdialog

### 7. Projekt speichern
- **Speichern** (Ctrl+S) → `.photowand`-Projektdatei erstellen
- **Öffnen** (Ctrl+O) → Gespeichertes Projekt wiederherstellen

---

## Tastenkürzel

| Taste | Aktion |
|---|---|
| Ctrl+S | Projekt speichern |
| Ctrl+O | Projekt öffnen |
| Ctrl+Z | Rückgängig |
| Ctrl+Y | Wiederherstellen |
| Ctrl+Mausrad | Vorschau-Zoom |
| Mausrad (auf Slot) | Foto-Zoom |
| Doppelklick (auf Slot) | Zoom/Position zurücksetzen |

---

## Technologie-Stack

| Komponente | Technologie | Version |
|---|---|---|
| Sprache | Python | 3.13+ |
| GUI-Framework | CustomTkinter | >= 5.2.0 |
| Bildverarbeitung | Pillow (PIL) | >= 10.0.0 |
| Drag & Drop | tkinterdnd2 | >= 0.4.2 |
| Verpackung | PyInstaller | 6.19.0 |
| Plattform | Windows | 10/11 |

---

## Installation & Build

### Voraussetzungen
- Python 3.13+
- Windows 10/11

### Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### Aus Quellcode starten
```bash
python -m photowand
```

### Standalone .exe bauen
```bash
pip install pyinstaller
python -m PyInstaller --noconfirm build/photowand.spec
```

Die fertige `Photowand.exe` liegt danach im `dist/`-Ordner.

---

## Projektstruktur

```
photowand/
  main.py                  # Einstiegspunkt
  app.py                   # Hauptfenster & Orchestrierung
  models.py                # HexSlotData Datenklasse
  core/
    hexagon.py             # Hexagon-Geometrie (Vertices, mm/px)
    layout.py              # Layout-Engine (A5–A0, Slot-Positionen)
    renderer.py            # 300-DPI-Druckbild-Renderer
    image_utils.py         # Bildladen, EXIF-Korrektur
    project.py             # Projekt speichern/laden (.photowand)
  gui/
    hex_canvas.py          # Interaktives Hexagon-Widget (Zoom/Pan)
    a4_preview.py          # Seitenvorschau mit Scroll & Zoom
    toolbar.py             # Werkzeugleiste
    photo_strip.py         # Foto-Seitenleiste (Thumbnails)
    vorschau_dialog.py     # Druck-Vorschau-Dialog
```

---

## Lizenz

Dieses Projekt ist frei zur persönlichen Nutzung.
