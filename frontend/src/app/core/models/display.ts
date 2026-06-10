/**
 * Anzeige-Labels, Kurzbeschreibungen und Platzhalter-Icon-Glyphen.
 * Die `type`-Keys stammen aus `shared/balance.json`. Labels werden hier
 * fuer das deutsche UI gepflegt; der Server bleibt autoritativ fuer Zahlen.
 *
 * Asset-Pfade sind so strukturiert, dass die Glyph-Platzhalter spaeter durch
 * echte Bilder ersetzt werden koennen (z. B. assets/img/ships/light_fighter.svg).
 */

export interface DisplayMeta {
  label: string;
  glyph: string;
  /** Kurz-Hinweis (Tooltip, eine Zeile). */
  blurb?: string;
  /** Ausfuehrliche Beschreibung / "kleine Geschichte" fuer die Detail-Ansicht. */
  desc?: string;
}

export const RESOURCE_META: Record<string, DisplayMeta> = {
  metal: { label: 'Metall', glyph: '⛏️', blurb: 'Grundbaustoff fuer alles.' },
  crystal: { label: 'Kristall', glyph: '💎', blurb: 'Elektronik und Forschung.' },
  deuterium: { label: 'Deuterium', glyph: '🛢️', blurb: 'Treibstoff und Fusion.' },
  energy: { label: 'Energie', glyph: '⚡', blurb: 'Treibt die Minen an.' },
};

export const BUILDING_META: Record<string, DisplayMeta> = {
  metal_mine: {
    label: 'Metallmine', glyph: '⛏️', blurb: 'Foerdert Metall.',
    desc: 'Förderschächte treiben tief in die Kruste des Planeten. Metall ist das Rückgrat jeder Werft und jedes Gebäudes — eine Kolonie wächst nur so schnell wie ihre Metallmine. Jede Stufe steigert die Förderrate, verlangt aber spürbar mehr Energie.',
  },
  crystal_mine: {
    label: 'Kristallmine', glyph: '💠', blurb: 'Foerdert Kristall.',
    desc: 'Kristalline Adern werden mit Schneidlasern aus dem Gestein gelöst. Kristall steckt in jeder Elektronik, jedem Triebwerk und jeder Forschung — knapper und teurer als Metall, aber unverzichtbar für höhere Technik.',
  },
  deuterium_synth: {
    label: 'Deuterium-Synthesizer', glyph: '🛢️', blurb: 'Gewinnt Deuterium.',
    desc: 'Schwerwasser-Reaktoren filtern Deuterium aus der Atmosphäre. Der Treibstoff aller Flotten und der Brennstoff der Fusion — kalte Welten geben mehr her als heiße. Ohne Deuterium bleibt jede Flotte am Boden.',
  },
  solar_plant: {
    label: 'Solarkraftwerk', glyph: '☀️', blurb: 'Erzeugt Energie.',
    desc: 'Weite Solarsegel fangen das Sternenlicht ein. Die verlässlichste Energiequelle einer jungen Kolonie — auf Feuerwelten brennt sie am hellsten. Reicht die Energie nicht, drosseln alle Minen ihre Förderung.',
  },
  fusion_reactor: {
    label: 'Fusionsreaktor', glyph: '🔆', blurb: 'Energie aus Deuterium.',
    desc: 'Verbrennt Deuterium in einem eingeschlossenen Plasma und liefert Energie unabhängig vom Sternenlicht. Teuer im Unterhalt, aber die Antwort, wenn die Solarsegel an ihre Grenzen kommen.',
  },
  robot_factory: {
    label: 'Roboterfabrik', glyph: '🤖', blurb: 'Beschleunigt Bauten.',
    desc: 'Autonome Bautrupps und Schwerlast-Roboter verkürzen jede Bauzeit auf dem Planeten. Eine frühe Investition, die sich über jede spätere Stufe hinweg auszahlt.',
  },
  shipyard: {
    label: 'Werft', glyph: '🛠️', blurb: 'Baut Schiffe & Verteidigung.',
    desc: 'Das Herz der militärischen Macht: hier entstehen Flotten und planetare Verteidigung. Höhere Stufen schalten größere Rümpfe frei und lassen die Hellinge schneller arbeiten.',
  },
  research_lab: {
    label: 'Forschungslabor', glyph: '🔬', blurb: 'Schaltet Technologien frei.',
    desc: 'Reinraumlabore und Testkammern, in denen neue Technik aus der Theorie in den Einsatz wandert. Jede Stufe beschleunigt die Forschung — ohne Labor steht der gesamte Techbaum still.',
  },
  metal_storage: {
    label: 'Metallspeicher', glyph: '🏗️', blurb: 'Erhoeht Metall-Kapazitaet.',
    desc: 'Massive Bunker fassen die Metallförderung. Ist der Speicher voll, geht jede weitere Förderung verloren — und volle Lager sind ein verlockendes Ziel für Angreifer.',
  },
  crystal_storage: {
    label: 'Kristallspeicher', glyph: '🏬', blurb: 'Erhoeht Kristall-Kapazitaet.',
    desc: 'Klimatisierte Hallen lagern den empfindlichen Kristall. Mehr Kapazität bedeutet, dass du über Nacht Vorräte für teure Forschung und Großbauten anhäufen kannst.',
  },
  deuterium_tank: {
    label: 'Deuteriumtank', glyph: '🛢️', blurb: 'Erhoeht Deuterium-Kapazitaet.',
    desc: 'Druckisolierte Tanks halten den flüchtigen Treibstoff. Großoffensiven verschlingen Unmengen Deuterium — ohne Reserven bleibt die Flotte im Hangar.',
  },
  command_academy: {
    label: 'Kommando-Akademie', glyph: '🎖️', blurb: 'Bildet Commander aus.',
    desc: 'Hier werden aus Rekruten Commander geformt — Menschen, die deine Flotten führen und ihre Moral tragen. Das Fundament der Doktrin „Befehlige nicht nur Flotten, führe Menschen."',
  },
  command_center: {
    label: 'Kommandozentrale', glyph: '📡', blurb: 'Erhoeht Span of Control.',
    desc: 'Das Nervenzentrum deines Imperiums. Jede Stufe erweitert deine Befehlsreichweite (Span of Control) — also wie viele Commander du gleichzeitig im Einsatz halten kannst.',
  },
};

export const TECH_META: Record<string, DisplayMeta> = {
  energy_tech: {
    label: 'Energietechnik', glyph: '⚡', blurb: 'Grundlage vieler Technologien.',
    desc: 'Die Lehre vom Bändigen und Leiten reiner Energie. Klingt unscheinbar, ist aber das Tor zu fast allem Höheren — von Lasern bis zur Fusion baut der halbe Techbaum auf ihr auf.',
  },
  combustion_drive: {
    label: 'Verbrennungstriebwerk', glyph: '🚀', blurb: 'Antrieb leichter Schiffe.',
    desc: 'Der erste echte Schub: chemische Verbrennung treibt Jäger und Transporter durchs System. Jede Stufe macht diese Schiffe schneller — der Einstieg in jede Flotte.',
  },
  impulse_drive: {
    label: 'Impulstriebwerk', glyph: '🛸', blurb: 'Schnellerer Antrieb.',
    desc: 'Ein Quantensprung gegenüber der Verbrennung: Impulskammern beschleunigen die mittlere Schiffsklasse. Wer schneller am Ziel ist, diktiert, wann gekämpft wird.',
  },
  spy_tech: {
    label: 'Spionagetechnik', glyph: '🛰️', blurb: 'Ermoeglicht Sonden.',
    desc: 'Sensorik, Verschlüsselung und das Handwerk des Lauschens. Schaltet Spionagesonden frei — denn ein Angriff ins Blinde ist nur ein teurer Selbstmord.',
  },
  computer_tech: {
    label: 'Computertechnik', glyph: '💻', blurb: '+1 Flottenslot pro Stufe.',
    desc: 'Rechenleistung für Flottenkoordination. Jede Stufe erlaubt dir, eine Flotte mehr gleichzeitig ins Feld zu führen — die stille Voraussetzung für jeden, der an mehreren Fronten spielt.',
  },
  weapons_tech: {
    label: 'Waffentechnik', glyph: '🔫', blurb: '+10% Angriff pro Stufe.',
    desc: 'Bessere Läufe, dichtere Munition, präzisere Zielrechner. Jede Stufe erhöht den Angriffswert deiner gesamten Flotte um 10 % — ein Bonus, der jedes Gefecht durchschlägt.',
  },
  shield_tech: {
    label: 'Schildtechnik', glyph: '🛡️', blurb: '+10% Schild pro Stufe.',
    desc: 'Energieschirme, die den ersten Treffer schlucken, bevor die Hülle leidet. +10 % Schildkraft pro Stufe für die ganze Flotte — was überlebt, kann zurückschlagen.',
  },
  armor_tech: {
    label: 'Panzerung', glyph: '🪖', blurb: '+10% Huelle pro Stufe.',
    desc: 'Verbundpanzerung und Schottwände. +10 % Hüllenintegrität pro Stufe — die rohe Lebensversicherung deiner Schiffe, wenn die Schilde fallen.',
  },
  command_doctrine: {
    label: 'Kommando-Doktrin', glyph: '📖', blurb: '+Span of Control.',
    desc: 'Die Kunst, mehr Menschen zu führen, ohne die Kontrolle zu verlieren. Erweitert deine Befehlsreichweite — mehr Commander, mehr gleichzeitig geführte Operationen.',
  },
  logistics_tech: {
    label: 'Logistik', glyph: '📦', blurb: 'Schnellere Moral-Erholung.',
    desc: 'Nachschub, Rotation, Ruhephasen: gute Logistik bringt erschöpfte Crews schneller zurück in Form. Lässt die Moral deiner Commander rascher regenerieren.',
  },
  crew_psychology: {
    label: 'Crew-Psychologie', glyph: '🧠', blurb: 'Hoehere Moral-Decke.',
    desc: 'Wer Menschen führt, muss sie verstehen. Hebt die Obergrenze der Moral — gut betreute Crews kämpfen mit einem Feuer, das Maschinen nie aufbringen.',
  },
  laser_tech: {
    label: 'Lasertechnik', glyph: '🔦', blurb: 'Lasergeschuetze & Schlachtkreuzer.',
    desc: 'Gebündeltes Licht, das Schilde aufreißt. Öffnet das Tor zu Lasergeschützen und schlagkräftigeren Kriegsschiffen — der erste Schritt vom Jäger zur echten Kampfflotte.',
  },
  ion_tech: {
    label: 'Ionentechnik', glyph: '🌀', blurb: 'Ionengeschuetze & Kreuzer.',
    desc: 'Geladene Teilchenströme, die Schilde leerfressen und Subsysteme lahmlegen. Grundlage von Kreuzern und Ionengeschützen — weniger Zerstörer, mehr Entwaffner.',
  },
  plasma_tech: {
    label: 'Plasmatechnik', glyph: '🔥', blurb: 'Plasmawerfer, Bomber & Zerstoerer.',
    desc: 'Auf Sterntemperatur erhitzte Materie als Waffe. Schaltet die brutalste Verteidigung und die schwersten Angriffsschiffe frei — Plasma verzeiht keine Hülle.',
  },
  hyperspace_tech: {
    label: 'Hyperraumtechnik', glyph: '🌌', blurb: 'Grundlage fuer Grosskampfschiffe.',
    desc: 'Das Verständnis des gefalteten Raums. Selbst keine Waffe, aber das Fundament jedes Großkampfschiffs — ohne sie bleibt die schwere Flotte ein Traum.',
  },
  hyperspace_drive: {
    label: 'Hyperraumantrieb', glyph: '🌠', blurb: 'Antrieb schwerer Kriegsschiffe.',
    desc: 'Faltet den Raum und schleudert tonnenschwere Rümpfe über Systemgrenzen. Der Antrieb der Schlachtschiffe und Zerstörer — langsam zu erforschen, aber unverzichtbar für Reichweite.',
  },
  graviton_tech: {
    label: 'Gravitontechnik', glyph: '🌑', blurb: 'Ermoeglicht den Todesstern.',
    desc: 'Die Beherrschung künstlicher Schwerkraft — die Königsdisziplin der Forschung. Einzige Voraussetzung für den Todesstern, eine mobile Festung von der Größe eines Mondes.',
  },
};

export const SHIP_META: Record<string, DisplayMeta> = {
  light_fighter: {
    label: 'Leichter Jaeger', glyph: '🛩️', blurb: 'Schnell und billig.',
    desc: 'Das billige Arbeitstier jeder Werft — schnell gebaut, schnell verheizt. Einzeln kaum mehr als ein Funkenflug, doch in Schwärmen erdrücken leichte Jäger jeden Gegner unter schierer Masse.',
  },
  heavy_fighter: {
    label: 'Schwerer Jaeger', glyph: '✈️', blurb: 'Robuster Angreifer.',
    desc: 'Der ältere, gepanzerte Bruder des leichten Jägers. Trägt mehr Feuerkraft und steckt mehr ein — das Rückgrat einer frühen Angriffsflotte, bevor die großen Rümpfe kommen.',
  },
  cruiser: {
    label: 'Kreuzer', glyph: '🚀', blurb: 'Schlagkraeftiges Kriegsschiff.',
    desc: 'Schnell, schlagkräftig und gefürchtet von Jägerschwärmen: gegen leichte Jäger feuert der Kreuzer in rascher Folge. Das erste Schiff, das ein Schlachtfeld wirklich dominiert.',
  },
  small_cargo: {
    label: 'Kleiner Transporter', glyph: '📦', blurb: 'Transportiert Ressourcen.',
    desc: 'Wendiger Frachter für den schnellen Ressourcen-Pendelverkehr. Klein, billig, unbewaffnet — aber ohne diese Schiffe verhungert jede Kolonie und jede Beute bleibt liegen.',
  },
  large_cargo: {
    label: 'Grosser Transporter', glyph: '🚛', blurb: 'Hohe Frachtkapazitaet.',
    desc: 'Ein fliegender Laderaum. Langsamer als der kleine Transporter, aber er schleppt ein Vielfaches — die Wahl, wenn ganze Trümmerfelder oder Plünderzüge nach Hause müssen.',
  },
  colony_ship: {
    label: 'Kolonieschiff', glyph: '🪐', blurb: 'Gruendet neue Kolonien.',
    desc: 'Eine Arche aus Stahl: trägt alles, um auf einer leeren Welt eine neue Kolonie zu gründen. Teuer und träge, aber jedes neue Imperium beginnt mit genau diesem Schiff.',
  },
  recycler: {
    label: 'Recycler', glyph: '♻️', blurb: 'Sammelt Truemmerfelder ein.',
    desc: 'Nach jeder Schlacht treibt Schrott im Orbit — der Recycler erntet ihn. Wer die Trümmerfelder einsammelt, finanziert seinen Krieg mit den Wracks des Feindes.',
  },
  solar_satellite: {
    label: 'Solarsatellit', glyph: '🛰️', blurb: 'Liefert Energie im Orbit.',
    desc: 'Eine schwebende Solarplattform ohne Antrieb. Liefert günstig Energie an den Planeten — aber wehrlos: bei einem Angriff ist sie das erste, was zerschossen wird.',
  },
  spy_probe: {
    label: 'Spionagesonde', glyph: '📡', blurb: 'Spaeht Ziele aus.',
    desc: 'Winzig, schnell, kaum zu treffen. Huscht ins feindliche Orbit, funkt zurück, was sie sieht — Flotten, Verteidigung, Vorräte. Wissen, das einen Angriff entscheidet, bevor er beginnt.',
  },
  battleship: {
    label: 'Schlachtschiff', glyph: '🚀', blurb: 'Rueckgrat der Kampfflotte.',
    desc: 'Der breitschultrige Linienkämpfer, an dem sich jede Schlacht festbeißt. Viel Hülle, schwere Geschütze, kein besonderer Trick — einfach die Wand, hinter der deine Flotte steht.',
  },
  battlecruiser: {
    label: 'Schlachtkreuzer', glyph: '⚔️', blurb: 'Schnell und schlagkraeftig.',
    desc: 'Die Faust, die zuerst zuschlägt: fast so schwer bewaffnet wie ein Schlachtschiff, aber deutlich schneller. Ideal für Blitzangriffe, ehe der Gegner seine Flotte sammeln kann.',
  },
  bomber: {
    label: 'Bomber', glyph: '💣', blurb: 'Bricht feindliche Verteidigung.',
    desc: 'Spezialist fürs grobe Geschäft: Plasmabomben, die planetare Verteidigung in Schutt legen. Gegen Geschütztürme unschlagbar, gegen wendige Schiffe träge und verwundbar.',
  },
  destroyer: {
    label: 'Zerstoerer', glyph: '🔱', blurb: 'Schwerer Linienkaempfer.',
    desc: 'Eines der schwersten Kriegsschiffe überhaupt — eine wandelnde Geschützbatterie. Wo ein Zerstörer auftaucht, kippt die Schlacht; nur Masse oder ein Todesstern halten ihn auf.',
  },
  deathstar: {
    label: 'Todesstern', glyph: '🌑', blurb: 'Mobile Kampfstation.',
    desc: 'Eine Festung von der Größe eines Mondes, gebaut aus Gravitontechnik. Nahezu unzerstörbar und mit Geschützen, die ganze Flotten zerstäuben — die ultimative Machtdemonstration. Schwerfällig, aber Furcht erregend.',
  },
  carrier: {
    label: 'Traeger', glyph: '🛸', blurb: 'Kraftmultiplikator, startet Drohnen.',
    desc: 'Kämpft nicht selbst, sondern entfesselt Schwärme: der Träger startet Drohnen und verstärkt die Schiffe um sich herum. Ein Kraftmultiplikator, dessen Verlust eine ganze Flotte schwächt.',
  },
  drone: {
    label: 'Drohne', glyph: '🛩️', blurb: 'Billige Schwarm-Einheit.',
    desc: 'Unbemannt, spottbillig, in Massen verfügbar. Allein bedeutungslos, im Schwarm eine Lawine — vom Träger ins Gefecht geschleudert, um den Feind in Zahlen zu ertränken.',
  },
  interdictor: {
    label: 'Interdiktor', glyph: '🧲', blurb: 'Fang-Feld: verhindert Flucht.',
    desc: 'Spannt ein Massefeld auf, das gegnerischen Schiffen die Flucht abschneidet. Kein großer Kämpfer — aber er verwandelt einen Rückzug in eine Falle, aus der kein Fleetsave rettet.',
  },
  ewar_frigate: {
    label: 'EWAR-Fregatte', glyph: '⚡', blurb: 'Ionen: leert Schilde, legt Antrieb lahm.',
    desc: 'Elektronische Kriegsführung in Reinform: Ionensalven leeren feindliche Schilde und legen Antriebe lahm. Richtet selbst kaum Schaden an, macht den Feind aber reif für die Schlächter.',
  },
  boarder: {
    label: 'Enterschiff', glyph: '🪝', blurb: 'Kapert gestrandete Schiffe.',
    desc: 'Klammert sich an antriebslose Wracks und schickt Enterkommandos hinüber. Wo andere zerstören, raubt der Boarder — gestrandete Feindschiffe wechseln einfach die Seite.',
  },
  stealth_corvette: {
    label: 'Tarnkappen-Korvette', glyph: '🌫️', blurb: 'Stealth, eroeffnet den Ueberfall.',
    desc: 'Gleitet ungesehen heran und eröffnet das Gefecht aus dem Nichts. Die Tarnkappen-Korvette ist die Klinge im Dunkeln — ein Hinterhalt, der entschieden ist, bevor der Feind überhaupt zielt.',
  },
  escort_frigate: {
    label: 'Eskort-Fregatte', glyph: '🛡️', blurb: 'Punktverteidigung, schirmt Fracht.',
    desc: 'Die Leibwache des Konvois: ihre Punktverteidigung fängt Raketen und Drohnen ab, bevor sie die Fracht erreichen. Defensiv, geduldig, unverzichtbar für sichere Transporte.',
  },
  shield_tender: {
    label: 'Schild-Tender', glyph: '🔆', blurb: 'Projiziert Schilde im Gefecht.',
    desc: 'Spannt im Gefecht einen Schildschirm über benachbarte Schiffe. Selbst zerbrechlich, hält er andere am Leben — und wird vom Gegner zu Recht zuerst ins Visier genommen.',
  },
  interceptor: {
    label: 'Abfangjaeger', glyph: '🏹', blurb: 'Sehr schnell, Anti-Jaeger.',
    desc: 'Gebaut für eine einzige Aufgabe: feindliche Jäger einholen und zerreißen. Extrem schnell, gegen größere Schiffe aber zerbrechlich — der Wächter über deinem eigenen Luftraum.',
  },
  miner: {
    label: 'Bergbauschiff', glyph: '⛏️', blurb: 'Mobiler Rohstoff-Abbau.',
    desc: 'Eine fliegende Mine. Setzt sich auf Asteroiden und reiche Felder und fördert Rohstoffe fern der Heimat — der Motor jeder Bergbau-Expansion.',
  },
  deep_scout: {
    label: 'Tief-Aufklaerer', glyph: '🔭', blurb: 'Langstrecken-Aufklaerung.',
    desc: 'Späht weiter, als jede Sonde reicht. Der Tief-Aufklärer kartiert ferne Systeme und Anomalien — die Augen des Imperiums an seinen Rändern.',
  },
  expedition_ship: {
    label: 'Expeditions-Schiff', glyph: '🧭', blurb: 'Erkundung und Langstrecke.',
    desc: 'Gebaut für die Reise ins Ungewisse: lange Reichweite, robuste Systeme, Platz für Funde. Schickt es in die Leere zwischen den Sternen — was es zurückbringt, ist nie vorhersehbar.',
  },
};

export const DEFENSE_META: Record<string, DisplayMeta> = {
  rocket_launcher: {
    label: 'Raketenwerfer', glyph: '🚀', blurb: 'Guenstige Verteidigung.',
    desc: 'Die billigste Mauer, die du ziehen kannst. Einzeln ein Pappkamerad, in Hunderten aber eine Wand aus Raketen, an der sich kleine Angriffsflotten die Zähne ausbeißen.',
  },
  light_laser: {
    label: 'Leichtes Lasergeschuetz', glyph: '🔦', blurb: 'Solide Verteidigung.',
    desc: 'Solides Brot-und-Butter-Geschütz: günstig, schildbrechend und in Masse erstaunlich zäh. Das Fundament fast jeder planetaren Verteidigung.',
  },
  heavy_laser: {
    label: 'Schweres Lasergeschuetz', glyph: '🔆', blurb: 'Robusteres Lasergeschuetz.',
    desc: 'Der größere Bruder des leichten Lasers — mehr Reichweite, mehr Hülle, mehr Biss. Hält dort stand, wo leichte Geschütze schon Funken sprühen.',
  },
  gauss_cannon: {
    label: 'Gausskanone', glyph: '🎯', blurb: 'Anti-Grosskampfschiff.',
    desc: 'Beschleunigt ein Projektil auf wahnwitzige Geschwindigkeit und durchschlägt selbst dicke Panzerung. Spezialist gegen Großkampfschiffe — gegen Jägerschwärme aber zu träge.',
  },
  ion_cannon: {
    label: 'Ionengeschuetz', glyph: '🌀', blurb: 'Hoher Schild, Schildtank.',
    desc: 'Ein Geschütz mit gewaltigem Eigenschild, das den feindlichen Beschuss schluckt und Schilde leerfrisst. Der Schildtank deiner Stellung — hält lange, schlägt mittel.',
  },
  plasma_turret: {
    label: 'Plasmawerfer', glyph: '🔥', blurb: 'Staerkste Verteidigung.',
    desc: 'Die brutalste Verteidigung, die ein Planet aufbieten kann: Plasmasalven, die durch Schild und Hülle gleichermaßen brennen. Teuer, aber jeder Angreifer rechnet zweimal.',
  },
  small_shield_dome: {
    label: 'Kleine Schildkuppel', glyph: '🛡️', blurb: 'Max. 1 pro Planet.',
    desc: 'Ein planetenweiter Energieschirm, der einen Teil jedes Angriffs absorbiert. Nur einmal pro Planet baubar — aber dieser eine Schild kann eine Schlacht überstehen lassen.',
  },
  large_shield_dome: {
    label: 'Grosse Schildkuppel', glyph: '🛡️', blurb: 'Max. 1 pro Planet.',
    desc: 'Die ausgereifte Schildkuppel: schluckt ein Vielfaches der kleinen Version. Zusammen bilden beide Kuppeln einen Schirm, der selbst schweren Bombardements trotzt.',
  },
  anti_ballistic_missile: {
    label: 'Abfangrakete', glyph: '🚀', blurb: 'Faengt Interplanetarraketen ab.',
    desc: 'Reine Versicherung: jede Abfangrakete fängt genau eine feindliche Interplanetarrakete ab, bevor sie deine Verteidigung trifft. Unsichtbar im Lager — bis der Tag kommt, an dem sie alles rettet.',
  },
  interplanetary_missile: {
    label: 'Interplanetarrakete', glyph: '☄️', blurb: 'Zerstoert feindliche Verteidigung.',
    desc: 'Der Vorschlaghammer aus der Ferne: schlägt über Systemgrenzen in die feindliche Verteidigung ein, ohne dass eine Flotte fliegen muss. Reißt Löcher, durch die danach deine Schiffe stoßen.',
  },
};

/**
 * Waffen-Typen der Rollen-Kampf-Profile (balance.json `combat_roster`).
 * `vs` haelt den statischen Effektivitaets-Hinweis (Design-fix, siehe `damage_matrix`).
 */
export const WEAPON_META: Record<string, { label: string; glyph: string; vs: string }> = {
  kinetic: { label: 'Kinetik', glyph: '💥', vs: 'stark vs. Hülle, schwach vs. Schild' },
  energy: { label: 'Energie', glyph: '⚡', vs: 'stark vs. Schild' },
  ion: { label: 'Ionen', glyph: '🌀', vs: 'lähmt Antrieb/Subsysteme, 0 vs. Hülle' },
  missile: { label: 'Raketen', glyph: '🚀', vs: 'stark vs. Hülle' },
};

/** Reichweiten-Baender (Farbsemantik konsistent zum Kampfbericht-Viewer). */
export const RANGE_META: Record<string, { label: string; dot: string }> = {
  near: { label: 'Nah', dot: '🔴' },
  medium: { label: 'Mittel', dot: '🟡' },
  far: { label: 'Fern', dot: '🔵' },
};

/** Planetentypen (aus der Position abgeleitet, Doku 06a). */
export const PLANET_TYPE_META: Record<string, DisplayMeta> = {
  fire: { label: 'Feuerplanet', glyph: '🔥', blurb: 'Sehr heiss, wenige Felder, viel Solarenergie.' },
  barren: { label: 'Karger Planet', glyph: '🪨', blurb: 'Heiss-gemaessigt, mittlere Felder.' },
  normal: { label: 'Normal', glyph: '🌍', blurb: 'Ausgewogen, meiste Felder.' },
  cold: { label: 'Kalter Planet', glyph: '❄️', blurb: 'Kuehl, mehr Deuterium.' },
  ice: { label: 'Eisplanet', glyph: '🧊', blurb: 'Sehr kalt, viel Deuterium.' },
};

export const MISSION_META: Record<string, DisplayMeta> = {
  attack: { label: 'Angriff', glyph: '⚔️' },
  transport: { label: 'Transport', glyph: '📦' },
  spy: { label: 'Spionage', glyph: '🛰️' },
  deploy: { label: 'Stationierung', glyph: '🚚' },
  recycle: { label: 'Recycling', glyph: '♻️' },
  colonize: { label: 'Kolonisieren', glyph: '🌱' },
  mine: { label: 'Bergbau', glyph: '⛏️' },
  expedition: { label: 'Expedition', glyph: '🧭' },
};

export const SPECIALIZATION_META: Record<string, DisplayMeta> = {
  combat: { label: 'Kampf', glyph: '⚔️' },
  logistics: { label: 'Logistik', glyph: '📦' },
  spy: { label: 'Spionage', glyph: '🛰️' },
  research: { label: 'Forschung', glyph: '🔬' },
  trade: { label: 'Handel', glyph: '💱' },
};

export const RANK_META: Record<string, DisplayMeta> = {
  cadet: { label: 'Kadett', glyph: '▪' },
  officer: { label: 'Offizier', glyph: '▴' },
  veteran: { label: 'Veteran', glyph: '★' },
  elite: { label: 'Elite', glyph: '✦' },
  legend: { label: 'Legende', glyph: '✸' },
};

/**
 * Gueteklassen F..SSS (Doku 05a). `glyph` haelt die CSS-Klasse fuer die
 * Farbcodierung des Grad-Badges (F-D grau, C-B blau, A-S cyan, SS-SSS magenta/gold).
 */
export const GRADE_META: Record<string, DisplayMeta> = {
  F: { label: 'F', glyph: 'grade-low' },
  E: { label: 'E', glyph: 'grade-low' },
  D: { label: 'D', glyph: 'grade-low' },
  C: { label: 'C', glyph: 'grade-mid' },
  B: { label: 'B', glyph: 'grade-mid' },
  A: { label: 'A', glyph: 'grade-high' },
  S: { label: 'S', glyph: 'grade-high' },
  SS: { label: 'SS', glyph: 'grade-elite' },
  SSS: { label: 'SSS', glyph: 'grade-elite' },
};

/** CSS-Klassenname fuer das Grad-Badge (Farbcodierung). Fallback: blau (mid). */
export function gradeBadgeClass(grade: string | null | undefined): string {
  return GRADE_META[grade ?? 'C']?.glyph ?? 'grade-mid';
}

/** Anzeige-Label einer Gueteklasse (Fallback: Roh-Schluessel oder 'C'). */
export function gradeLabel(grade: string | null | undefined): string {
  return GRADE_META[grade ?? 'C']?.label ?? (grade ?? 'C');
}

export const TRAIT_META: Record<string, DisplayMeta> = {
  aggressive: { label: 'aggressiv', glyph: '🔥' },
  cautious: { label: 'vorsichtig', glyph: '🧊' },
  loyal: { label: 'loyal', glyph: '🤝' },
  ambitious: { label: 'ehrgeizig', glyph: '📈' },
  greedy: { label: 'gierig', glyph: '🪙' },
  honorable: { label: 'ehrenhaft', glyph: '🎗️' },
  charismatic: { label: 'charismatisch', glyph: '✨' },
  hot_tempered: { label: 'aufbrausend', glyph: '💢' },
};

/** Faellt auf einen lesbaren Titel zurueck, wenn kein Label gepflegt ist. */
export function humanize(key: string): string {
  return key
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function metaFor(map: Record<string, DisplayMeta>, key: string): DisplayMeta {
  return map[key] ?? { label: humanize(key), glyph: '◆' };
}

/**
 * Waehlt deterministisch eines der acht echten Commander-Gesichter
 * (``faces/face_01.png`` … ``face_08.png``) anhand der Commander-ID.
 * Formel: Summe der charCodes der ID modulo 8, +1, zweistellig.
 */
export function commanderFace(id: string): string {
  let sum = 0;
  for (let i = 0; i < id.length; i++) {
    sum += id.charCodeAt(i);
  }
  const idx = (sum % 8) + 1;
  return `assets/img/commanders/faces/face_${String(idx).padStart(2, '0')}.png`;
}
