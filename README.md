# SignalScope (version défensive)

Cette version se concentre sur l'**analyse défensive** de résultats déjà collectés (JSON/CSV internes), sans scraping actif de services illicites.

## Ce qui a été ajouté
- `safe_signalscope.py` : moteur de scoring local pour classer des éléments en `priority`, `emerging`, `noise`.
- Rapport local synthétique en français.

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
