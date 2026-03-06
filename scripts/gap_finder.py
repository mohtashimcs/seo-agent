#!/usr/bin/env python3
"""
gap_finder.py — Connects to Google Search Console, identifies gap zone keywords
(positions 5–20), generates specific action recommendations, saves .md and .json reports.
"""

import os
import json
import datetime
import pickle
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Google Search Console auth ──────────────────────────────────────────────
def get_gsc_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
    token_path = Path("token.pickle")
    creds = None

    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret_file = os.getenv("GSC_CLIENT_SECRET_FILE", "credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("searchconsole", "v1", credentials=creds)


def fetch_gsc_data(service, site_url, days=90):
    """Pull query-level data from GSC for the past N days."""
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)

    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 1000,
        "startRow": 0,
    }

    response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return response.get("rows", [])


# ── Action recommendation logic ─────────────────────────────────────────────
def generate_recommendation(keyword, position, impressions, ctr):
    """Generate a specific action recommendation based on keyword signals."""
    keyword_lower = keyword.lower()

    # Heuristics for recommendation type based on position + CTR signals
    if ctr == 0.0:
        rec_type = "NO_PAGE"
        rec = f"New article opportunity. No page is capturing clicks for this query. A dedicated post targeting this exact phrase could land page 1 within 30–60 days."
    elif position <= 8 and ctr < 0.03:
        rec_type = "WEAK_TITLE"
        rec = f"Update the title and meta description. You're ranking well but not getting clicks — the snippet isn't compelling enough. Add a specific outcome or number to the title."
    elif position > 12 and impressions > 500:
        rec_type = "NO_INTERNAL_LINKS"
        rec = f"Add internal links. High impressions but deep ranking suggests the page isn't getting enough internal authority. Add 3–5 links from your highest-traffic posts."
    elif any(word in keyword_lower for word in ["how", "guide", "tutorial", "steps"]):
        rec_type = "STRUCTURAL_ISSUE"
        rec = f"Restructure the post. How-to queries reward numbered steps and a clear answer in the first paragraph. If your post buries the process, reorder it."
    elif len(keyword.split()) <= 2:
        rec_type = "NEEDS_HUB"
        rec = f"Add a hub page. Short-tail keyword suggests you're ranking for multiple variations without a central article consolidating authority. One hub page can push all variations higher."
    else:
        rec_type = "WEAK_TITLE"
        rec = f"Improve content depth. Review the top 3 ranking pages and identify what they cover that you don't. Adding a comparison table or FAQ section often pushes mid-range positions to top 5."

    return rec_type, rec


# ── Main analysis ────────────────────────────────────────────────────────────
def run_gap_analysis():
    site_url = os.getenv("GSC_SITE_URL")
    if not site_url:
        raise ValueError("GSC_SITE_URL not set in .env file")

    print(f"🔍 Connecting to Google Search Console for {site_url}...")
    service = get_gsc_service()

    print("📊 Fetching 90-day ranking data...")
    rows = fetch_gsc_data(service, site_url)

    if not rows:
        print("⚠️  No data returned from GSC. Check your site URL and permissions.")
        return

    print(f"✅ Retrieved {len(rows)} keywords. Identifying gap zone (positions 5–20)...")

    # Filter to gap zone
    gap_zone = []
    for row in rows:
        position = row.get("position", 0)
        impressions = row.get("impressions", 0)
        clicks = row.get("clicks", 0)
        ctr = row.get("ctr", 0)
        query = row["keys"][0]

        if 5 <= position <= 20 and impressions >= 1:
            rec_type, rec = generate_recommendation(query, position, impressions, ctr)
            gap_zone.append({
                "keyword": query,
                "impressions": int(impressions),
                "position": round(position, 1),
                "clicks": int(clicks),
                "ctr": round(ctr * 100, 1),
                "rec_type": rec_type,
                "recommendation": rec,
            })

    # Sort by impressions descending
    gap_zone.sort(key=lambda x: x["impressions"], reverse=True)
    top_10 = gap_zone[:10]

    print(f"🎯 Found {len(gap_zone)} gap zone keywords. Top 10 saved.")

    # ── Save JSON (for dashboard) ─────────────────────────────────────────
    today = datetime.date.today().isoformat()
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    json_path = reports_dir / f"gap-analysis-{today}.json"
    output_data = {
        "date": today,
        "site_url": site_url,
        "total_gap_keywords": len(gap_zone),
        "top_opportunity": top_10[0] if top_10 else None,
        "keywords": top_10,
        "kpis": {
            "total_impressions": sum(r.get("impressions", 0) for r in rows),
            "gap_zone_count": len(gap_zone),
            "avg_position": round(
                sum(r.get("position", 0) for r in rows) / len(rows), 1
            ) if rows else 0,
            "total_clicks": sum(r.get("clicks", 0) for r in rows),
        },
    }

    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2)

    # ── Save Markdown (human-readable) ────────────────────────────────────
    md_path = reports_dir / f"gap-analysis-{today}.md"
    with open(md_path, "w") as f:
        f.write(f"# Gap Analysis — {site_url}\n")
        f.write(f"**Date:** {today} | **Window:** 90 days\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total gap zone keywords: {len(gap_zone)}\n")
        f.write(f"- Total impressions (all keywords): {output_data['kpis']['total_impressions']:,}\n")
        f.write(f"- Avg position (all keywords): {output_data['kpis']['avg_position']}\n")
        f.write(f"- Total clicks: {output_data['kpis']['total_clicks']:,}\n\n")

        if top_10:
            f.write(f"## Top Opportunity\n")
            top = top_10[0]
            f.write(f"**\"{top['keyword']}\"** — {top['impressions']:,} impressions, position {top['position']}, {top['ctr']}% CTR\n")
            f.write(f"→ {top['recommendation']}\n\n")

        f.write(f"## Keyword Opportunity Cards (Top 10)\n\n")
        for i, kw in enumerate(top_10, 1):
            f.write(f"### {i}. \"{kw['keyword']}\"\n")
            f.write(f"- Impressions: {kw['impressions']:,}\n")
            f.write(f"- Position: {kw['position']}\n")
            f.write(f"- CTR: {kw['ctr']}%\n")
            f.write(f"- Recommendation: {kw['recommendation']}\n\n")

    print(f"\n✅ Reports saved:")
    print(f"   {md_path}")
    print(f"   {json_path}")
    if top_10:
        print(f"\n📋 Top opportunity: \"{top_10[0]['keyword']}\" at position {top_10[0]['position']}")
        print(f"   → {top_10[0]['recommendation']}")
    else:
        print(f"\n📋 No gap zone keywords found. Your 5 keywords may all be outside positions 5–20 or below 50 impressions.")

    return output_data


if __name__ == "__main__":
    run_gap_analysis()
