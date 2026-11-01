"""Récupère quelques données fondamentales (Yahoo Finance) -> data/fundamentals.csv
Capitalisation, PER historique et prévisionnel, dette, trésorerie, free cash-flow."""
import json, sys, time
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
U = json.loads((ROOT / "config/universe.json").read_text())
FIELDS = {"marketCap": "capitalisation", "trailingPE": "per_historique", "forwardPE": "per_previsionnel",
          "totalDebt": "dette", "totalCash": "tresorerie", "freeCashflow": "free_cash_flow",
          "revenueGrowth": "croissance_ca", "currency": "devise", "financialCurrency": "devise_comptes"}
rows = []
for a in U["assets"]:
    if a["group"] in ("Indices", "Signaux"):
        continue
    info = {}
    for attempt in range(3):
        try:
            info = yf.Ticker(a["ticker"]).info or {}
            break
        except Exception as e:  # limite de Yahoo : on réessaie
            print("retry", a["ticker"], e, file=sys.stderr)
            time.sleep(3)
    row = {"ticker": a["ticker"], "name": a["name"], "group": a["group"]}
    for k, v in FIELDS.items():
        row[v] = info.get(k)
    rows.append(row)
    time.sleep(0.5)
df = pd.DataFrame(rows)
old = ROOT / "data/fundamentals.csv"
if df[["capitalisation", "per_previsionnel"]].notna().sum().sum() == 0 and old.exists():
    print("Aucune donnée reçue : on garde l'ancien fichier", file=sys.stderr)
else:
    df.to_csv(old, index=False)
print(df[["ticker", "per_historique", "per_previsionnel", "free_cash_flow"]].to_string())
