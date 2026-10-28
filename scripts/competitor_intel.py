#!/usr/bin/env python3
"""
competitor_intel.py — Reads latest gap analysis, searches Google for top-ranking
competitors on each keyword, analyzes why they're winning, assigns threat levels.
"""

import os
import json
import datetime
import time
import requests
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


def search_google(query, num_results=3):
    """Search Google and return top organic results using SerpAPI or requests fallback."""
    # Try DataForSEO if credentials available
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")

    if login and password:
        # Over-fetch so dropping our own domain still leaves num_results rivals
        results = search_dataforseo(query, login, password, num_results + 3)
        return [r for r in results if not is_own_domain(r.get("domain"))][:num_results]
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


def analyze_competitor(competitor, keyword):
    """Assign threat level and generate specific reason they're winning."""
    domain = competitor.get("domain", "")
    title = competitor.get("title", "")
    url = competitor.get("url", "")
    rank = competitor.get("rank", 1)

    # High-authority domains
    high_authority_domains = [
        "shopify.com", "hubspot.com", "semrush.com", "ahrefs.com", "moz.com",
        "neil patel", "backlinko", "searchengineland", "searchenginejournal",
        "make.com", "zapier.com", "hootsuite.com", "buffer.com",
    ]

    is_high_authority = any(d in domain.lower() for d in high_authority_domains)
    has_year = "2026" in title or "2025" in title
    has_comparison = any(w in title.lower() for w in ["vs", "versus", "compare", "best", "top"])
    has_guide = any(w in title.lower() for w in ["guide", "tutorial", "how to", "steps"])
    is_brand_result = keyword.lower().split()[0] in domain.lower() if keyword else False

    # Assign threat and reason
    if is_brand_result:
        threat = "HIGH"
        reason = f"Ranking for their own brand term — not beatable on this exact query. Target a 'best alternatives to {domain}' angle instead."
    elif is_high_authority:
        threat = "HIGH"
        reason = f"Massive domain authority (DR 80+). Hard to displace with content alone — target their gap keywords instead, or go 3x deeper on a specific sub-topic they only skim."
    elif has_year:
        threat = "MEDIUM"
        reason = f"Published with '{('2026' if '2026' in title else '2025')}' in title/URL — recency signal Google is rewarding. Fix: update your title to include the year and add a 'What's changed' section."
    elif has_comparison:
        threat = "MEDIUM"
        reason = f"Comparison or listicle format above the fold — Google AI Overview pulls from structured tables. Fix: add a comparison table to your post and move it higher up the page."
    elif has_guide:
        threat = "MEDIUM"
        reason = f"Comprehensive guide format with likely strong internal linking. Fix: match the content depth and make sure your post has at least 5 internal links pointing to it."
    else:
        threat = "LOW"
        reason = f"Appears to be thin content or ranking on coincidence. Beatable with a single focused, well-structured 1,500-word post targeting this query directly."

    return threat, reason


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
            threat, reason = analyze_competitor(comp, keyword)
            entry = {
                "keyword": keyword,
                "competitor": comp.get("domain", "unknown"),
                "url": comp.get("url", ""),
                "threat": threat,
                "reason": reason,
            }
            keyword_results.append(entry)
            results.append(entry)

            if threat == "LOW":
                quick_wins.append(entry)
            if threat == "HIGH":
                avoid_list.append({"keyword": keyword, "competitor": comp.get("domain"), "reason": reason})

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
