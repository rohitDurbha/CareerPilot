// Builds the static half of the hosted CareerPilot demo into site/.
//
// Vercel runs this before each deploy. It copies the two HTML pages and
// settings.js, and puts the hosted addresses in front of settings.js so the
// pages call the backend function at /api on the same site. Locally the pages
// keep using Project/settings.js as it is.
//
//   CAREERPILOT_API_URL   where the pages send requests (default /api)
//   CAREERPILOT_MEET_URL  where the dashboard opens the interview room
//                         (left at the local default when unset)

import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const project = join(root, 'Project');
const out = resolve(root, process.argv[2] || 'site');

export function hostedSettings(env) {
  const settings = { apiUrl: (env.CAREERPILOT_API_URL || '').trim() || '/api' };
  const meetUrl = (env.CAREERPILOT_MEET_URL || '').trim();
  if (meetUrl) settings.meetUrl = meetUrl;
  return settings;
}

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
for (const page of ['index.html', 'dashboard.html']) {
  copyFileSync(join(project, page), join(out, page));
}
const prelude =
  '// Added by scripts/build-site.mjs for the hosted site.\n' +
  'window.CAREERPILOT_SETTINGS = Object.assign(' +
  JSON.stringify(hostedSettings(process.env)) +
  ', window.CAREERPILOT_SETTINGS || {});\n';
writeFileSync(join(out, 'settings.js'), prelude + readFileSync(join(project, 'settings.js'), 'utf8'));
console.log(`Built ${out} with`, hostedSettings(process.env));
