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
  nanite_factory: {
    label: 'Nanitenfabrik', glyph: '🧬', blurb: '−25 % Gebäude- / −5 % Schiff-Bauzeit je Stufe.',
    desc: 'Selbstreplizierende Nanit-Schwärme übernehmen den Bau: jede Stufe senkt die Bauzeit ALLER Gebäude um 25 % und die Bauzeit von Schiffen um 5 % (multiplikativ, stapelt sich). Erfordert eine Roboterfabrik der Stufe 12 — die Krönung der Bau-Infrastruktur im Endgame.',
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
    label: 'Kommando-Akademie', glyph: '🎖️', blurb: '+1 Ausbildungsplatz je Stufe.',
    desc: 'Hier werden aus Rekruten Commander geformt — Menschen, die deine Flotten führen und ihre Moral tragen. Ohne Akademie (mindestens Stufe 1) lässt sich kein Commander ausbilden. Jede weitere Stufe öffnet einen zusätzlichen Ausbildungsplatz, sodass du mehrere Commander gleichzeitig trainieren kannst — Stufe 3 = 3 parallele Ausbildungen. Das Fundament der Doktrin „Befehlige nicht nur Flotten, führe Menschen."',
  },
  command_center: {
    label: 'Kommandozentrale', glyph: '📡', blurb: '+1 Span of Control je Stufe.',
    desc: 'Das Nervenzentrum deines Imperiums. Ohne Kommandozentrale kannst du genau 1 Commander gleichzeitig im Feld führen. Jede Stufe hebt deine Befehlsreichweite (Span of Control) um +1 — es gibt kein Maximum, nur die Baukosten setzen die Grenze. Zählt wird die höchste Stufe über alle deine Planeten. Wer mehr Geschwader losschickt, als die Span erlaubt, kassiert pro überzähligem Geschwader −8 % Kampfkraft (Koordinationsstrafe). Hinzu kommt noch die Kommando-Doktrin (+1 Span je Forschungsstufe).',
  },
  // -- Mond-Gebäude (nur auf Monden baubar) --
  moon_base: {
    label: 'Mondbasis', glyph: '🌑', blurb: 'Fundament aller Mondbauten.',
    desc: 'Die erste Infrastruktur auf einem Mond: Druckkuppeln, Landeplattform, Energie. Ohne Mondbasis lässt sich auf dem Mond nichts weiter errichten — sie schaltet Sensorphalanx, Orbitalbatterie, Schildkuppel und Labor frei.',
  },
  sensorphalanx: {
    label: 'Sensorphalanx', glyph: '📡', blurb: 'Scannt feindliche Flottenbewegungen.',
    desc: 'Eine gewaltige Sensorkuppel auf dem Mond. Scannt Koordinaten in Reichweite und enthüllt alle Flottenbewegungen zu und von ihnen — die ETA, auf die ein Abfang-Jäger seinen Angriff timt. Jeder Scan kostet Deuterium.',
  },
  orbital_battery: {
    label: 'Orbitalbatterie', glyph: '🔫', blurb: 'Mond-Verteidigung gegen Angreifer.',
    desc: 'Schwere Geschütztürme auf der Mondoberfläche, die in den Orbit feuern. Verteidigen den Mond — und über ihn auch den zugehörigen Planeten — gegen anfliegende Flotten. Gravitationsforschung verstärkt sie.',
  },
  shield_dome_moon: {
    label: 'Mond-Schildkuppel', glyph: '🛡️', blurb: 'Energieschirm über dem Mond.',
    desc: 'Ein planetarer Schildgenerator in klein: spannt einen Energieschirm über den Mond und absorbiert einen Teil jedes Angriffs. Macht den Mond zur harten Nuss.',
  },
  gravity_lab: {
    label: 'Gravitationslabor', glyph: '🪐', blurb: 'Schaltet Sprungtor & Graviton-Tech.',
    desc: 'Forschungskomplex für künstliche Schwerkraft. Voraussetzung für das Sprungtor und Türöffner der Gravitationsforschung — die Königsdisziplin der Mond-Technik.',
  },
  jump_gate: {
    label: 'Sprungtor', glyph: '🌀', blurb: 'Sofort-Sprung zwischen eigenen Monden.',
    desc: 'Ein massives Hyperraum-Portal. Versetzt Flotten ohne Flugzeit zwischen zwei deiner Monde — strategische Logistik in Sekunden statt Stunden. Teuerstes Mondbauwerk, mit Abklingzeit zwischen den Sprüngen.',
  },
  antimatter_collector: {
    label: 'Antimaterie-Kollektor', glyph: '⚛️', blurb: 'Antimaterie — nur auf heißen Slots (Pos 1–2).',
    desc: 'Erntet Antimaterie aus der Sternenstrahlung — baubar nur auf den heißen, sonnennahen Slots eines Systems (Position 1 voller Ertrag, Position 2 halber). Sehr energiehungrig (braucht ein starkes Solarkraftwerk, ab Stufe 12). Der Ertrag fließt kontoweit auf deine Antimaterie-Reserve (kein Lagerlimit) und treibt die Antimaterie-Schmiede. Bei Energiedefizit drosselt sich die Förderung selbst.',
  },
  dark_matter_condenser: {
    label: 'Dunkle-Materie-Kondensator', glyph: '🌑', blurb: 'Dunkle Materie — nur auf kalten Slots (Pos 14–15).',
    desc: 'Kondensiert Dunkle Materie in der eisigen Außenzone — baubar nur auf den kalten, sternfernen Slots eines Systems (Position 15 voller Ertrag, Position 14 halber). Sehr energiehungrig (braucht einen starken Fusionsreaktor, ab Stufe 8). Der Ertrag fließt kontoweit auf deine Dunkle-Materie-Reserve (kein Lagerlimit) und treibt Forschungs-Nexus & Materie-Dekompressor.',
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
  hyperspace_interdiction: {
    label: 'Hyperraum-Interdiktion', glyph: '🧲', blurb: 'Größere Abfang-Reichweite & Fang-Chance.',
    desc: 'Künstlich aufgespannte Massefelder reißen durchreisende Flotten aus dem Hyperraum. Erweitert die Reichweite deiner Abfang-Patrouillen (+1 System je Stufe bis Stufe 5) und erhöht ihre Fang-Chance um +0,5 % je Stufe (bis Stufe 10 = +5 %). Die letzten Prozent bis zum 95-%-Cap sind ausschließlich über diese Forschung erreichbar — reine Abfangjäger-Masse deckelt bei 90 %.',
  },
  ion_disruptors: {
    label: 'Ionen-Disruptoren', glyph: '🌀', blurb: 'Stärkere Ionenwaffen & Verteidigungs-Lähmung.',
    desc: 'Verfeinerte Ionen-Emitter bündeln den Ladungsstoß. Jede Stufe verstärkt Schild-Strip und Antriebsschaden deiner Ionenwaffen — und legt feindliche Verteidigung schneller und vollständiger lahm. Der Türöffner-Effekt wird zur echten Waffe.',
  },
  boarding_doctrine: {
    label: 'Enter-Doktrin', glyph: '🪝', blurb: '+Kaper-Kapazität je Enterschiff.',
    desc: 'Drillkommandos, Enterhaken-Logistik und Prisenrecht. Jede Stufe lässt deine Enterschiffe ein gestrandetes Feindschiff mehr kapern — aus „zerstören" wird „erbeuten".',
  },
  leadership_doctrine: {
    label: 'Führungsdoktrin', glyph: '🎖️', blurb: 'Weniger Unmut / seltener Meuterei.',
    desc: 'Klare Befehlsketten, faire Rotation, gelebte Werte. Jede Stufe senkt den Unmut-Aufbau deiner Kommandeure — sie stellen seltener Forderungen und laufen seltener über.',
  },
  tactical_academy: {
    label: 'Taktische Akademie', glyph: '📚', blurb: '+XP-Gewinn der Kommandeure.',
    desc: 'Simulatoren, Manöverkritik, Kriegsspiele. Jede Stufe steigert den Erfahrungsgewinn deiner Kommandeure aus jedem Gefecht — schnellere Aufstiege, mehr Skillpunkte.',
  },
  mining_efficiency: {
    label: 'Bergbau-Effizienz', glyph: '⛏️', blurb: '+Minen-Förderung je Stufe.',
    desc: 'Bessere Bohrköpfe, Förderbänder und Aufbereitung. Jede Stufe erhöht den Ertrag deiner Metall-, Kristall- und Deuteriumförderung — der stille Wachstumsmotor.',
  },
  storage_tech: {
    label: 'Speichertechnik', glyph: '🏬', blurb: '+Lagerkapazität je Stufe.',
    desc: 'Verdichtete Lager, Druckspeicher, bessere Logistik. Jede Stufe erhöht die Kapazität deiner Lager — mehr Puffer für teure Großbauten und gegen überlaufende Minen.',
  },
  astrophysics: {
    label: 'Astrophysik', glyph: '🔭', blurb: '+1 Kolonie je Stufe.',
    desc: 'Sternkartierung, Gravitationsanalyse, Habitabilitäts-Modelle. Schon ohne Astrophysik darfst du 3 Kolonien gründen; jede Stufe hebt dieses Limit um +1 (zusätzlich zu deinem Heimatplaneten). Stufe 1 schaltet außerdem Expeditionen in die galaktischen Weiten frei, und jede weitere Stufe verlängert die maximale Verweildauer einer Expedition um +1 Std (bis 24 Std). Die Grundlage echter Expansion.',
  },
  expedition_tech: {
    label: 'Expeditionstechnik', glyph: '🧭', blurb: '+Expeditions-Ertrag je Stufe.',
    desc: 'Tiefenscanner, Bergungsdrohnen, Anomalie-Analyse. Jede Stufe steigert die Ausbeute deiner Expeditionen in die Leere zwischen den Sternen.',
  },
  jump_gate_tech: {
    label: 'Sprungtor-Kalibrierung', glyph: '🌀', blurb: '−Abklingzeit & −Sprungkosten.',
    desc: 'Feinabstimmung der Hyperraum-Resonatoren. Jede Stufe senkt Abklingzeit und Deuterium-Kosten je Sprung — schnellere Mond-zu-Mond-Logistik.',
  },
  phalanx_tech: {
    label: 'Phalanx-Sensorik', glyph: '📡', blurb: '+Scan-Reichweite & −Scankosten.',
    desc: 'Empfindlichere Sensoren, sparsamere Scans. Jede Stufe erweitert die Reichweite der Sensorphalanx um ein System und senkt die Scankosten.',
  },
  gravitics: {
    label: 'Gravitationsforschung', glyph: '🪐', blurb: '+Mond-Chance & +Orbitalgeschütze.',
    desc: 'Beherrschung von Gravitationsfeldern. Jede Stufe hebt die Obergrenze der Mond-Entstehungschance und verstärkt deine Orbitalbatterien.',
  },
  convoy_tactics: {
    label: 'Konvoi-Taktik', glyph: '🛡️', blurb: '−NPC-Piraten-Risiko auf Handelsrouten.',
    desc: 'Geleitformationen, Ausweichkurse, Funkdisziplin. Jede Stufe senkt das Risiko, dass deine Handelsflotten von NPC-Piraten überfallen werden. Hilft NICHT gegen Spieler-Abfangen (das ist getimter Flotten-Fang und eine andere Mechanik).',
  },
  research_network: {
    label: 'Forschungsnetzwerk', glyph: '🌐', blurb: 'Koppelt Labore mehrerer Planeten.',
    desc: 'Ein intergalaktisches Datennetz verbindet die Forschungslabore deiner Kolonien zu einem Verbund. Statt nur am stärksten Labor zu rechnen, summieren sich die Labore deiner besten Planeten — jede Stufe hängt einen weiteren Planeten ins Netz. Je breiter dein Imperium, desto schneller forschst du.',
  },
  weapons_mastery: {
    label: 'Waffen-Meisterschaft', glyph: '🎯', blurb: '+1 % Angriff/Stufe · wiederholbar.',
    desc: 'Endlose Verfeinerung deiner Waffensysteme. Jede Stufe gibt +1 % Angriff — die Kosten steigen linear, der Effekt addiert sich. Diese Forschung wird nie „fertig": ein Dauerziel fürs ewige Universum, bei dem frühe Stufen am meisten pro Forschungspunkt bringen.',
  },
  shield_mastery: {
    label: 'Schild-Meisterschaft', glyph: '🔰', blurb: '+1 % Schild/Stufe · wiederholbar.',
    desc: 'Stetige Optimierung der Schildgeneratoren. +1 % Schildkraft je Stufe, linear-additiv und unbegrenzt wiederholbar — ein ewiger Forschungs-Sink, der nie an eine Decke stößt.',
  },
  armor_mastery: {
    label: 'Panzerungs-Meisterschaft', glyph: '🛠️', blurb: '+1 % Hülle/Stufe · wiederholbar.',
    desc: 'Immer dichtere Verbundpanzerung. +1 % Hüllenintegrität je Stufe, linear-additiv und unbegrenzt — Endgame-Forschung, die mit deinem Imperium ewig mitwächst.',
  },
  extraction_tech: {
    label: 'Fördertechnik', glyph: '⛏️', blurb: '+1 % Minen-Förderung/Stufe.',
    desc: 'Bessere Bohrköpfe, effizientere Schmelzöfen, optimierte Förderbänder. Jede Stufe steigert die Förderung aller Minen (Metall, Kristall, Deuterium) um 1 % — ergänzt die Bergbau-Effizienz und zahlt sich über das ganze Imperium aus.',
  },
  extraction_mastery: {
    label: 'Förder-Meisterschaft', glyph: '⚒️', blurb: '+0,5 % Förderung/Stufe · wiederholbar.',
    desc: 'Die endlose Verfeinerung der Rohstoffgewinnung. +0,5 % Minen-Förderung je Stufe, linear-additiv und unbegrenzt — der ewige Wirtschafts-Motor fürs persistente Universum.',
  },
  terraforming: {
    label: 'Terraforming', glyph: '🌍', blurb: '+5 Bauplätze/Stufe auf allen Planeten.',
    desc: 'Atmosphären-Prozessoren, Krustenstabilisatoren, künstliche Magnetfelder. Jede Stufe schafft +5 Bauplätze auf JEDEM deiner Planeten — mehr Platz für höhere Gebäudestufen. Ein gewaltiger, ewig skalierender Bau-Sink für angehäuften Reichtum.',
  },
  flagship_command: {
    label: 'Flaggschiff-Doktrin', glyph: '🚩', blurb: '+1 erlaubtes Flaggschiff/Stufe.',
    desc: 'Befehlsstrukturen, um mehr als ein Flaggschiff zu führen. Jede Stufe erlaubt dir ein weiteres Flaggschiff (Standard: 1). Mehr Flaggschiffe = mehr getrennte, Aura-verstärkte Flotten (Auren stapeln nicht).',
  },
  corsair_command: {
    label: 'Korsaren-Verband', glyph: '🏴‍☠️', blurb: '+1 erlaubter Korsar/Stufe.',
    desc: 'Eine Piraten-Flottille statt eines einzelnen Räubers. Jede Stufe erlaubt dir einen weiteren Korsar (Standard: 1) — für alle, die Hit-and-run zum Beruf machen.',
  },
  leviathan_command: {
    label: 'Großhandels-Lizenz', glyph: '🐋', blurb: '+1 erlaubter Handels-Leviathan/Stufe.',
    desc: 'Behördliche Freigabe für eine ganze Leviathan-Flotte. Jede Stufe erlaubt dir einen weiteren Handels-Leviathan (Standard: 1) — Großhandel im industriellen Maßstab.',
  },
  harvest_command: {
    label: 'Schürf-Kommando', glyph: '⛏️', blurb: '+1 erlaubter Ernte-Titan/Stufe.',
    desc: 'Koordination einer ganzen Ernte-Flotte. Jede Stufe erlaubt dir einen weiteren Ernte-Titan (Standard: 1) — industrieller Bergbau auf Imperiumsmaßstab.',
  },
  fleet_logistics: {
    label: 'Logistik-Netz', glyph: '📦', blurb: '+1 gleichzeitige Farm-Routine/Stufe · wiederholbar.',
    desc: 'Ein automatisiertes Versorgungsnetz koordiniert deine wiederkehrenden Farm-Routinen. Jede Stufe erlaubt dir +1 gleichzeitig laufende Farm-Routine — wiederholbar und ohne feste Obergrenze, der Schlüssel zu einem dicht getakteten Ernte-Imperium.',
  },
  route_planning: {
    label: 'Routen-Planung', glyph: '🗺️', blurb: '+1 Feld je Farm-Route/Stufe · wiederholbar.',
    desc: 'Vorberechnete Flugkorridore und Ziel-Priorisierung verlängern den Aktionsradius jeder Farm-Route. Jede Stufe hängt +1 Feld an jede Route an — wiederholbar, damit deine Routinen mit jedem Ausbau mehr Ziele in einem Durchlauf abklappern.',
  },
};

/**
 * Effekt-Metadaten je Forschung fuer die Detail-Ansicht.
 * `summary` = was die Tech bewirkt (eine Zeile). `levelEffect` = numerischer
 * Pro-Stufe-Effekt, aus dem das Popup "aktuell -> naechste Stufe" berechnet
 * (Wert bei Stufe n = base + perLevel*n). `branch` = Zweig fuer die Einordnung.
 */
export interface TechLevelEffect {
  label: string;
  perLevel: number;
  unit: string;
  base?: number;
}
export interface TechEffectMeta {
  branch: string;
  summary: string;
  levelEffect?: TechLevelEffect;
}

export const TECH_EFFECTS: Record<string, TechEffectMeta> = {
  energy_tech: {
    branch: 'Grundlagen',
    summary:
      'Steigert die Energieausbeute von Solarkraftwerk & Fusionsreaktor: +1 %-Punkt auf den Ausbeute-Faktor je Stufe (multiplikativ pro Kraftwerksstufe — wirkt umso stärker, je höher das Kraftwerk ausgebaut ist). Zugleich Schlüssel-Tech: Voraussetzung für Laser, Fusion, Schilde und höhere Antriebe.',
  },
  combustion_drive: {
    branch: 'Antrieb',
    summary:
      '+10 % Reisetempo je Stufe für Schiffe mit Verbrennungstriebwerk (Jäger, Transporter, Recycler, Sonden). Antriebsstufe = Bau-Voraussetzung dieser Schiffe.',
    levelEffect: { label: 'Reisetempo', perLevel: 10, unit: '%' },
  },
  impulse_drive: {
    branch: 'Antrieb',
    summary:
      '+20 % Reisetempo je Stufe für Schiffe mit Impulstriebwerk (mittlere Klasse: Kreuzer, Kolonie- und Spezialschiffe). Antriebsstufe = Bau-Voraussetzung.',
    levelEffect: { label: 'Reisetempo', perLevel: 20, unit: '%' },
  },
  hyperspace_drive: {
    branch: 'Antrieb',
    summary:
      '+30 % Reisetempo je Stufe für Großkampfschiffe (Schlachtschiff, Zerstörer, Träger, Todesstern). Antriebsstufe = Bau-Voraussetzung.',
    levelEffect: { label: 'Reisetempo', perLevel: 30, unit: '%' },
  },
  spy_tech: {
    branch: 'Aufklärung',
    summary: 'Tiefere Spionageberichte je Stufe; schaltet Spionagesonde & Tief-Aufklärer frei. +0,5 % Hinterhalt-Entdeckung je Stufe (die letzten 5 % über dem 90-%-Sensor-Cap, bis Stufe 10).',
  },
  computer_tech: {
    branch: 'Kommando',
    summary: '+1 gleichzeitig führbare Flotte je Stufe.',
    levelEffect: { label: 'Flottenslots', perLevel: 1, unit: '', base: 1 },
  },
  weapons_tech: {
    branch: 'Waffen',
    summary: '+10 % Angriff aller Schiffe & Verteidigung je Stufe.',
    levelEffect: { label: 'Angriff', perLevel: 10, unit: '%' },
  },
  shield_tech: {
    branch: 'Schild',
    summary: '+10 % Schildkraft aller Einheiten je Stufe.',
    levelEffect: { label: 'Schild', perLevel: 10, unit: '%' },
  },
  armor_tech: {
    branch: 'Panzerung',
    summary: '+10 % Hüllenintegrität aller Einheiten je Stufe.',
    levelEffect: { label: 'Hülle', perLevel: 10, unit: '%' },
  },
  command_doctrine: {
    branch: 'Kommando',
    summary: '+1 Befehlsreichweite (Span of Control) je Stufe — ein Geschwader mehr ohne Koordinationsstrafe (−8 % Kampfkraft je Geschwader über dem Span). Linear, kein Maximum.',
    levelEffect: { label: 'Befehlsreichweite', perLevel: 1, unit: '' },
  },
  logistics_tech: {
    branch: 'Kommando',
    summary: 'Schnellere Moral-Erholung der Crews (+8 %/Stufe Drift) + bessere Evakuierungschance (+3 %/Stufe).',
    levelEffect: { label: 'Evakuierungschance', perLevel: 3, unit: '%' },
  },
  crew_psychology: {
    branch: 'Kommando',
    summary: 'Höhere Moral-Stabilität: hebt das gehaltene Moral-Niveau (+2/Stufe) und dämpft den Neglect-Verfall untätiger Crews (−10 %/Stufe).',
    levelEffect: { label: 'Moral-Niveau', perLevel: 2, unit: '' },
  },
  laser_tech: {
    branch: 'Waffen',
    summary: 'Schaltet frei: Schlachtkreuzer, Stealth-Korvette, Eskort-Fregatte, Abfangjäger sowie leichtes & schweres Lasergeschütz. Grundlage für Ionen- und Plasmatechnik.',
  },
  ion_tech: {
    branch: 'Waffen',
    summary: 'Ionenwaffen: leeren Schilde, lähmen Antriebe und legen Verteidigung lahm. Schaltet Kreuzer, EWAR-Fregatte & Ionengeschütz frei.',
  },
  plasma_tech: {
    branch: 'Waffen',
    summary: 'Stärkste Waffentechnik: Plasmawerfer, Bomber, Zerstörer & Träger.',
  },
  hyperspace_tech: {
    branch: 'Antrieb',
    summary: 'Fundament jedes Großkampfschiffs — Voraussetzung für Hyperraumantrieb, Schlachtkreuzer & Graviton.',
  },
  graviton_tech: {
    branch: 'Endgame',
    summary: 'Königsdisziplin: ermöglicht den Todesstern, eine mobile Festung von Mondgröße.',
  },
  hyperspace_interdiction: {
    branch: 'Abfangen',
    summary: '+1 Abfang-Reichweite je Stufe (bis Stufe 5) und +0,5 % Fang-Chance je Stufe (bis Stufe 10 = +5 %, einziger Weg über den 90-%-Schiffs-Cap).',
    levelEffect: { label: 'Abfang-Radius', perLevel: 1, unit: ' Sys', base: 5 },
  },
  ion_disruptors: {
    branch: 'Waffen',
    summary: '+10 % Ionen-Wirkung je Stufe: stärkerer Schild-Strip, Antriebsschaden und Verteidigungs-Lähmung.',
    levelEffect: { label: 'Ionen-Wirkung', perLevel: 10, unit: '%' },
  },
  boarding_doctrine: {
    branch: 'Waffen',
    summary: '+1 gekapertes Schiff je Enterschiff und Stufe.',
    levelEffect: { label: 'Kaper-Kapazität', perLevel: 1, unit: '/Enterschiff', base: 2 },
  },
  leadership_doctrine: {
    branch: 'Kommando',
    summary: '−10 % Unmut-Aufbau der Kommandeure je Stufe (seltener Forderungen & Überläufe).',
    levelEffect: { label: 'Unmut-Dämpfung', perLevel: 10, unit: '%' },
  },
  tactical_academy: {
    branch: 'Kommando',
    summary: '+10 % XP-Gewinn der Kommandeure je Stufe.',
    levelEffect: { label: 'XP-Gewinn', perLevel: 10, unit: '%' },
  },
  mining_efficiency: {
    branch: 'Wirtschaft',
    summary: '+2 % Metall-/Kristall-/Deuteriumförderung je Stufe.',
    levelEffect: { label: 'Förderung', perLevel: 2, unit: '%' },
  },
  storage_tech: {
    branch: 'Wirtschaft',
    summary: '+5 % Lagerkapazität je Stufe.',
    levelEffect: { label: 'Lagerkapazität', perLevel: 5, unit: '%' },
  },
  astrophysics: {
    branch: 'Expansion',
    summary: 'Erlaubt +1 Kolonie je Stufe.',
    levelEffect: { label: 'Max. Kolonien', perLevel: 1, unit: '', base: 3 },
  },
  expedition_tech: {
    branch: 'Expansion',
    summary: '+10 % Expeditions-Ressourcenertrag je Stufe.',
    levelEffect: { label: 'Expeditions-Ertrag', perLevel: 10, unit: '%' },
  },
  // -- Mond/Logistik-Techs --
  phalanx_tech: {
    branch: 'Aufklärung',
    summary: '+1 Scan-Reichweite (Systeme) und −8 % Scankosten je Stufe (Sensorphalanx).',
    levelEffect: { label: 'Scan-Reichweite', perLevel: 1, unit: ' Sys' },
  },
  jump_gate_tech: {
    branch: 'Mond',
    summary: '−6 % Sprungtor-Abklingzeit und −8 % Sprungkosten je Stufe.',
  },
  gravitics: {
    branch: 'Mond',
    summary: '+2 %-Punkte Mond-Entstehungschance-Obergrenze und stärkere Orbitalbatterien je Stufe.',
  },
  convoy_tactics: {
    branch: 'Wirtschaft',
    summary: '−6 % NPC-Piraten-Überfallrisiko auf Handelsrouten je Stufe (hilft NICHT gegen Spieler-Abfangen).',
  },
  research_network: {
    branch: 'Endgame',
    summary: 'Summiert die Labore deiner besten (Stufe+1) Planeten in die Forschungszeit. Stufe 1 = 2 Labore gekoppelt, Stufe 2 = drei usw. Belohnt breite Expansion.',
  },
  weapons_mastery: {
    branch: 'Endgame',
    summary: 'Wiederholbar, kein Maximum: +1 % Angriff aller Einheiten je Stufe. Lineare Kosten + additiver Effekt → sinkender Grenznutzen, kein Power-Creep.',
    levelEffect: { label: 'Angriff (Meisterschaft)', perLevel: 1, unit: '%' },
  },
  shield_mastery: {
    branch: 'Endgame',
    summary: 'Wiederholbar, kein Maximum: +1 % Schildkraft aller Einheiten je Stufe. Linear-additiv.',
    levelEffect: { label: 'Schild (Meisterschaft)', perLevel: 1, unit: '%' },
  },
  armor_mastery: {
    branch: 'Endgame',
    summary: 'Wiederholbar, kein Maximum: +1 % Hülle aller Einheiten je Stufe. Linear-additiv.',
    levelEffect: { label: 'Hülle (Meisterschaft)', perLevel: 1, unit: '%' },
  },
  extraction_tech: {
    branch: 'Wirtschaft',
    summary: '+1 % Minen-Förderung (Metall/Kristall/Deuterium) je Stufe. Ergänzt die Bergbau-Effizienz.',
    levelEffect: { label: 'Förderung', perLevel: 1, unit: '%' },
  },
  extraction_mastery: {
    branch: 'Endgame',
    summary: 'Wiederholbar, kein Maximum: +0,5 % Minen-Förderung je Stufe. Linear-additiv — ewiger Wirtschafts-Motor.',
    levelEffect: { label: 'Förderung (Meisterschaft)', perLevel: 0.5, unit: '%' },
  },
  terraforming: {
    branch: 'Endgame',
    summary: '+5 Bauplätze auf jedem Planeten je Stufe. Mehr Felder → mehr Gebäudestufen → ewiger Bau-Sink.',
    levelEffect: { label: 'Bauplätze/Planet', perLevel: 5, unit: '' },
  },
  flagship_command: {
    branch: 'Endgame',
    summary: 'Wiederholbar: +1 erlaubtes Flaggschiff je Stufe (Default 1). Kostet je Stufe linear mehr.',
    levelEffect: { label: 'Flaggschiff-Limit', perLevel: 1, unit: '', base: 1 },
  },
  corsair_command: {
    branch: 'Endgame',
    summary: 'Wiederholbar: +1 erlaubter Korsar je Stufe (Default 1).',
    levelEffect: { label: 'Korsar-Limit', perLevel: 1, unit: '', base: 1 },
  },
  leviathan_command: {
    branch: 'Endgame',
    summary: 'Wiederholbar: +1 erlaubter Handels-Leviathan je Stufe (Default 1).',
    levelEffect: { label: 'Leviathan-Limit', perLevel: 1, unit: '', base: 1 },
  },
  harvest_command: {
    branch: 'Endgame',
    summary: 'Wiederholbar: +1 erlaubter Ernte-Titan je Stufe (Default 1).',
    levelEffect: { label: 'Ernte-Titan-Limit', perLevel: 1, unit: '', base: 1 },
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
    label: 'Traeger', glyph: '🛸', blurb: 'Lädt beim Angriff Drohnen aus der Garnison.',
    desc: 'Eine fliegende Drohnen-Basis. Schickst du einen Träger auf Angriff, lädt er automatisch bis zu seiner Kapazität Drohnen aus deiner Garnison ein — sie fliegen als echte Schiffe mit und kämpfen (mit echten Verlusten). Ohne gebaute Drohnen ist der Träger nur ein mittelschweres Schiff: erst Drohnen + Träger zusammen entfalten den Schwarm.',
  },
  drone: {
    label: 'Drohne', glyph: '🛩️', blurb: 'Schwarm-Einheit; Träger laden sie automatisch.',
    desc: 'Unbemannt, spottbillig, in Massen verfügbar. Allein bedeutungslos, im Schwarm eine Lawine. Baue Drohnen in der Garnison — Träger laden sie beim Angriff automatisch ein und führen sie ins Gefecht. Du kannst sie aber auch wie jedes andere Schiff von Hand einer Flotte zuteilen.',
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
  warp_stabilizer: {
    label: 'Warp-Stabilisator', glyph: '🌀', blurb: 'Konter zum Interdiktor: hält den Warp offen.',
    desc: 'Das Gegenstück zum Interdiktor. Jeder Warp-Stabilisator in deiner Flotte stabilisiert den Sprungkanal: Er senkt die Chance, aus dem Warp gerissen (abgefangen) zu werden, und neutralisiert im Gefecht je ein gegnerisches Interdiktor-Feld — pro Stabilisator ein Interdiktor. Mit genug Stabilisatoren bleibt der Fleetsave deine Versicherung, egal wie viele Fang-Schiffe der Feind auffährt. Selbst kein Schläger; sein Wert ist die garantierte Flucht.',
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
    label: 'Tief-Aufklaerer', glyph: '🔭', blurb: 'Sensor-Schiff: entlarvt Tarnkappen-Hinterhalte.',
    desc: 'Ein hochauflösendes Sensor-Array spürt getarnte Angreifer auf. Jeder Tief-Aufklärer in deiner Kampfflotte erhöht die Chance, einen Tarnkappen-Hinterhalt zu entdecken (+1 % je Schiff, bis 90 %); die letzten 5 % bis zum 95-%-Cap gibt es nur über Spionagetech. Wird der Hinterhalt entdeckt, verliert der Gegner seine Überraschungsrunde — den Erstschlag. Gegen Tarnkappen-Korvetten unverzichtbar; ganz sicher ist man aber nie. (Planeten ausspionieren ist Sache der Spionagesonde.)',
  },
  expedition_ship: {
    label: 'Expeditions-Schiff', glyph: '🧭', blurb: 'Erkundung und Langstrecke.',
    desc: 'Gebaut für die Reise ins Ungewisse: lange Reichweite, robuste Systeme, Platz für Funde. Schickt es in die Leere zwischen den Sternen — was es zurückbringt, ist nie vorhersehbar.',
  },
  // -- Endgame-Capstone-Schiffe (eines je Spielstil; Default-Besitz 1, +1 je Kommando-Forschung) --
  flagship: {
    label: 'Flaggschiff', glyph: '🚩', blurb: 'Kampf-Aura: verstärkt die ganze Flotte.',
    desc: 'Das Kronjuwel des ehrenvollen Kämpfers. Solange ein Flaggschiff in der Flotte fliegt, kämpft die GESAMTE Begleitflotte stärker (Aura: +Angriff & +Schild) — die Bühne für deine Kommandeure. Auren stapeln NICHT: zwei Flaggschiffe geben keine doppelte Aura, sondern erlauben zwei getrennte verstärkte Flotten. Antimaterie-gegatet; standardmäßig nur eins erlaubt, die Flaggschiff-Doktrin hebt das Limit.',
  },
  corsair: {
    label: 'Korsar', glyph: '🏴‍☠️', blurb: 'Tarnung, Entern, mehr Beute.',
    desc: 'Das Schiff des Piraten: getarnt (umgeht Phalanx & Abfangen), mit Enterhaken (kapert gegnerische Schiffe, statt sie nur zu zerstören) und vergrößertem Beuteraum. Eine Glaskanone für den Hinterhalt — stark im Überfall, verwundbar im offenen Schlagabtausch. Anders als die anderen Capstones in Stückzahl baubar (Piraten verlieren Schiffe), gebremst durch hohe Antimaterie-Kosten.',
  },
  trade_leviathan: {
    label: 'Handels-Leviathan', glyph: '🐋', blurb: 'Gigantischer Frachter + Konvoi-Schutz.',
    desc: 'Der Stolz des Händlers: ein kolossaler Frachter mit gewaltigem Laderaum. Fliegt er in einer Handelsflotte mit, legt er eine Konvoi-Schutz-Aura über die Route und halbiert das Überfallrisiko. Kein Markt-Eingriff — reine Logistik & Sicherheit. Dunkle-Materie-gegatet.',
  },
  harvest_titan: {
    label: 'Ernte-Titan', glyph: '⛏️', blurb: 'Mobile Mega-Raffinerie (Abbau ×8).',
    desc: 'Der Traum des Miners: ein gewaltiges Erntschiff, das an Asteroidenfeldern ein Vielfaches eines normalen Bergbauschiffs fördert (zählt wie viele Bergbauschiffe zugleich) und riesige Mengen heimbringt. Dunkle-Materie-gegatet; verwandelt Schürfen in Industrie.',
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
  orbital_gun: {
    label: 'Orbitalgeschütz', glyph: '🔫', blurb: 'Mond-Verteidigung (aus der Orbitalbatterie).',
    desc: 'Das Feuer der Orbitalbatterien deines Mondes — kein eigenständig baubares Geschütz, sondern die Verteidigungskraft, die das Gebäude „Orbitalbatterie" bereitstellt und mit der der Mond (und der zugehörige Planet) anfliegende Flotten beschießt.',
  },
};

/**
 * Waffen-Typen der Rollen-Kampf-Profile (balance.json `combat_roster`).
 * `vs` haelt den statischen Effektivitaets-Hinweis (Design-fix, siehe `damage_matrix`).
 */
export const WEAPON_META: Record<string, { label: string; glyph: string; vs: string }> = {
  kinetic: { label: 'Kinetik', glyph: '💥', vs: 'stark vs. Hülle, schwach vs. Schild' },
  energy: { label: 'Energie', glyph: '⚡', vs: 'stark vs. Schild' },
  ion: { label: 'Ionen', glyph: '🌀', vs: 'lähmt Antrieb + legt Verteidigung lahm, 0 vs. Hülle' },
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
  trade: { label: 'Handel', glyph: '💱' },
  intercept: { label: 'Abfangen', glyph: '📡' },
  escort: { label: 'Eskorte', glyph: '🛡️' },
};

export const SPECIALIZATION_META: Record<string, DisplayMeta> = {
  combat: { label: 'Kampf', glyph: '⚔️' },
  logistics: { label: 'Logistik', glyph: '📦' },
  spy: { label: 'Spionage', glyph: '🛰️' },
  research: { label: 'Forschung', glyph: '🔬' },
  trade: { label: 'Handel', glyph: '💱' },
  admin: { label: 'Verwaltung', glyph: '🏛️' },
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
