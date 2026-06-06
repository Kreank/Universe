// Kopiert shared/balance.json nach src/assets/balance.json (lokaler Dev-Sync).
// Bewusst NICHT Teil von `npm run build`, damit der Docker-Build-Context
// (nur der frontend/-Ordner) eigenstaendig bleibt.
import { copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '../../shared/balance.json');
const dest = resolve(here, '../src/assets/balance.json');

try {
  await copyFile(src, dest);
  console.log(`balance.json synchronisiert: ${src} -> ${dest}`);
} catch (err) {
  console.error('Sync fehlgeschlagen:', err.message);
  process.exit(1);
}
