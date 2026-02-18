"""Projekt speichern und laden (.photowand JSON-Datei)."""

import json
from dataclasses import dataclass, field


@dataclass
class SlotZuweisung:
    """Zuweisung eines Fotos zu einem Slot."""

    slot_index: int
    foto_pfad: str
    zoom: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    seite: int = 0


@dataclass
class ProjektDaten:
    """Daten eines gespeicherten Projekts."""

    version: int = 1
    format_name: str = "A4"
    foto_pfade: list[str] = field(default_factory=list)
    slots: list[SlotZuweisung] = field(default_factory=list)


def projekt_speichern(pfad: str, daten: ProjektDaten) -> None:
    """Speichert ein Projekt als .photowand JSON-Datei."""
    obj = {
        "version": daten.version,
        "format_name": daten.format_name,
        "foto_pfade": daten.foto_pfade,
        "slots": [
            {
                "slot_index": s.slot_index,
                "foto_pfad": s.foto_pfad,
                "zoom": s.zoom,
                "offset_x": s.offset_x,
                "offset_y": s.offset_y,
                "seite": s.seite,
            }
            for s in daten.slots
        ],
    }
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def projekt_laden(pfad: str) -> ProjektDaten:
    """Laedt ein Projekt aus einer .photowand JSON-Datei."""
    with open(pfad, "r", encoding="utf-8") as f:
        obj = json.load(f)

    slots = [
        SlotZuweisung(
            slot_index=s["slot_index"],
            foto_pfad=s["foto_pfad"],
            zoom=s.get("zoom", 1.0),
            offset_x=s.get("offset_x", 0.0),
            offset_y=s.get("offset_y", 0.0),
            seite=s.get("seite", 0),
        )
        for s in obj.get("slots", [])
    ]

    return ProjektDaten(
        version=obj.get("version", 1),
        format_name=obj.get("format_name", "A4"),
        foto_pfade=obj.get("foto_pfade", []),
        slots=slots,
    )
