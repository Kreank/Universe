"""Endgame-Forschungen kosten zusaetzlich Dunkle Materie (ausser research_network/terraforming).

Die Dunkle-Materie-Kosten stecken im ``cost``-Block der balance.json und werden von
``cost_for_level`` zusammen mit metal/crystal/deuterium pro Stufe skaliert. ``spend_resources``
(Economy) zieht ``dark_matter`` bereits ab (Exoten pro Planet) — hier wird die Kosten-Quelle
geprueft, die in den Spend-Pfad fliesst."""
from app.platform.balance import get_balance
from app.research.service import cost_for_level

# Endgame-Forschungen, die zusaetzlich Dunkle Materie kosten sollen (Branch "Endgame"
# aus display.ts, OHNE research_network und terraforming).
ENDGAME_WITH_DM = (
    "graviton_tech",
    "weapons_mastery",
    "shield_mastery",
    "armor_mastery",
    "extraction_mastery",
    "flagship_command",
    "corsair_command",
    "leviathan_command",
    "harvest_command",
    "veteran_shipyard",
)


def test_endgame_techs_demand_dark_matter():
    for tech in ENDGAME_WITH_DM:
        cost = cost_for_level(tech, 0)
        assert cost.get("dark_matter", 0) > 0, f"{tech} sollte Dunkle Materie kosten"


def test_excluded_endgame_techs_have_no_dark_matter():
    # Forschungsnetzwerk und Terraforming sind bewusst ausgenommen.
    for tech in ("research_network", "terraforming"):
        cost = cost_for_level(tech, 0)
        assert cost.get("dark_matter", 0) == 0, f"{tech} darf KEINE Dunkle Materie kosten"


def test_non_endgame_tech_has_no_dark_matter():
    assert cost_for_level("weapons_tech", 0).get("dark_matter", 0) == 0


def test_dark_matter_scales_with_level_like_mcd():
    # Repeatable-Tech: linear-additiv (base * (level+1)) — DM skaliert wie metal/crystal/deuterium.
    base = get_balance().techs["weapons_mastery"]["cost"]["dark_matter"]
    assert cost_for_level("weapons_mastery", 0)["dark_matter"] == round(base, 2)
    assert cost_for_level("weapons_mastery", 4)["dark_matter"] == round(base * 5, 2)

    # Nicht-repeatable Endgame-Tech: exponentiell (base * 2^level).
    g_base = get_balance().techs["graviton_tech"]["cost"]["dark_matter"]
    assert cost_for_level("graviton_tech", 3)["dark_matter"] == round(g_base * 8, 2)
