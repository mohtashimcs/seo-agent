#!/usr/bin/env python3
"""
write_article.py — Article prep and QA for a target keyword.

  python scripts/write_article.py --keyword "buy tradelines"
      Builds a research brief (plan entry, top-10 SERP if DataForSEO creds are
      set, brand-voice rules) and saves it to drafts/[slug]-[date].brief.md.
      The article itself is written by Claude from that brief.

  python scripts/write_article.py --keyword "buy tradelines" --check drafts/buy-tradelines-2026-10-29.md
      Lints a draft against the brand-voice hard rules and the
      "Only You Could Write This" check. Exits 1 if anything fails.
"""

import re
import sys
import json
import base64
import argparse
import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Phrases brand-voice.md section 9 forbids (or that need review when used).
BANNED = [
    (r"\bskyrocket", "hype word"),
    (r"\bmassive\b", "hype word"),
    (r"\bsecret\b", "hype word"),
    (r"\bhack\b", "hype word"),
    (r"\bloophole", "hype word"),
    (r"guaranteed approval", "approval promise"),
    (r"\b(boost|raise|increase|add)\w*\s+(your\s+)?(score\s+)?(by\s+)?\d+\s*(\+\s*)?points", "score promise"),
    (r"\b700\+", "score range"),
    (r"only \w+ left", "manufactured urgency"),
    (r"act now|buy before it'?s gone|limited time", "manufactured urgency"),
    (r"our team of experts", "faceless voice"),
    (r"instantly appear", "avoid term"),
    (r"credit boost package", "avoid term"),
    (r"highest .* in the industry", "unsupported comparative claim"),
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def latest_plan_entry(keyword):
    plans = sorted(Path("reports").glob("content-plan-*.json"), reverse=True)
    for p in plans:
        data = json.loads(p.read_text())
        for a in data.get("articles", []):
            if a["keyword"].lower() == keyword.lower():
                return a
    return None


def fetch_serp(keyword):
    login, pwd = os.getenv("DATAFORSEO_LOGIN"), os.getenv("DATAFORSEO_PASSWORD")
    if not (login and pwd):
        return None
    token = base64.b64encode(f"{login}:{pwd}".encode()).decode()
    resp = requests.post(
        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
        headers={"Authorization": f"Basic {token}"},
        json=[{"keyword": keyword, "location_code": 2840, "language_code": "en", "depth": 10}],
        timeout=60,
    )
    resp.raise_for_status()
    items = resp.json()["tasks"][0]["result"][0]["items"]
    return [
        {"rank": i["rank_absolute"], "domain": i.get("domain"), "title": i.get("title"), "url": i.get("url")}
        for i in items if i.get("type") == "organic"
    ][:10]


def build_brief(keyword):
    entry = latest_plan_entry(keyword)
    serp = fetch_serp(keyword)
    today = datetime.date.today().isoformat()

    lines = [f"# Research Brief — {keyword}", f"**Date:** {today}", ""]
    if entry:
        lines += [
            "## Plan entry",
            f"- Title: {entry['title']}",
            f"- Priority: {entry['priority']} | Intent: {entry['intent']} | Position: {entry['current_position']}",
            f"- Brief: {entry['brief']}",
            "",
        ]
    else:
        lines += ["## Plan entry", "_Keyword not found in the latest content plan._", ""]

    lines.append("## Top 10 SERP")
    if serp:
        lines += [f"{r['rank']}. {r['title']} — {r['domain']} ({r['url']})" for r in serp]
    else:
        lines.append("_Skipped: set DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in .env to pull live results._")

    lines += [
        "",
        "## Before drafting",
        "- Read brand-voice.md sections 2, 3, 6, 9, 10.",
        "- Put limitations near the top; explain mechanism before benefit.",
        "- No score promises, CPN promotion, urgency, or named competitors.",
        "",
        "## Before saving",
        f"- Run: python scripts/write_article.py --keyword \"{keyword}\" --check <draft>",
    ]

    out = Path("drafts") / f"{slugify(keyword)}-{today}.brief.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"Saved {out}")


def check_draft(path):
    text = Path(path).read_text()
    body = text.split("### Pre-publication notes")[0]
    problems = []

    for pattern, label in BANNED:
        for m in re.finditer(pattern, body, re.IGNORECASE):
            # Quoted phrases are red-flag examples ("Add 100 points"), not claims.
            before = body[body.rfind("\n", 0, m.start()) + 1 : m.start()]
            if before.count('"') % 2 == 1 or before.count("“") > before.count("”"):
                continue
            line_no = body[: m.start()].count("\n") + 1
            problems.append(f"line {line_no}: {label} — “{m.group(0)}”")

    checks = {
        "customer-experience insight (named staff / Raleigh office)": r"Matt|Kathleen|Raleigh",
        "a position competitors don't hold (limits stated / details shown before payment)": r"before you (pay|buy)|before payment|may not help|won't help|unlikely to help",
        "written-guarantee or no-score-promise language": r"guarantee|don't guess|do not guarantee",
    }
    for label, pattern in checks.items():
        if not re.search(pattern, body, re.IGNORECASE):
            problems.append(f"'Only You Could Write This' check failed: missing {label}")

    if problems:
        print(f"FAIL {path}")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"PASS {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--check", metavar="DRAFT", help="lint an existing draft instead of building a brief")
    args = ap.parse_args()
    if args.check:
        check_draft(args.check)
    else:
        build_brief(args.keyword)


if __name__ == "__main__":
    main()
