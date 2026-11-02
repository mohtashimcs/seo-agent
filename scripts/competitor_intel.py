#!/usr/bin/env python3
"""
competitor_intel.py — Reads latest gap analysis, searches Google for top-ranking
competitors on each keyword, analyzes why they're winning, assigns threat levels.
"""

import os
import json
import datetime
import time
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def get_latest_gap_analysis():
    """Find the most recent gap analysis JSON in /reports."""
    reports = sorted(Path("reports").glob("gap-analysis-*.json"), reverse=True)
    if not reports:
        raise FileNotFoundError("No gap analysis found. Run gap_finder.py first.")
    with open(reports[0]) as f:
        return json.load(f)


def own_domain():
    """Bare domain of our own site, derived from GSC_SITE_URL."""
    site = os.getenv("GSC_SITE_URL", "")
    site = site.replace("sc-domain:", "").split("://")[-1].split("/")[0].lower()
    return site[4:] if site.startswith("www.") else site


def is_own_domain(domain):
    own = own_domain()
    domain = (domain or "").lower()
    return bool(own) and (domain == own or domain.endswith("." + own))


# Not rankable competitors: Google's own redirect/feature links and UGC/video hosts
NON_COMPETITOR_DOMAINS = {
    "google.com", "youtube.com", "reddit.com", "quora.com", "facebook.com",
    "linkedin.com", "pinterest.com", "x.com", "twitter.com", "wikipedia.org",
}


def is_non_competitor(domain):
    domain = (domain or "").lower()
    return any(domain == d or domain.endswith("." + d) for d in NON_COMPETITOR_DOMAINS)


def search_google(query, num_results=3):
    """Search Google and return top organic results using SerpAPI or requests fallback."""
    # Try DataForSEO if credentials available
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")

    if login and password:
        # Over-fetch so dropping our own domain and Google/YouTube rows still leaves num_results rivals
        results = search_dataforseo(query, login, password, num_results + 10)
        seen, rivals = set(), []
        for r in results:
            domain = r.get("domain")
            if is_own_domain(domain) or is_non_competitor(domain) or domain in seen:
                continue
            seen.add(domain)
            rivals.append(r)
        return rivals[:num_results]
    else:
        # Fallback: basic search via requests (limited, for demo)
        return search_basic(query, num_results)


def search_dataforseo(query, login, password, num_results=3, attempts=4):
    """Use DataForSEO SERP API to get real competitor data.

    Retries with backoff on timeouts, rate limits, and empty results.
    Returns [] if every attempt fails — never placeholder data.
    """
    url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    payload = [{
        "keyword": query,
        "location_code": 2840,  # United States
        "language_code": "en",
        "depth": 10,
    }]

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, auth=(login, password), json=payload, timeout=90)
            task = (response.json().get("tasks") or [{}])[0]
            if task.get("status_code") != 20000:
                raise RuntimeError(f"task {task.get('status_code')}: {task.get('status_message')}")
            items = ((task.get("result") or [{}])[0] or {}).get("items") or []
            results = [
                {
                    "url": item.get("url", ""),
                    "domain": item.get("domain", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "rank": item.get("rank_absolute", 0),
                }
                for item in items if item.get("type") == "organic"
            ][:num_results]
            if not results:
                raise RuntimeError("no organic results returned")
            return results
        except Exception as e:
            print(f"  DataForSEO attempt {attempt}/{attempts} failed: {e}")
            if attempt < attempts:
                time.sleep(5 * attempt)
    return []


def search_basic(query, num_results=3):
    """Basic fallback — returns placeholder structure for demo purposes."""
    # In production, replace with SerpAPI or similar
    # For demo/recording purposes, returns realistic mock data
    return [
        {"domain": f"competitor-{i+1}.com", "title": f"Top result {i+1} for {query}", "url": f"https://competitor-{i+1}.com/{query.replace(' ', '-')}", "rank": i+1}
        for i in range(num_results)
    ]


HIGH_AUTHORITY_DOMAINS = [
    "nerdwallet.com", "experian.com", "equifax.com", "transunion.com", "forbes.com",
    "bankrate.com", "investopedia.com", "creditkarma.com", "nav.com", "citi.com",
    "chase.com", "ftc.gov", "consumerfinance.gov", "myfico.com", "lendingtree.com",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_page(url, attempts=2):
    """Fetch a competitor page. Returns HTML text, or None if it can't be read."""
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(
                url, timeout=20, allow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            )
            if resp.status_code == 200 and "html" in resp.headers.get("content-type", "html"):
                return resp.text[:2_000_000]
            if resp.status_code in (401, 403, 404, 410):
                return None  # blocked or gone — retrying won't help
        except requests.RequestException:
            pass
        if attempt < attempts:
            time.sleep(2)
    return None


def _walk_json(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk_json(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_json(v)


def extract_signals(html, domain):
    """Measure what the page actually contains."""
    soup = BeautifulSoup(html, "html.parser")

    schema_types, modified = set(), None
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        for node in _walk_json(data):
            t = node.get("@type")
            for name in (t if isinstance(t, list) else [t]):
                if isinstance(name, str):
                    schema_types.add(name)
            modified = modified or node.get("dateModified") or node.get("datePublished")
    for prop in ("article:modified_time", "article:published_time", "og:updated_time"):
        meta = soup.find("meta", attrs={"property": prop})
        if meta and meta.get("content"):
            modified = modified or meta["content"]

    age_days = None
    if modified:
        try:
            when = datetime.datetime.fromisoformat(str(modified)[:10])
            age_days = (datetime.datetime.now() - when).days
        except ValueError:
            pass

    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    text = root.get_text(" ", strip=True)

    own = domain.lower().removeprefix("www.")
    internal = {
        a["href"].split("#")[0] for a in root.find_all("a", href=True)
        if a["href"].startswith("/") or own in a["href"].lower()
    }
    h1 = soup.find("h1")
    headings = [h.get_text(" ", strip=True).lower() for h in root.find_all(["h2", "h3"])]
    lower = text.lower()

    return {
        "words": len(text.split()),
        "h2_count": len(root.find_all("h2")),
        "tables": len(root.find_all("table")),
        "has_faq": "FAQPage" in schema_types or any("faq" in h or h.endswith("?") for h in headings),
        "schema": sorted(schema_types & {"FAQPage", "Product", "Article", "BlogPosting", "Review", "AggregateRating", "Organization", "HowTo"}),
        "internal_links": len(internal),
        "age_days": age_days,
        "price_shown": bool(re.search(r"\$\s?\d{2,4}", text)),
        "guarantee": "guarantee" in lower,
        "year_in_title": bool(re.search(r"20(25|26)", (soup.title.string or "") if soup.title else "")),
        "h1": h1.get_text(" ", strip=True) if h1 else "",
    }


def analyze_competitor(competitor, keyword):
    """Fetch the page, measure it, and return (threat, reason, signals).

    Threat comes from a strength score built only from measured signals. If the
    page can't be read, the result is MEDIUM and says so — never a guessed LOW.
    """
    domain = competitor.get("domain", "")
    title = competitor.get("title", "")
    url = competitor.get("url", "")
    domain_label = domain.lower().removeprefix("www.").split(".")[0]
    exact_match = bool(keyword) and keyword.lower().replace(" ", "") in domain_label

    html = fetch_page(url) if url else None
    sig = extract_signals(html, domain) if html else None
    # A near-empty body means a JS-rendered shell, not a thin page — don't score it
    if sig is not None and sig["words"] < 150:
        html = None
    if html is None:
        return "MEDIUM", (
            f"Page could not be read (blocked, JS-rendered or unavailable), so depth is unmeasured. "
            f"Title: \"{title[:80]}\". Review {domain} manually before treating this as a quick win."
        ), None

    strengths, gaps = [], []
    score = 0

    if any(d in domain.lower() for d in HIGH_AUTHORITY_DOMAINS):
        score += 3
        strengths.append(f"high-authority domain ({domain})")
    if exact_match:
        score += 2
        strengths.append("exact-match domain")
    if sig["words"] >= 2500:
        score += 2
        strengths.append(f"{sig['words']:,}-word page")
    elif sig["words"] >= 1200:
        score += 1
        strengths.append(f"{sig['words']:,} words")
    else:
        gaps.append(f"only {sig['words']:,} words")
    if sig["tables"]:
        score += 1
        strengths.append(f"{sig['tables']} comparison/data table(s)")
    if sig["has_faq"]:
        score += 1
        strengths.append("FAQ section")
    if sig["schema"]:
        score += 1
        strengths.append("schema: " + ", ".join(sig["schema"]))
    if sig["internal_links"] >= 40:
        score += 1
        strengths.append(f"{sig['internal_links']} internal links")
    if sig["age_days"] is not None and sig["age_days"] <= 180:
        score += 1
        strengths.append(f"updated {sig['age_days']} days ago")
    elif sig["age_days"] is not None and sig["age_days"] > 540:
        gaps.append(f"last updated {sig['age_days']} days ago")
    if sig["year_in_title"]:
        score += 1
        strengths.append("year in title")

    if score >= 6:
        threat = "HIGH"
    elif score >= 3:
        threat = "MEDIUM"
    else:
        threat = "LOW"

    if threat == "HIGH":
        reason = (
            "Hard to displace: " + "; ".join(strengths[:4]) + ". "
            "Fix: don't fight the exact query head-on — win a narrower angle "
            "(reporting dates, order-by deadlines, who a tradeline won't help)."
        )
    else:
        fixes = []
        if not sig["tables"]:
            fixes.append("add a comparison table")
        if not sig["has_faq"]:
            fixes.append("add an FAQ with FAQPage schema")
        if sig["words"] < 1500:
            fixes.append("write a 1,500+ word guide")
        if sig["age_days"] is None or sig["age_days"] > 365:
            fixes.append("show a recent 'last updated' date")
        if not sig["price_shown"]:
            fixes.append("show pricing/line details before checkout")
        edge = "; ".join(strengths[:3]) or "no strong structural advantage"
        weak = "; ".join(gaps[:2])
        reason = f"Edge: {edge}." + (f" Weak spots: {weak}." if weak else "")
        reason += " Fix: " + ", ".join(fixes[:3]) + "." if fixes else ""
    return threat, reason, {**sig, "score": score}


def keyword_benchmark(entries):
    """Average the measured top-result pages so content briefs have a target."""
    measured = [e["signals"] for e in entries if e.get("signals")]
    if not measured:
        return None
    return {
        "pages_measured": len(measured),
        "avg_words": round(sum(m["words"] for m in measured) / len(measured)),
        "pct_with_table": round(100 * sum(1 for m in measured if m["tables"]) / len(measured)),
        "pct_with_faq": round(100 * sum(1 for m in measured if m["has_faq"]) / len(measured)),
        "pct_showing_price": round(100 * sum(1 for m in measured if m["price_shown"]) / len(measured)),
    }


def run_competitor_intel():
    print("🔍 Loading latest gap analysis...")
    gap_data = get_latest_gap_analysis()
    keywords = [kw["keyword"] for kw in gap_data.get("keywords", [])[:8]]

    if not keywords:
        print("⚠️  No keywords found in gap analysis.")
        return

    print(f"🏆 Analyzing competitors for {len(keywords)} keywords...\n")

    results = []
    quick_wins = []
    avoid_list = []
    failed_keywords = []
    benchmarks = {}

    for keyword in keywords:
        print(f"  Searching: \"{keyword}\"...")
        competitors = search_google(keyword, num_results=3)
        time.sleep(3)  # Rate limiting

        if not competitors:
            print(f"  ⚠️  \"{keyword}\" — no data after retries, skipping")
            failed_keywords.append(keyword)
            continue

        keyword_results = []
        for comp in competitors:
            threat, reason, signals = analyze_competitor(comp, keyword)
            entry = {
                "keyword": keyword,
                "competitor": comp.get("domain", "unknown"),
                "url": comp.get("url", ""),
                "threat": threat,
                "reason": reason,
                "signals": signals,
            }
            time.sleep(1)
            keyword_results.append(entry)
            results.append(entry)

            if threat == "LOW" and signals:
                quick_wins.append(entry)
            if threat == "HIGH":
                avoid_list.append({"keyword": keyword, "competitor": comp.get("domain"), "reason": reason})

        benchmarks[keyword] = keyword_benchmark(keyword_results)

        # Print summary per keyword
        threats = [r["threat"] for r in keyword_results]
        dominant = max(set(threats), key=threats.count)
        emoji = "🔴" if dominant == "HIGH" else "🟡" if dominant == "MEDIUM" else "🟢"
        print(f"  {emoji} \"{keyword}\" — dominant threat: {dominant}")

    # ── Save outputs ──────────────────────────────────────────────────────
    today = datetime.date.today().isoformat()
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    output_data = {
        "date": today,
        "keywords_analyzed": len(keywords) - len(failed_keywords),
        "failed_keywords": failed_keywords,
        "benchmarks": benchmarks,
        "results": results,
        "quick_wins": quick_wins[:3],
        "avoid_list": avoid_list[:3],
    }

    json_path = reports_dir / f"competitive-{today}.json"
    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2)

    md_path = reports_dir / f"competitive-{today}.md"
    with open(md_path, "w") as f:
        f.write(f"# Competitive Intelligence Report\n")
        f.write(f"**Date:** {today}\n\n")
        f.write(f"## Competitor Table\n\n")
        f.write("| Keyword | Competitor | Threat | Why They Win |\n")
        f.write("|---|---|---|---|\n")
        for r in results:
            threat_emoji = "🔴" if r["threat"] == "HIGH" else "🟡" if r["threat"] == "MEDIUM" else "🟢"
            f.write(f"| {r['keyword']} | {r['competitor']} | {threat_emoji} {r['threat']} | {r['reason']} |\n")

        f.write("\n## Content Benchmarks (measured from top-ranking pages)\n\n")
        f.write("| Keyword | Pages measured | Avg words | With table | With FAQ | Show price |\n|---|---|---|---|---|---|\n")
        for kw, b in benchmarks.items():
            if b:
                f.write(f"| {kw} | {b['pages_measured']} | {b['avg_words']:,} | {b['pct_with_table']}% | {b['pct_with_faq']}% | {b['pct_showing_price']}% |\n")
            else:
                f.write(f"| {kw} | 0 | n/a | n/a | n/a | n/a |\n")

        if failed_keywords:
            f.write(f"\n**No data (lookup failed):** {', '.join(failed_keywords)}\n")

        f.write(f"\n## Quick Wins (LOW Threat — Displaceable This Month)\n")
        for qw in quick_wins[:3]:
            f.write(f"- **{qw['keyword']}** → {qw['competitor']}: {qw['reason']}\n")

        f.write(f"\n## Avoid Direct Competition\n")
        for av in avoid_list[:3]:
            f.write(f"- **{av['keyword']}** → {av['competitor']}: {av['reason']}\n")

    print(f"\n✅ Reports saved:")
    print(f"   {md_path}")
    print(f"   {json_path}")
    if failed_keywords:
        print(f"\n⚠️  {len(failed_keywords)} keyword(s) had no data: {', '.join(failed_keywords)}")
    print(f"\n🟢 Quick wins: {len(quick_wins)} LOW-threat competitors you can displace this month")
    print(f"🔴 Avoid: {len(avoid_list)} HIGH-threat keywords — find related angles instead")

    return output_data


if __name__ == "__main__":
    run_competitor_intel()
