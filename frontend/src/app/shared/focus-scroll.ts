/**
 * Deeplink-Hilfe fuer „Dashboard -> laufender Prozess": scrollt die per Query-Param `focus`
 * angesprungene Bau-/Forschungs-/Werft-Kachel sanft in den Blick. Die Kachel bekommt im
 * Screen `id="tile-<type>"` und (kurzzeitig) `[focused]` fuer den Aufmerk-Flash.
 */
export function scrollToTile(type: string): void {
  // Kurzer Verzug, bis Tab/Grid gerendert sind.
  setTimeout(() => {
    document.getElementById('tile-' + type)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 200);
}
