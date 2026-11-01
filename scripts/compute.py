"""Calcule les portefeuilles fictifs et le résumé des actifs -> data/*.csv + data/dashboard.json"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
U = json.loads((ROOT / "config/universe.json").read_text())
S = json.loads((ROOT / "config/strategies.json").read_text())
T = json.loads((ROOT / "config/thresholds.json").read_text())
CAP = S["capital_eur"]

px = pd.read_csv(ROOT / "data/prices.csv", parse_dates=["date"], index_col="date").sort_index()
px = px.ffill()  # jours fériés différents selon les places
ccy = {a["ticker"]: a["ccy"] for a in U["assets"]}
fx = px[U["fx"]]  # USD pour 1 EUR

def eur(t):
    s = px[t]
    return s / fx if ccy[t] == "USD" else s

start = px.index[px.index >= pd.Timestamp(U["start_date"])][0]
idx = px.index[px.index >= start]
days = pd.Series((idx - start).days, index=idx)

def basket(weights, amount=CAP, entry=start):
    v = pd.Series(0.0, index=idx)
    for t, w in weights.items():
        p = eur(t).loc[idx]
        v += amount * w * p / p.loc[entry]
    return v

out = pd.DataFrame(index=idx)
meta = []
by_id = {}
for st in S["strategies"]:
    if st["type"] == "basket":
        v = basket(st["weights"])
    elif st["type"] == "pair":
        rl = eur(st["long"]).loc[idx] / eur(st["long"]).loc[start] - 1
        rs = eur(st["short"]).loc[idx] / eur(st["short"]).loc[start] - 1
        fin = days / 365 * (st["long_notional"] * st["financing_long_annual"]
                            + st["short_notional"] * st["financing_short_annual"])
        out[st["id"] + "_long_pnl"] = st["long_notional"] * rl
        out[st["id"] + "_short_pnl"] = -st["short_notional"] * rs
        out[st["id"] + "_financing"] = -fin
        v = CAP + st["long_notional"] * rl - st["short_notional"] * rs - fin
    elif st["type"] == "hedged":
        base = by_id[st["base"]]
        rh = eur(st["hedge"]).loc[idx] / eur(st["hedge"]).loc[start] - 1
        n = CAP * st["hedge_ratio"]
        out[st["id"] + "_hedge_pnl"] = -n * rh
        v = base - n * rh - days / 365 * n * st["financing_short_annual"]
    elif st["type"] == "dca":
        w = next(x for x in S["strategies"] if x["id"] == st["base_weights_from"])["weights"]
        k = len(st["tranches"])
        v = pd.Series(0.0, index=idx)
        invested = pd.Series(0.0, index=idx)
        for d in st["tranches"]:
            after = idx[idx >= pd.Timestamp(d)]
            if len(after) == 0:
                continue  # palier futur : reste en cash
            e = after[0]
            part = basket(w, CAP / k, e).where(idx >= e, 0.0)
            v += part
            invested += pd.Series(np.where(idx >= e, CAP / k, 0.0), index=idx)
        out[st["id"] + "_invested"] = invested
        v = v + (CAP - invested)  # cash non investi
    by_id[st["id"]] = v
    out[st["id"]] = v
    last = v.iloc[-1]
    meta.append({**{k: st[k] for k in ("id", "name", "platform", "thesis")},
                 "value": round(last, 2), "pnl": round(last - CAP, 2),
                 "pnl_pct": round(last / CAP - 1, 4),
                 "max_drawdown": round(float((v / v.cummax() - 1).min()), 4)})
for b in S["benchmarks"]:
    p = eur(b["ticker"]).loc[idx]
    out[b["id"]] = CAP * p / p.loc[start]

out.index.name = "date"
out.round(2).to_csv(ROOT / "data/strategies.csv")

# Résumé des actifs
rows = []
last_d = px.index[-1]
for a in U["assets"]:
    s = px[a["ticker"]].dropna()
    if s.empty:
        continue
    def chg(n):
        return float(s.iloc[-1] / s.iloc[-1 - n] - 1) if len(s) > n else None
    w3 = s[s.index >= last_d - pd.Timedelta(days=91)]
    w52 = s[s.index >= last_d - pd.Timedelta(days=365)]
    rows.append({**a, "last": round(float(s.iloc[-1]), 4),
                 "chg_1d": chg(1), "chg_1w": chg(5), "chg_1m": chg(21),
                 "since_start": float(s.iloc[-1] / s.loc[:start].iloc[-1] - 1),
                 "from_3m_high": float(s.iloc[-1] / w3.max() - 1),
                 "from_52w_high": float(s.iloc[-1] / w52.max() - 1)})
summary = pd.DataFrame(rows)
summary.to_csv(ROOT / "data/assets_summary.csv", index=False, float_format="%.6f")

# Signaux manuels (CDS, Fed) + alertes
sig = pd.read_csv(ROOT / "data/signals.csv", parse_dates=["date"]).sort_values("date")
latest = sig.groupby("indicator").tail(1).set_index("indicator")
alerts = []
for r in T["rules"]:
    if r["indicator"] in latest.index:
        val = float(latest.loc[r["indicator"], "value"])
        hit = val > r["value"] if r["op"] == ">" else val < r["value"]
        alerts.append({**r, "current": val, "triggered": bool(hit)})
pair = next(x for x in S["strategies"] if x["type"] == "pair")
pair_pnl = by_id["pair"].iloc[-1] / CAP - 1
alerts.append({"indicator": "Pair trade (P&L / capital)", "op": "<", "value": pair["stop_loss_pct_capital"],
               "current": round(float(pair_pnl), 4), "triggered": bool(pair_pnl < pair["stop_loss_pct_capital"]),
               "action": "Stop-loss : couper le pair trade"})

(ROOT / "data/dashboard.json").write_text(json.dumps({
    "as_of": str(last_d.date()), "start": str(start.date()), "capital_eur": CAP,
    "strategies": meta, "alerts": alerts, "events": T["events"]}, ensure_ascii=False, indent=1))
print("as_of", last_d.date(), {m["id"]: m["pnl_pct"] for m in meta})
