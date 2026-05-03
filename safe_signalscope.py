import re
from collections import Counter
from typing import Any

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "into", "total", "energy", "energie", "group", "company"
}

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PRICE_RE = re.compile(r"\b(?:\$|usd|eur|btc|xmr|monero)\b", re.I)
TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

DOC_TERMS = ["passport", "license", "id card", "template", "scan", "forgery", "counterfeit"]
ACCESS_TERMS = ["credentials", "password", "admin", "vpn", "rdp", "ssh", "access", "token", "api key"]
LEAK_TERMS = ["dump", "leak", "database", "customer", "employee", "internal", "breach", "records"]

JUNK_TITLE_TERMS = ["directory", "search engine", "catalog", "trusted", "safe market"]
JUNK_CONTENT_TERMS = ["click here", "register now", "anonymity guaranteed", "sponsored", "advertisement"]
NOISE_LINE_RE = [
    re.compile(r"^\s*$"),
    re.compile(r"^(home|login|register|menu|next|previous|search)$", re.I),
]


def _clean_text(text: str) -> str:
    lines = []
    seen = set()
    for raw in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 3:
            continue
        if any(rx.match(line) for rx in NOISE_LINE_RE):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    joined = " ".join(lines)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined[:18000]


def _normalize_text(item: dict[str, Any]) -> str:
    title = item.get("final_title") or item.get("title", "")
    content = _clean_text(item.get("content", ""))
    return f"{title} {content}".lower().strip()


def _tokenize_query(query: str) -> list[str]:
    raw = TOKEN_RE.findall(query.lower())
    uniq = []
    seen = set()
    for tok in raw:
        if tok in STOPWORDS:
            continue
        if tok not in seen:
            seen.add(tok)
            uniq.append(tok)
    return uniq


def _token_hits(text: str, query_tokens: list[str]) -> list[str]:
    hits = []
    for tok in query_tokens:
        if tok in text:
            hits.append(tok)
            continue
        if len(tok) >= 5 and tok[:-1] in text:
            hits.append(tok)
    return hits


def _junk_penalty(title: str, text: str) -> int:
    penalty = 0
    t = (title or "").lower()
    if any(term in t for term in JUNK_TITLE_TERMS):
        penalty += 12
    if any(term in text for term in JUNK_CONTENT_TERMS):
        penalty += 8
    return penalty


def analyze_item(item: dict[str, Any], query: str) -> dict[str, Any]:
    text = _normalize_text(item)
    query_tokens = _tokenize_query(query)
    q_hits = _token_hits(text, query_tokens)

    if not query_tokens:
        return {**item, "kept": False, "score": 0, "bucket": "noise", "reason": "query_not_specific"}
    if not q_hits:
        return {**item, "kept": False, "score": 0, "bucket": "noise", "reason": "no_query_token_match"}

    title = item.get("final_title") or item.get("title", "")
    content = _clean_text(item.get("content", ""))
    indicators = {
        "query_tokens": q_hits,
        "emails": EMAIL_RE.findall(content)[:10],
        "price_marker": bool(PRICE_RE.search(text)),
        "doc_terms": [t for t in DOC_TERMS if t in text],
        "access_terms": [t for t in ACCESS_TERMS if t in text],
        "leak_terms": [t for t in LEAK_TERMS if t in text],
        "content_chars": len(content),
    }

    score = 8 + min(32, len(q_hits) * 10)
    if indicators["emails"]:
        score += 8
    if indicators["price_marker"]:
        score += 4
    score += min(20, len(indicators["doc_terms"]) * 4)
    score += min(20, len(indicators["access_terms"]) * 4)
    score += min(20, len(indicators["leak_terms"]) * 4)

    if indicators["content_chars"] > 800:
        score += 6
    elif indicators["content_chars"] < 120:
        score -= 8

    score -= _junk_penalty(title, text)

    duplicate_count = int(item.get("duplicate_count", 1) or 1)
    if duplicate_count > 1:
        score -= min(8, (duplicate_count - 1) * 2)

    score = max(score, 0)

    if score >= 60:
        bucket = "priority"
    elif score >= 22:
        bucket = "emerging"
    else:
        bucket = "noise"

    return {**item, "kept": bucket != "noise", "score": score, "bucket": bucket, "indicators": indicators}


def analyze_results(items: list[dict[str, Any]], query: str) -> dict[str, list[dict[str, Any]]]:
    analyzed = [analyze_item(item, query) for item in items]
    priority = sorted((x for x in analyzed if x["bucket"] == "priority"), key=lambda x: x["score"], reverse=True)
    emerging = sorted((x for x in analyzed if x["bucket"] == "emerging"), key=lambda x: x["score"], reverse=True)
    noise = sorted((x for x in analyzed if x["bucket"] == "noise"), key=lambda x: x.get("reason", ""))
    return {"priority": priority, "emerging": emerging, "noise": noise, "all": analyzed}


def generate_local_report(query: str, analyzed: dict[str, list[dict[str, Any]]]) -> str:
    all_items = analyzed["all"]
    page_types = Counter([x.get("page_type", "unknown") for x in all_items])
    avg_score = round(sum(x.get("score", 0) for x in all_items) / max(len(all_items), 1), 1)
    return (
        f"Objet: {query}\n"
        f"Résultats: {len(all_items)}\n"
        f"Prioritaires: {len(analyzed['priority'])}\n"
        f"Émergents: {len(analyzed['emerging'])}\n"
        f"Score moyen: {avg_score}\n"
        f"Typologies: {', '.join([f'{k} ({v})' for k, v in page_types.most_common(5)]) or 'aucune'}"
    )
