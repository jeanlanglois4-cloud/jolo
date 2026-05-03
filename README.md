# SignalScope (version défensive)

Cette version se concentre sur l'**analyse défensive** de résultats déjà collectés (JSON/CSV internes), sans scraping actif de services illicites.

## Améliorations apportées (v2)
- Nettoyage de bruit renforcé: suppression des lignes de navigation, déduplication de lignes, normalisation d'espaces.
- Scoring plus robuste: seuils revus, pénalité de bruit (titres/contenus promotionnels), pénalité de duplicats.
- Matching requête plus tolérant: tokenisation regex + petite tolérance morphologique (tokens tronqués).
- Rapport local enrichi avec score moyen global.

## Utilisation rapide
```python
from safe_signalscope import analyze_results, generate_local_report

items = [
    {"title": "Example", "content": "employee database leak", "page_type": "forum_post"}
]
analysis = analyze_results(items, query="employee leak")
print(generate_local_report("employee leak", analysis))
```

## Note
Je ne fournis pas d'aide pour développer ou opérer un moteur de recherche orienté activités illicites.
