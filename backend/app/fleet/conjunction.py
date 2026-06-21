"""Welle 5 — Physikalisch wandernde Galaxie (Variante A: Konjunktions-Fenster).

REINE, DETERMINISTISCHE Distanz-Modulation. Der Kosmos „atmet": die effektive Distanz zwischen
zwei Systemen schwankt zeitabhaengig um die statische OGame-Distanz. Selten geraten zwei Systeme
in **Konjunktion** (ihre deterministischen Phasen treffen sich) -> die Distanz sinkt kurzzeitig bis
``max_discount`` (schnelle/billige Routen). Dazwischen ein sanftes Auf und Ab um 1.0 (bis
``max_surcharge``).

WICHTIG (Design): Die Modulation wird NUR ZUM BERECHNUNGSZEITPUNKT (= Flotten-Start) angewandt.
``arrive_at``/``return_at`` werden danach fix gespeichert -> interception/phalanx/spionage/stations
(die ohnehin beim Start snapshoten) brechen NICHT.

Diese Datei ist DB-frei und ohne Seiteneffekte: die Kernfunktionen nehmen die Zeit als Parameter
(epoch seconds) entgegen — KEIN ``new Date()``/``now()``, KEIN ``random`` in der reinen Logik.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math

Coord = tuple[int, int, int]

# Fallback-Defaults, falls balance.json den Block (noch) nicht enthaelt. Single Source of Truth
# bleibt shared/balance.json -> ``load_cfg`` ueberschreibt diese Werte.
_DEFAULTS: dict = {
    "enabled": True,
    "cycle_hours": 6.0,            # Laenge eines vollen Schwingungs-Zyklus pro System-Paar
    "conjunction_window_hours": 0.5,  # Gesamtdauer eines Konjunktions-Fensters (um das Zentrum zentriert)
    "max_discount": 0.7,          # Faktor-Tiefpunkt im Konjunktions-Zentrum (0.7 = -30% Distanz)
    "max_surcharge": 1.15,        # Faktor-Hochpunkt am Anti-Konjunktions-Punkt (+15% Distanz)
    "radius": 12,                 # Endpoint: Nachbar-Systeme +/- radius um eigene Systeme
    "max_upcoming": 12,           # Endpoint: max. Anzahl kommender Fenster
    "inter_galaxy_enabled": False,  # Konjunktionen auch zwischen verschiedenen Galaxien?
}


def load_cfg() -> dict:
    """Liest den ``conjunction``-Block aus balance.json (mit Defaults gemerged)."""
    from app.platform.balance import get_balance

    cfg = dict(_DEFAULTS)
    cfg.update(get_balance().data.get("conjunction", {}) or {})
    return cfg


def _now_epoch() -> float:
    return dt.datetime.now(dt.timezone.utc).timestamp()


def _applies(origin: Coord, target: Coord, cfg: dict) -> bool:
    """Konjunktionen sind NUR zwischen verschiedenen Systemen sinnvoll.

    - Gleiche Koords (z. B. Mond<->Planet) oder gleiches System (nur Position differiert) -> nein.
    - Anderes System (gleiche Galaxie) -> ja.
    - Andere Galaxie -> nur wenn ``inter_galaxy_enabled``.
    """
    if tuple(origin) == tuple(target):
        return False
    if origin[0] != target[0]:
        return bool(cfg.get("inter_galaxy_enabled", False))
    if origin[1] != target[1]:
        return True
    return False  # gleiche Galaxie + gleiches System


def _pair_offset(origin: Coord, target: Coord) -> float:
    """Deterministischer Phasen-Offset eines System-PAARS in [0, 1).

    Symmetrisch (origin<->target gleich) und nur von (Galaxie, System) abhaengig (Position spielt
    keine Rolle, Konjunktion ist eine System-Eigenschaft). ``hashlib`` statt ``hash()``, damit der
    Wert prozess-/lauf-stabil ist (Pythons ``hash`` ist gesalzen)."""
    a = (int(origin[0]), int(origin[1]))
    b = (int(target[0]), int(target[1]))
    lo, hi = sorted((a, b))
    key = f"{lo[0]}:{lo[1]}|{hi[0]}:{hi[1]}".encode()
    digest = hashlib.sha256(key).hexdigest()
    return (int(digest[:12], 16) % 1_000_000) / 1_000_000.0


def _period_seconds(cfg: dict) -> float:
    return max(60.0, float(cfg.get("cycle_hours", 6.0)) * 3600.0)


def _half_window_seconds(cfg: dict) -> float:
    """Halbe Konjunktions-Fensterbreite in Sekunden (Fenster ist um das Zentrum zentriert)."""
    return max(1.0, float(cfg.get("conjunction_window_hours", 0.5)) * 3600.0 / 2.0)


def _nearest_center(at_epoch: float, period: float, offset: float) -> float:
    """Naechstgelegenes Konjunktions-Zentrum (Phase = 0) in Sekunden."""
    k = round(at_epoch / period + offset)
    return (k - offset) * period


def distance_factor(origin: Coord, target: Coord, at_epoch: float, cfg: dict) -> float:
    """Deterministischer Distanz-Faktor in [max_discount, max_surcharge].

    Formel:
      phase   = frac(at_epoch / period + offset)         # 0 = Konjunktions-Zentrum
      base    = 1 + (max_surcharge-1) * (0.5 - 0.5*cos(2π*phase))   # sanftes Atmen, Peak bei phase=0.5
      strength= max(0, 1 - |at_epoch - center| / half_window)       # Dreieck im Fenster, 0 ausserhalb
      factor  = base - strength * (base - max_discount)             # zieht im Fenster bis max_discount
    Im Zentrum (phase=0, strength=1) ist base=1.0 -> factor=max_discount exakt. Ausserhalb des
    Fensters (strength=0) -> factor=base (stetig). Immer geklemmt auf [max_discount, max_surcharge]."""
    if not cfg.get("enabled", True) or not _applies(origin, target, cfg):
        return 1.0
    period = _period_seconds(cfg)
    half_window = _half_window_seconds(cfg)
    offset = _pair_offset(origin, target)
    max_disc = float(cfg.get("max_discount", 0.7))
    max_sur = float(cfg.get("max_surcharge", 1.15))

    phase = (at_epoch / period + offset) % 1.0
    base = 1.0 + (max_sur - 1.0) * (0.5 - 0.5 * math.cos(2.0 * math.pi * phase))

    center = _nearest_center(at_epoch, period, offset)
    dist_s = abs(at_epoch - center)
    strength = max(0.0, 1.0 - dist_s / half_window) if half_window > 0 else 0.0

    factor = base - strength * (base - max_disc)
    return max(max_disc, min(max_sur, factor))


def is_conjunction(origin: Coord, target: Coord, at_epoch: float, cfg: dict) -> bool:
    """Ob das Paar zum Zeitpunkt ``at_epoch`` in einem aktiven Konjunktions-Fenster ist."""
    if not cfg.get("enabled", True) or not _applies(origin, target, cfg):
        return False
    period = _period_seconds(cfg)
    half_window = _half_window_seconds(cfg)
    offset = _pair_offset(origin, target)
    center = _nearest_center(at_epoch, period, offset)
    return abs(at_epoch - center) <= half_window


def next_conjunction(origin: Coord, target: Coord, from_epoch: float, cfg: dict) -> float | None:
    """Naechstes Konjunktions-ZENTRUM (epoch seconds) STRIKT nach ``from_epoch`` (fuer Countdown).

    ``None``, wenn auf dieses Paar keine Konjunktion zutrifft / Feature aus. Monoton: groesseres
    ``from_epoch`` ergibt nie ein frueheres Ergebnis."""
    if not cfg.get("enabled", True) or not _applies(origin, target, cfg):
        return None
    period = _period_seconds(cfg)
    offset = _pair_offset(origin, target)
    k = math.floor(from_epoch / period + offset) + 1
    return (k - offset) * period


def active_window_end(origin: Coord, target: Coord, at_epoch: float, cfg: dict) -> float | None:
    """Ende (epoch seconds) des AKTUELL aktiven Fensters, sonst ``None`` (gerade keine Konjunktion)."""
    if not is_conjunction(origin, target, at_epoch, cfg):
        return None
    period = _period_seconds(cfg)
    half_window = _half_window_seconds(cfg)
    offset = _pair_offset(origin, target)
    center = _nearest_center(at_epoch, period, offset)
    return center + half_window


def effective_distance(
    origin: Coord, target: Coord, at_epoch: float | None = None, cfg: dict | None = None
) -> int:
    """Effektive Distanz = round(compute_distance * distance_factor) zum Zeitpunkt ``at_epoch``.

    Bei ``enabled=false`` ist der Faktor 1.0 -> Ergebnis identisch zur statischen ``compute_distance``
    (Verhalten exakt wie bisher). Nur HIER (Berechnungszeitpunkt) wird moduliert; das Ergebnis wird
    danach fix in ``arrive_at``/``return_at`` verbacken."""
    from app.fleet.service import compute_distance

    base = compute_distance(tuple(origin), tuple(target))
    if cfg is None:
        cfg = load_cfg()
    if at_epoch is None:
        at_epoch = _now_epoch()
    factor = distance_factor(tuple(origin), tuple(target), at_epoch, cfg)
    return max(1, int(round(base * factor)))
