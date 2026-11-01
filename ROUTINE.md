# Routine planifiée (Claude) : mise à jour du tableau de bord et newsletter

Exécutée chaque jour de bourse vers 7 h 40 (heure de Paris) par une tâche planifiée Claude.

Tableau de bord : https://claude.ai/artifact/2yc1SDPvQVvpVnHM7qCVtf (type Dashboard)

## Chaque jour

1. Vérifier que le workflow GitHub « Mise à jour quotidienne des cours » a tourné pour la dernière séance (commit « Cours du … »). Sinon, le relancer (`POST repos/paulleriic/ai-bubble-tracker/actions/workflows/update.yml/dispatches`, ref `main`), attendre sa fin et faire `git pull`.
2. Lancer `python3 scripts/compute.py` en local (pandas et numpy suffisent) si `data/signals.csv` ou la config ont changé.
3. Recopier les fichiers dans le tableau de bord. Chaque fichier `data/dash/<id>.json` alimente le jeu de données du même nom :

| Fichier | Jeu de données |
|---|---|
| `data/dash/strategies.json` | `datasets/strategies` |
| `data/dash/strategy_stats.json` | `datasets/strategy_stats` |
| `data/dash/prices.json` | `datasets/prices` |
| `data/dash/assets.json` | `datasets/assets` |
| `data/dash/signals.json` | `datasets/signals` |
| `data/dash/alerts.json` | `datasets/alerts` |
| `data/dash/events.json` | `datasets/events` |

   Pour chacun : téléverser le fichier comme asset de l'artifact (Artifact, `asset: true`, un appel par fichier JSON), lire le document du jeu de données, puis faire un `update` (avec `if_version`) de `source.url`, `source.name` et `updated: {at, by}`. Ensuite, supprimer l'ancien asset (son id = les 32 caractères après `/_blob/` dans l'ancienne url).
4. Si une règle de `data/dash/alerts.json` passe à `triggered: true`, prévenir Paul.

## Le lundi, en plus : la newsletter

1. Rechercher sur le web l'actualité de la semaine : CDS 5 ans d'Oracle, CoreWeave et SoftBank, rendements obligataires de CoreWeave, probabilités CME FedWatch pour la prochaine réunion de la Fed, résultats et annonces de capex des entreprises suivies, notations.
2. Ajouter chaque nouveau relevé chiffré, avec sa date et son URL source, dans `data/signals.csv`. Ne jamais inventer de chiffre : si une valeur n'est pas trouvée, ne pas l'ajouter et le dire.
3. Mettre à jour `config/thresholds.json` (`events`) avec les nouvelles dates connues.
4. Relancer `scripts/compute.py`, puis l'étape 3 ci-dessus.
5. Rédiger `newsletters/AAAA-MM-JJ.md` sur le modèle de la précédente : en une phrase, chiffres de la semaine, crédit et Fed, règles déclenchées, stratégies (suivi réel et rétro-test), ce qu'on apprend, à surveiller, sources.
6. Commit et push sur `main`, puis envoyer à Paul la newsletter et le lien du tableau de bord.
