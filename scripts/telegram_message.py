"""Construit le message Telegram du matin (HTML) -> data/telegram.html"""
import json, sys
from html import escape
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "data/dashboard.json").read_text())
A = pd.read_csv(ROOT / "data/assets_summary.csv").set_index("ticker")
monday = "--monday" in sys.argv


def pct(v):
    return f"{v * 100:+.1f} %".replace(".", ",")


asof = pd.Timestamp(D["as_of"]).strftime("%d/%m")
L = [f"<b>AI Bubble Tracker · clôture du {asof}</b>", ""]
moves = [("Nasdaq-100", "^NDX"), ("Nvidia", "NVDA"), ("Oracle", "ORCL"), ("CoreWeave", "CRWV"), ("Schneider", "SU.PA")]
L.append("📈 " + " · ".join(f"{n} {pct(A.loc[t, 'chg_1d'])}" for n, t in moves if t in A.index))
L.append(f"VIX {A.loc['^VIX', 'last']:.1f} · taux US 10 ans {A.loc['^TNX', 'last']:.2f} %".replace(".", ","))
L.append("")
trig = [a for a in D["alerts"] if a["triggered"]]
if trig:
    L.append(f"🚨 <b>{len(trig)} règle(s) déclenchée(s)</b>")
    L += [f"• {escape(a['indicator'])} : {a['current']:g} → {escape(a['action'])}" for a in trig]
else:
    L.append(f"✅ Aucune règle déclenchée ({len(D['alerts'])} suivies)")
L.append("")
live_days = (pd.Timestamp(D["as_of"]) - pd.Timestamp(D["start"])).days
if live_days >= 7:
    L.append("<b>Stratégies (suivi réel depuis le " + pd.Timestamp(D["start"]).strftime("%d/%m") + ")</b>")
    rows = D["strategies"]
else:
    L.append("<b>Stratégies : rétro-test 3 mois</b> (le suivi réel démarré le "
             + pd.Timestamp(D["start"]).strftime("%d/%m") + " n'a pas encore une semaine)")
    rows = D["backtest"]
for s in rows:
    if s["kind"] == "strategy":
        L.append(f"• {escape(s['name'])} : {pct(s['pnl_pct'])} (pire baisse {pct(s['max_drawdown'])})")
today = pd.Timestamp.now(tz="Europe/Paris").strftime("%Y-%m-%d")
nxt = [e for e in D["events"] if e["date"] >= today][:2]
if nxt:
    L.append("")
    L.append("🗓 " + " · ".join(f"{pd.Timestamp(e['date']).strftime('%d/%m')} {escape(e['label'])}" for e in nxt))
if monday:
    L += ["", "📰 La newsletter de la semaine est dans le tableau de bord (onglet Newsletter)."]
out = "\n".join(L)
(ROOT / "data/telegram.html").write_text(out)
print(out)
