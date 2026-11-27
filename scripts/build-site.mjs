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
//   CAREERPILOT_DEMO_RESPONSES
//                         path to answers recorded by scripts/record_demo_api.py.
//                         When set, the build is the static GitHub Pages demo.
//                         The pages answer backend calls from the recordings,
//                         and the interview room link opens a page explaining
//                         that the room needs the full deploy.

import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const project = join(root, 'Project');
const out = resolve(root, process.argv[2] || 'site');

export function hostedSettings(env) {
  const isStatic = Boolean((env.CAREERPILOT_DEMO_RESPONSES || '').trim());
  const settings = {
    apiUrl: (env.CAREERPILOT_API_URL || '').trim() || (isStatic ? 'demo-api' : '/api'),
  };
  const meetUrl = (env.CAREERPILOT_MEET_URL || '').trim() || (isStatic ? '.' : '');
  if (meetUrl) settings.meetUrl = meetUrl;
  return settings;
}

const ROOM_NOTICE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CareerPilot interview room</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0b1020; color: #e8ecff; margin: 0; padding: 48px 16px; }
    main { max-width: 560px; margin: 0 auto; line-height: 1.6; }
    a { color: #8fb4ff; }
  </style>
</head>
<body>
  <main>
    <h1>Mock interview room</h1>
    <p>This is the static demo of CareerPilot, so the live interview room is not part of it.
    The room needs LiveKit and runs on the full Vercel deploy of the project.</p>
    <p><a href="../../dashboard.html">Back to the dashboard</a></p>
  </main>
</body>
</html>
`;

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
let settingsJs = prelude + readFileSync(join(project, 'settings.js'), 'utf8');

const demoResponses = (process.env.CAREERPILOT_DEMO_RESPONSES || '').trim();
if (demoResponses) {
  const recorded = JSON.parse(readFileSync(resolve(demoResponses), 'utf8'));
  settingsJs +=
    '\n// Recorded mock backend answers for the static demo.\n' +
    'window.CAREERPILOT_DEMO_RESPONSES = ' + JSON.stringify(recorded) + ';\n' +
    readFileSync(join(root, 'scripts', 'static-demo.js'), 'utf8');
  const room = join(out, 'rooms', 'test-room');
  mkdirSync(room, { recursive: true });
  writeFileSync(join(room, 'index.html'), ROOM_NOTICE);
}
writeFileSync(join(out, 'settings.js'), settingsJs);
console.log(`Built ${out} with`, hostedSettings(process.env));
