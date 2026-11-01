# AI Bubble Tracker

Suivi personnel de la « bulle IA » : cours des entreprises concernées, portefeuilles **fictifs** (10 000 € chacun, départ le 30/10/2026) pour chaque stratégie, signaux de crédit (CDS) et de la Fed, newsletter hebdomadaire.

> Outil d'analyse personnel. Ce n'est pas un conseil en investissement.

## Fonctionnement

| Quoi | Où | Quand |
|---|---|---|
| Cours de clôture (Yahoo Finance) | `data/prices.csv` | chaque soir de bourse (GitHub Actions) |
| Valeur des stratégies fictives | `data/strategies.csv`, `data/dashboard.json` | idem |
| Résumé par actif (variations, distance aux plus hauts) | `data/assets_summary.csv` | idem |
| Signaux CDS / Fed (relevés dans la presse) | `data/signals.csv` | chaque lundi par la newsletter, ou à la main |
| Newsletter | `newsletters/AAAA-MM-JJ.md` | chaque lundi |

Lancer à la main : onglet **Actions** → « Mise à jour quotidienne des cours » → **Run workflow**.

## Les stratégies suivies

| Id | Stratégie | Plateforme | Construction fictive |
|---|---|---|---|
| `leaders` | Leaders qui encaissent | Trade Republic | 25 % Nvidia, TSMC, Alphabet, Microsoft |
| `pelles` | Pelles & pioches | Trade Republic (PEA) | 25 % Schneider, Siemens Energy, Legrand, ASML |
| `pair` | Pair trade Nvidia / CoreWeave | Axi (CFD) | long 10 000 € NVDA, short 5 000 € CRWV, financement estimé 6,5 % / 2 % par an |
| `hedged` | Leaders + couverture | TR + Axi | `leaders` + short Nasdaq-100 sur 40 % |
| `paliers` | Leaders par paliers | Trade Republic | 3 achats à 1 mois d'intervalle : 30/10, 30/11, 30/12 |

Un **rétro-test** depuis le 31/07/2026 applique les mêmes règles sur les 3 mois précédents (dont la baisse d'octobre).

Repères : ETF MSCI World (URTH) et Nasdaq-100, convertis en euros.

## Modifier

- Ajouter un titre : `config/universe.json`
- Changer une stratégie (poids, ratio de couverture, frais) : `config/strategies.json`
- Seuils d'alerte et calendrier : `config/thresholds.json`
- Ajouter un relevé de CDS : une ligne dans `data/signals.csv`

## Tableau de bord et newsletter

- Tableau de bord public (GitHub Pages) : https://paulleriic.github.io/ai-bubble-tracker/, reconstruit à chaque mise à jour par `scripts/build_site.py`. Même page sur Claude : https://claude.ai/artifact/2yc1SDPvQVvpVnHM7qCVtf. Le code de la page est dans `dashboard/index.html`.
- La tâche planifiée Claude qui le met à jour et rédige la newsletter du lundi suit `ROUTINE.md`.
