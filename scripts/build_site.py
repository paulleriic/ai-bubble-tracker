"""Construit la version web autonome du tableau de bord -> site/index.html

Reprend dashboard/index.html (la même page que sur Claude) et lui fournit :
- les données de data/dash/*.json, intégrées dans la page ;
- une petite couche `dash` compatible (data, onData, draw, params, setParams, setLink, colors) ;
- les couleurs et espacements du thème, en clair et en sombre.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
page = (ROOT / "dashboard/index.html").read_text()
page = page.replace('<meta name="dash-one-writer">', "")
data = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data/dash").glob("*.json"))}
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>AI Bubble Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
:root {
  --font-anthropic-sans: "Inter Tight", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-anthropic-serif: "Source Serif 4", Georgia, serif;
  --color-bg: #fbfbf9; --color-fg: #1d1f24; --color-fg-muted: #626875; --color-panel: #ffffff;
  --color-border-line: #e3e4e8; --color-ok: #1f7a4d; --color-warn: #a35d00; --color-bad: #c0352b;
  --cds-chart-grid: #ececef; --cds-chart-axis: #b9bcc4; --cds-chart-reference: #8d919b; --cds-chart-muted: #9aa0ab;
  --cds-surface-popover: #ffffff; --cds-border: #dadce1; --cds-shadow-popover: 0 4px 16px rgba(20, 24, 33, .12);
  --cds-text-secondary: #626875;
  --cds-radius: 8px; --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 16px; --cds-pad-xl: 24px;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 16px; --cds-gap-lg: 24px; --cds-gap-xl: 32px;
  --cds-font-size-caption: 12.5px; --cds-font-size-body: 15px; --cds-font-size-heading: 16px; --cds-font-size-title: 28px;
  --cds-font-weight-medium: 500; --cds-dur-slow: .3s; --cds-ease-out: cubic-bezier(.2, .7, .2, 1);
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #15171b; --color-fg: #e9eaee; --color-fg-muted: #9a9fab; --color-panel: #1d2026;
    --color-border-line: #2e323a; --color-ok: #4cc38a; --color-warn: #e0a243; --color-bad: #f0776c;
    --cds-chart-grid: #272a31; --cds-chart-axis: #4a4f5a; --cds-chart-reference: #7d8390; --cds-chart-muted: #6f7582;
    --cds-surface-popover: #23262d; --cds-border: #353943; --cds-shadow-popover: 0 4px 16px rgba(0, 0, 0, .45);
    --cds-text-secondary: #9a9fab; color-scheme: dark;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: var(--cds-font-size-body); }
#dash-root { max-width: 1200px; margin-inline: auto; padding-block: max(20px, env(safe-area-inset-top, 0px)) 40px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.dash-skeleton { min-height: 1em; border-radius: 6px; background: var(--cds-chart-grid); }
.ab-foot { margin-top: 32px; color: var(--color-fg-muted); font-size: 12px; }
</style>
<script id="ab-data" type="application/json">__DATA__</script>
<script>
window.dash = (() => {
  const DATA = JSON.parse(document.getElementById('ab-data').textContent);
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const colors = dark
    ? ['#6aa8ff', '#f2a65a', '#4cc38a', '#c792ea', '#5fd0e0', '#f07fa8', '#b5d36b', '#e0c25c']
    : ['#2f6bd8', '#d26a1c', '#1f8a5b', '#8a4fd1', '#0e8ea0', '#c63f78', '#6f8f1f', '#a88310'];
  const draws = {}, subs = [];
  let params = {};
  const visible = (el) => !el.closest('[hidden]');
  const data = (id) => DATA[id]
    ? { status: 'ok', data: DATA[id], columns: Object.keys(DATA[id][0] || {}), meta: [], refreshing: false }
    : { status: 'missing', data: [], columns: [], meta: [] };
  const runDraw = (n) => document.querySelectorAll('[data-draw="' + n + '"]').forEach((el) => {
    if (!visible(el)) return;
    try { draws[n](el); } catch (e) { console.error(n, e); }
  });
  const runAll = () => { subs.forEach((f) => { try { f(); } catch (e) { console.error(e); } }); Object.keys(draws).forEach(runDraw); };
  return {
    data, colors,
    onData: (f) => { subs.push(f); },
    draw: (n, fn) => { if (fn) draws[n] = typeof fn === 'function' ? fn : fn.update; else runDraw(n); },
    params: () => ({ ...params }),
    setParams: (p) => { params = { ...params, ...p }; Object.keys(params).forEach((k) => params[k] == null && delete params[k]); runAll(); },
    resetParams: () => { params = {}; runAll(); },
    setLink: (n) => { try { history.replaceState(null, '', '#' + n); } catch (e) {} runAll(); },
    refresh: () => {}, calc: () => {}, loader: () => {},
    _runAll: runAll,
  };
})();
</script>
</head>
<body>
<div id="dash-root">
"""

FOOT = """
<p class="ab-foot">Analyse personnelle à partir de portefeuilles fictifs, pas un conseil en investissement. Cours : Yahoo Finance, mis à jour chaque soir de bourse.</p>
</div>
<script>
dash._runAll();
let abW = innerWidth;
addEventListener('resize', () => { if (Math.abs(innerWidth - abW) > 30) { abW = innerWidth; dash._runAll(); } });
</script>
</body>
</html>
"""

out = ROOT / "site"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(HEAD.replace("__DATA__", blob) + page + FOOT)
(out / ".nojekyll").write_text("")
print("site/index.html", round((out / "index.html").stat().st_size / 1024), "Ko")
