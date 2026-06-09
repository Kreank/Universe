"""Reiner Preis-Kern des Handelssystems (Anfliegen-Modell, X4-inspiriert).

Spieler fliegen Ressourcen (Metall/Kristall/Deuterium) zu Haendler-NPCs und tauschen.
KEIN Festkurs: Der Preis je Ressource haengt am Lagerbestand des Haendlers
(``price_of``). Eine Order wird **chunk-weise** gegen den Bestand abgerechnet, sodass
eine grosse Order den Kurs gegen den Spieler bewegt (**Slippage**): Verkauft der Spieler
viel, steigt der Bestand und der Preis faellt waehrend des Verkaufs; kauft er viel leer,
faellt der Bestand und der Preis steigt waehrend des Kaufs.

Jeder Haendler hat je Ressource einen **Sollbestand** (``setpoint``). Spezialisierungen
(``specializations`` in balance.json) skalieren den Sollbestand je Ressource -> Preis-
Differenziale zwischen Haendlern -> Arbitrage. ``reputation`` senkt die ``margin`` (Spanne
zugunsten des Haendlers) fuer Stammkunden.

Wie die Kampf-Engine: rein, deterministisch (KEINE Zufaelligkeit), ohne DB/IO -> direkt
testbar und identisch zur spaeteren In-Game-Abwicklung (eine Wahrheit, kein Drift).
Typen ueber dicts; der Aufrufer rundet spaeter (intern wird NICHT zu frueh gerundet).
"""
from __future__ import annotations

from typing import Any


def price_of(resource: str, stock: float, setpoint: float, cfg: dict) -> float:
    """Aktueller Preis einer Ressource bei einem Haendler (Wert je Einheit).

    base = cfg['base_value'][resource]; raw = base * (setpoint / max(stock, 1));
    Ergebnis wird auf [base*price_min_mult, base*price_max_mult] geclamped.
    Hoher Bestand -> billig, knapper Bestand -> teuer. Robust gegen stock <= 0
    (Nenner mindestens 1, verhindert Division durch 0 / Preis-Explosion)."""
    base_map = cfg["base_value"]
    if resource not in base_map:
        raise ValueError(f"unbekannte Ressource: {resource!r}")
    base = float(base_map[resource])
    raw = base * (float(setpoint) / max(float(stock), 1.0))
    lo = base * float(cfg["price_min_mult"])
    hi = base * float(cfg["price_max_mult"])
    # clamp auf [lo, hi]
    return max(lo, min(hi, raw))


def effective_margin(reputation_level: int, cfg: dict) -> float:
    """Effektive Haendler-Marge nach Reputation.

    margin - rep_level * margin_reduction_per_level; rep_level wird auf [0, max_level]
    gedeckelt und das Ergebnis auf >= 0 geklemmt (Marge wird nie negativ)."""
    rep = cfg["reputation"]
    level = max(0, min(int(reputation_level), int(rep["max_level"])))
    margin = float(cfg["margin"]) - level * float(rep["margin_reduction_per_level"])
    return max(0.0, margin)


def _check_resource(resource: str, cfg: dict) -> None:
    if resource not in cfg["base_value"]:
        raise ValueError(f"unbekannte Ressource: {resource!r}")


def simulate_swap(
    offer_res: str,
    offer_amount: float,
    want_res: str,
    stock: dict,
    setpoint: dict,
    cfg: dict,
    reputation_level: int = 0,
    cargo_capacity: float | None = None,
) -> dict[str, Any]:
    """Simuliert einen Tausch chunk-weise -> Slippage in BEIDE Richtungen.

    Der Spieler bietet ``offer_amount`` von ``offer_res`` an und erhaelt ``want_res``.

    Ablauf:
    1. **Verkauf** (Haendler KAUFT offer_res): ``offer_amount`` wird in ``swap_steps``
       gleich grosse Chunks zerlegt. Je Chunk
       ``value_in += price_of(offer_res, stock_offer, ...) * dq`` und ``stock_offer += dq``.
       Da der Bestand steigt, faellt der Preis -> spaetere Chunks sind weniger wert
       (Slippage zuungunsten des Verkaeufers).
    2. **Budget**: ``budget = value_in * (1 - effective_margin(rep, cfg))`` (Marktwert
       abzueglich Haendler-Spanne).
    3. **Kauf** (Spieler KAUFT want_res): erneut chunk-weise (~swap_steps Chunks der
       Soll-Menge), solange Budget reicht UND ``stock_want > min_stock_floor`` UND
       (cargo_capacity None oder received < cargo_capacity). Je Chunk
       ``cost = price_of(want_res, stock_want, ...) * dq``; an der Budget-/Cap-/Stock-
       Grenze wird ``dq`` anteilig gekuerzt. ``received += dq``, ``stock_want -= dq``.
       Da der Bestand faellt, steigt der Preis -> spaetere Chunks teurer (Slippage).

    ``stock``/``setpoint`` sind dicts {metal, crystal, deuterium}; sie werden NICHT
    mutiert (es wird auf Kopien gerechnet). Das nicht ausgegebene Budget verfaellt nicht,
    sondern wird als ``refund_value`` (Wert-Aequivalent in der Tauschwaehrung) zurueck-
    gegeben -> der Aufrufer entscheidet, ob er es als want_res ODER offer_res erstattet.

    Sonderfaelle: offer_res == want_res, offer_amount <= 0, unbekannte Ressource -> ValueError.

    Rueckgabe-Dict:
      received        Menge want_res fuer den Spieler
      value_in        Marktwert des Angebots (vor Marge)
      margin          angewandte effektive Marge
      avg_sell_price  value_in / offer_amount (Slippage des Verkaufs sichtbar)
      avg_buy_price   spent / received (oder 0 wenn received == 0)
      new_stock       Haendler-Bestand nach dem Tausch (offer hoch, want runter)
      spent           tatsaechlich ausgegebenes Budget (<= budget)
      refund_value    nicht ausgegebenes Budget (budget - spent)
    """
    # --- Validierung ---
    _check_resource(offer_res, cfg)
    _check_resource(want_res, cfg)
    if offer_res == want_res:
        raise ValueError("offer_res und want_res muessen verschieden sein")
    if offer_amount <= 0:
        raise ValueError("offer_amount muss > 0 sein")

    steps = max(1, int(cfg["swap_steps"]))
    floor = float(cfg["min_stock_floor"])
    offer_amount = float(offer_amount)

    # Auf Kopien arbeiten -> Eingaben bleiben unberuehrt.
    stock = dict(stock)
    setpoint = dict(setpoint)
    sp_offer = float(setpoint[offer_res])
    sp_want = float(setpoint[want_res])

    # --- 1) Verkauf: Haendler kauft offer_res chunk-weise (Bestand steigt -> Preis faellt) ---
    stock_offer = float(stock[offer_res])
    dq_sell = offer_amount / steps
    value_in = 0.0
    for _ in range(steps):
        value_in += price_of(offer_res, stock_offer, sp_offer, cfg) * dq_sell
        stock_offer += dq_sell

    # --- 2) Budget nach Marge ---
    margin = effective_margin(reputation_level, cfg)
    budget = value_in * (1.0 - margin)

    # --- 3) Kauf: Spieler kauft want_res chunk-weise (Bestand faellt -> Preis steigt) ---
    stock_want = float(stock[want_res])
    received = 0.0
    spent = 0.0
    # Soll-Chunk fuer den Kauf: ein gleich grosser Anteil eines "vollen" Sollbestands-
    # Schritts; das nutzt dieselbe Chunk-Granularitaet wie der Verkauf. Der letzte Chunk
    # wird an jeder Grenze (Budget/Cap/Stock-Floor) anteilig gekuerzt.
    dq_buy_full = max(sp_want / steps, 1e-9)

    # Sicherheits-Guard gegen Endlosschleifen, falls ein Chunk auf ~0 gekuerzt wird.
    guard = 0
    max_iter = steps * 4 + 16
    while guard < max_iter:
        guard += 1
        # Abbruch, wenn Bestand am Floor (Leerkauf-Schutz: stock_want darf nicht
        # unter min_stock_floor fallen).
        room_stock = stock_want - floor
        if room_stock <= 0:
            break
        # Restbudget aufgebraucht?
        room_budget_value = budget - spent
        if room_budget_value <= 0:
            break
        # Cargo-Cap erreicht?
        if cargo_capacity is not None:
            room_cargo = float(cargo_capacity) - received
            if room_cargo <= 0:
                break
        else:
            room_cargo = None

        # Preis fuer diesen Chunk (am AKTUELLEN Bestand -> Slippage).
        price = price_of(want_res, stock_want, sp_want, cfg)

        # Gewuenschte Chunk-Menge, anteilig an allen Grenzen kuerzen.
        dq = dq_buy_full
        dq = min(dq, room_stock)                 # nicht unter den Floor
        dq = min(dq, room_budget_value / price)  # nicht mehr als das Budget hergibt
        if room_cargo is not None:
            dq = min(dq, room_cargo)             # nicht ueber die Frachtkapazitaet

        if dq <= 0:
            break

        received += dq
        spent += price * dq
        stock_want -= dq

    refund_value = max(0.0, budget - spent)

    new_stock = dict(stock)
    new_stock[offer_res] = stock_offer
    new_stock[want_res] = stock_want

    return {
        "received": received,
        "value_in": value_in,
        "margin": margin,
        "avg_sell_price": value_in / offer_amount if offer_amount > 0 else 0.0,
        "avg_buy_price": spent / received if received > 0 else 0.0,
        "new_stock": new_stock,
        "spent": spent,
        "refund_value": refund_value,
    }
