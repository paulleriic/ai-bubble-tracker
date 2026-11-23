"""Télécharge les cours de clôture quotidiens (Yahoo Finance) -> data/prices.csv"""
import json, sys
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config/universe.json").read_text())
tickers = [a["ticker"] for a in cfg["assets"]]

raw = yf.download(tickers, start=cfg["history_start"], auto_adjust=True,
                  progress=False, group_by="column", threads=True)
close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
close = close.reindex(columns=tickers)
close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
close = close[~close.index.duplicated(keep="last")].sort_index()
close = close.dropna(how="all")

missing = [t for t in tickers if close[t].dropna().empty]
if missing:
    print("ATTENTION, aucun cours pour :", ", ".join(missing), file=sys.stderr)

# Si Yahoo ne renvoie rien pour un titre, on garde l'historique déjà connu
# (sinon toute la colonne serait effacée de data/prices.csv).
old_path = ROOT / "data/prices.csv"
if old_path.exists():
    old = pd.read_csv(old_path, index_col=0, parse_dates=True)
    old = old.reindex(columns=tickers)
    close = close.combine_first(old).reindex(columns=tickers).sort_index()

close.index.name = "date"
close.round(6).to_csv(ROOT / "data/prices.csv")
print(f"{len(close)} jours, dernier = {close.index[-1].date()}")
