#!/usr/bin/env python3
"""
build_dashboard.py — Reads the weekly report JSON files and renders the SEO
Intelligence dashboard as one self-contained HTML file (no external requests).

The page itself lives in scripts/dashboard_template.html; this script gathers
the data (latest reports, the previous run for week-over-week deltas, and the
run history for trend lines) and embeds it as JSON.

Run after gap_finder, competitor_intel, and content_plan.
"""

import json
import datetime
from pathlib import Path

REPORTS = Path("reports")
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
DATA_MARKER = "/*__DASHBOARD_DATA__*/null"


def load_all(pattern):
    """Every report matching pattern, oldest first, as (date_str, data)."""
    out = []
    for path in sorted(REPORTS.glob(pattern)):
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        out.append((data.get("date") or path.stem[-10:], data))
    return out


def is_placeholder(results):
    """competitor_intel.py's no-API fallback emits competitor-N.com rows."""
    return bool(results) and all(r.get("competitor", "").startswith("competitor-") for r in results)


def build_payload():
    gaps = load_all("gap-analysis-*.json")
    comps = load_all("competitive-*.json")
    plans = load_all("content-plan-*.json")

    if not gaps:
        raise FileNotFoundError("No gap analysis found. Run gap_finder.py first.")

    gap_date, gap = gaps[-1]
    site = gap.get("site_url", "")

    # Only compare against runs for the same property.
    history = [(d, g) for d, g in gaps if g.get("site_url") == site]
    earlier = [(d, g) for d, g in history if d < gap_date]
    prev_date, prev = earlier[-1] if earlier else (None, None)
    prev_by_kw = {k["keyword"]: k for k in (prev or {}).get("keywords", [])}

    keywords = []
    for k in gap.get("keywords", []):
        p = prev_by_kw.get(k["keyword"])
        keywords.append({**k, "prev_position": p["position"] if p else None,
                         "prev_impressions": p["impressions"] if p else None})

    comp_date, comp = comps[-1] if comps else (None, {})
    comp_results = comp.get("results", [])
    comp_is_placeholder = is_placeholder(comp_results)
    if comp_is_placeholder:
        comp_results = []

    plan_date, plan = plans[-1] if plans else (None, {})

    return {
        "site": site.replace("sc-domain:", ""),
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "gapDate": gap_date,
        "prevDate": prev_date,
        "kpis": gap.get("kpis", {}),
        "prevKpis": (prev or {}).get("kpis"),
        "keywords": keywords,
        "history": [{"date": d, **g.get("kpis", {})} for d, g in history],
        "compDate": comp_date,
        "competitors": comp_results,
        "compPlaceholder": comp_is_placeholder,
        "failedKeywords": comp.get("failed_keywords", []),
        "quickWins": comp.get("quick_wins", []),
        "avoid": comp.get("avoid_list", []),
        "planDate": plan_date,
        "plan": plan.get("articles", []),
    }


def build_dashboard():
    print("🏗️  Building dashboard...")
    payload = build_payload()

    # "</" inside inline JSON would end the <script> block early.
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    if DATA_MARKER not in template:
        raise RuntimeError(f"{TEMPLATE.name} is missing the {DATA_MARKER} marker.")
    html = template.replace(DATA_MARKER, data_json)

    REPORTS.mkdir(exist_ok=True)
    output_path = REPORTS / f"dashboard-{datetime.date.today().isoformat()}.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"✅ Dashboard built: {output_path}")
    print("   Open in browser to view and record.")
    return output_path


if __name__ == "__main__":
    build_dashboard()
