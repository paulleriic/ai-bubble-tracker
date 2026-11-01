"""Calcule les portefeuilles fictifs (suivi réel + rétro-test), le résumé des actifs et les alertes.

Sorties :
  data/strategies.csv, data/strategies_backtest.csv   valeur quotidienne de chaque stratégie (EUR)
  data/assets_summary.csv                              variations et distance aux plus hauts
  data/dashboard.json                                  résumé (stratégies, alertes, calendrier)
  data/dash/*.json                                     fichiers lus par le tableau de bord Claude
"""
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
names = {a["ticker"]: a["name"] for a in U["assets"]}
fx = px[U["fx"]]  # USD pour 1 EUR


def eur(t):
    s = px[t]
    return s / fx if ccy[t] == "USD" else s


def first_on_or_after(d, idx):
    after = idx[idx >= pd.Timestamp(d)]
    return after[0] if len(after) else None


def run(start_date):
    start = first_on_or_after(start_date, px.index)
    idx = px.index[px.index >= start]
    days = pd.Series((idx - start).days, index=idx)

    def basket(weights, amount=CAP, entry=start):
        v = pd.Series(0.0, index=idx)
        for t, w in weights.items():
            p = eur(t).loc[idx]
            v += amount * w * p / p.loc[entry]
        return v

    out = pd.DataFrame(index=idx)
    by_id = {}
    for st in S["strategies"]:
        if st["type"] == "basket":
            v = basket(st["weights"])
        elif st["type"] == "pair":
            rl = eur(st["long"]).loc[idx] / eur(st["long"]).loc[start] - 1
            rs = eur(st["short"]).loc[idx] / eur(st["short"]).loc[start] - 1
            fin = days / 365 * (st["long_notional"] * st["financing_long_annual"]
                                + st["short_notional"] * st["financing_short_annual"])
            out["pair_long_pnl"] = st["long_notional"] * rl
            out["pair_short_pnl"] = -st["short_notional"] * rs
            out["pair_financing"] = -fin
            v = CAP + st["long_notional"] * rl - st["short_notional"] * rs - fin
        elif st["type"] == "hedged":
            rh = eur(st["hedge"]).loc[idx] / eur(st["hedge"]).loc[start] - 1
            n = CAP * st["hedge_ratio"]
            out["hedged_hedge_pnl"] = -n * rh
            v = by_id[st["base"]] - n * rh - days / 365 * n * st["financing_short_annual"]
        elif st["type"] == "dca":
            w = next(x for x in S["strategies"] if x["id"] == st["base_weights_from"])["weights"]
            k = len(st["tranche_months"])
            v = pd.Series(0.0, index=idx)
            invested = pd.Series(0.0, index=idx)
            for m in st["tranche_months"]:
                e = first_on_or_after(start + pd.DateOffset(months=m), idx)
                if e is None:
                    continue  # palier pas encore atteint : reste en cash
                v += basket(w, CAP / k, e).where(idx >= e, 0.0)
                invested += pd.Series(np.where(idx >= e, CAP / k, 0.0), index=idx)
            out["paliers_invested"] = invested
            v = v + (CAP - invested)  # cash non investi, rémunéré 0 %
        by_id[st["id"]] = v
        out[st["id"]] = v
    for b in S["benchmarks"]:
        p = eur(b["ticker"]).loc[idx]
        out[b["id"]] = CAP * p / p.loc[start]
    out.index.name = "date"

    stats = []
    for item in S["strategies"] + S["benchmarks"]:
        v = out[item["id"]]
        stats.append({
            "id": item["id"], "name": item["name"],
            "platform": item.get("platform", "Repère"), "thesis": item.get("thesis", ""),
            "kind": "benchmark" if item in S["benchmarks"] else "strategy",
            "start": str(start.date()), "value": round(float(v.iloc[-1]), 2),
            "pnl": round(float(v.iloc[-1] - CAP), 2),
            "pnl_pct": round(float(v.iloc[-1] / CAP - 1), 5),
            "max_drawdown": round(float((v / v.cummax() - 1).min()), 5),
        })
    return out.round(2), stats


live, live_stats = run(U["start_date"])
bt, bt_stats = run(S["backtest_start"])
live.to_csv(ROOT / "data/strategies.csv")
bt.to_csv(ROOT / "data/strategies_backtest.csv")

# Résumé des actifs
last_d = px.index[-1]
start_live = first_on_or_after(U["start_date"], px.index)
rows = []
for a in U["assets"]:
    s = px[a["ticker"]].dropna()
    if s.empty:
        continue

    def chg(n):
        return round(float(s.iloc[-1] / s.iloc[-1 - n] - 1), 5) if len(s) > n else None

    w3 = s[s.index >= last_d - pd.Timedelta(days=91)]
    w52 = s[s.index >= last_d - pd.Timedelta(days=365)]
    rows.append({**a, "last": round(float(s.iloc[-1]), 4),
                 "chg_1d": chg(1), "chg_1w": chg(5), "chg_1m": chg(21),
                 "since_start": round(float(s.iloc[-1] / s.loc[:start_live].iloc[-1] - 1), 5),
                 "from_3m_high": round(float(s.iloc[-1] / w3.max() - 1), 5),
                 "from_52w_high": round(float(s.iloc[-1] / w52.max() - 1), 5)})
summary = pd.DataFrame(rows)
summary.to_csv(ROOT / "data/assets_summary.csv", index=False)

# Signaux relevés (CDS, Fed) + alertes
sig = pd.read_csv(ROOT / "data/signals.csv", parse_dates=["date"]).sort_values("date")
latest = sig.groupby("indicator").tail(1).set_index("indicator")
alerts = []
for r in T["rules"]:
    if r["indicator"] in latest.index:
        val = float(latest.loc[r["indicator"], "value"])
        hit = val > r["value"] if r["op"] == ">" else val < r["value"]
        alerts.append({**r, "current": val, "as_of": str(latest.loc[r["indicator"], "date"].date()),
                       "triggered": bool(hit)})
pair = next(x for x in S["strategies"] if x["type"] == "pair")
pair_pnl = float(live["pair"].iloc[-1] / CAP - 1)
alerts.append({"indicator": "Pair trade (perte / capital)", "op": "<", "value": pair["stop_loss_pct_capital"],
               "current": round(pair_pnl, 5), "as_of": str(last_d.date()),
               "triggered": pair_pnl < pair["stop_loss_pct_capital"],
               "action": "Stop-loss : couper le pair trade"})
for a in alerts:
    a["id"] = f'{a["indicator"]} {a["op"]} {a["value"]}'

(ROOT / "data/dashboard.json").write_text(json.dumps({
    "as_of": str(last_d.date()), "start": str(start_live.date()), "capital_eur": CAP,
    "strategies": live_stats, "backtest": bt_stats, "alerts": alerts, "events": T["events"]},
    ensure_ascii=False, indent=1))

# Fichiers du tableau de bord (lignes JSON)
D = ROOT / "data/dash"
D.mkdir(exist_ok=True)


def dump(name, records):
    (D / name).write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")))


def recs(df, mode=None):
    df = df.reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    if mode:
        df.insert(0, "mode", mode)
    return json.loads(df.to_json(orient="records"))


dump("strategies.json", recs(live, "live") + recs(bt, "backtest"))
dump("strategy_stats.json", [{"mode": "live", **x} for x in live_stats] + [{"mode": "backtest", **x} for x in bt_stats])
prices = px.copy()
prices.index.name = "date"
dump("prices.json", recs(prices.round(4)))
dump("assets.json", json.loads(summary.to_json(orient="records")))
sig2 = sig.copy()
sig2["date"] = sig2["date"].dt.strftime("%Y-%m-%d")
dump("signals.json", json.loads(sig2.fillna("").to_json(orient="records")))
dump("alerts.json", alerts)
dump("events.json", T["events"])
print("as_of", last_d.date(), "| live", {x["id"]: x["pnl_pct"] for x in live_stats},
      "| backtest", {x["id"]: x["pnl_pct"] for x in bt_stats})
