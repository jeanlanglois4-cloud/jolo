import re
from collections import Counter
from typing import Any

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "into",
    "total", "energy", "energie", "group", "company"
}

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PRICE_RE = re.compile(r"\b(?:\$|usd|eur|btc|xmr|monero)\b", re.I)

DOC_TERMS = ["passport", "license", "id card", "template", "scan", "forgery", "counterfeit"]
ACCESS_TERMS = ["credentials", "password", "admin", "vpn", "rdp", "ssh", "access", "token", "api key"]
LEAK_TERMS = ["dump", "leak", "database", "customer", "employee", "internal", "breach", "records"]


def _normalize_text(item: dict[str, Any]) -> str:
    return f"{item.get('title', '')} {item.get('content', '')}".lower()


def _tokenize_query(query: str) -> list[str]:
    return [p for p in query.lower().split() if len(p) >= 3 and p not in STOPWORDS]


def analyze_item(item: dict[str, Any], query: str) -> dict[str, Any]:
    text = _normalize_text(item)
    q_tokens = [tok for tok in _tokenize_query(query) if tok in text]

    if not q_tokens:
        return {**item, "kept": False, "score": 0, "reason": "no_query_token_match"}

    indicators = {
        "query_tokens": q_tokens,
        "emails": EMAIL_RE.findall(item.get("content", ""))[:10],
        "price_marker": bool(PRICE_RE.search(text)),
        "doc_terms": [t for t in DOC_TERMS if t in text],
        "access_terms": [t for t in ACCESS_TERMS if t in text],
        "leak_terms": [t for t in LEAK_TERMS if t in text],
    }

    score = 10 * min(len(q_tokens), 3)
    if indicators["emails"]:
        score += 8
    if indicators["price_marker"]:
        score += 4
    score += min(20, len(indicators["doc_terms"]) * 4)
    score += min(20, len(indicators["access_terms"]) * 4)
    score += min(20, len(indicators["leak_terms"]) * 4)

    if score >= 55:
        bucket = "priority"
    elif score >= 20:
        bucket = "emerging"
    else:
        bucket = "noise"

    return {
        **item,
        "kept": bucket != "noise",
        "score": score,
        "bucket": bucket,
        "indicators": indicators,
    }


def analyze_results(items: list[dict[str, Any]], query: str) -> dict[str, list[dict[str, Any]]]:
    analyzed = [analyze_item(item, query) for item in items]
    priority = sorted([x for x in analyzed if x["bucket"] == "priority"], key=lambda x: x["score"], reverse=True)
    emerging = sorted([x for x in analyzed if x["bucket"] == "emerging"], key=lambda x: x["score"], reverse=True)
    noise = [x for x in analyzed if x["bucket"] == "noise"]
    return {"priority": priority, "emerging": emerging, "noise": noise, "all": analyzed}


def generate_local_report(query: str, analyzed: dict[str, list[dict[str, Any]]]) -> str:
    all_items = analyzed["all"]
    page_types = Counter([x.get("page_type", "unknown") for x in all_items])
    return (
        f"Objet: {query}\n"
        f"Résultats: {len(all_items)}\n"
        f"Prioritaires: {len(analyzed['priority'])}\n"
        f"Émergents: {len(analyzed['emerging'])}\n"
        f"Typologies: {', '.join([f'{k} ({v})' for k, v in page_types.most_common(5)]) or 'aucune'}"
    )
