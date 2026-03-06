#!/usr/bin/env python3
"""
build_dashboard.py — Reads all reports JSON files and renders the SEO Intelligence
HTML dashboard. Run this after gap_finder, competitor_intel, and content_plan.
"""

import json
import datetime
from pathlib import Path


def get_latest_report(pattern):
    reports = sorted(Path("reports").glob(pattern), reverse=True)
    if not reports:
        return None
    with open(reports[0]) as f:
        return json.load(f)


def threat_badge(threat):
    colors = {
        "HIGH": ("rgba(248,113,113,0.1)", "#f87171", "rgba(248,113,113,0.2)"),
        "MEDIUM": ("rgba(251,191,36,0.1)", "#fbbf24", "rgba(251,191,36,0.2)"),
        "LOW": ("rgba(52,211,153,0.1)", "#34d399", "rgba(52,211,153,0.2)"),
    }
    bg, color, border = colors.get(threat, colors["MEDIUM"])
    dot_shadow = f"box-shadow: 0 0 4px {color};" if threat == "HIGH" else ""
    return f'''<span style="display:inline-flex;align-items:center;gap:5px;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:500;padding:3px 9px;border-radius:3px;background:{bg};color:{color};border:1px solid {border}"><span style="width:5px;height:5px;border-radius:50%;background:{color};{dot_shadow}display:inline-block"></span>{threat}</span>'''


def pos_color(position):
    if position is None:
        return "#6b7280"
    if position <= 8:
        return "#34d399"
    elif position <= 14:
        return "#fbbf24"
    else:
        return "#6b7280"


def build_dashboard():
    print("🏗️  Building dashboard...")

    gap = get_latest_report("gap-analysis-*.json")
    comp = get_latest_report("competitive-*.json")
    plan = get_latest_report("content-plan-*.json")

    today = datetime.date.today().strftime("%b %-d, %Y")
    site_url = gap.get("site_url", "your-site.com") if gap else "your-site.com"
    kpis = gap.get("kpis", {}) if gap else {}
    keywords = gap.get("keywords", []) if gap else []
    comp_results = comp.get("results", []) if comp else []
    articles = plan.get("articles", []) if plan else []

    # ── KPI values ────────────────────────────────────────────────────────
    total_impressions = kpis.get("total_impressions", 0)
    gap_count = kpis.get("gap_zone_count", 0)
    avg_pos = kpis.get("avg_position", 0)
    total_clicks = kpis.get("total_clicks", 0)

    impressions_fmt = f"{total_impressions/1000:.1f}K" if total_impressions >= 1000 else str(total_impressions)
    clicks_fmt = f"{total_clicks:,}"

    # ── Keyword opportunity cards HTML ────────────────────────────────────
    kw_cards_html = ""
    for kw in keywords[:6]:
        pos = kw["position"]
        color = pos_color(pos)
        kw_cards_html += f"""
        <div style="background:#131820;border:1px solid #1e2530;border-radius:8px;padding:18px 20px;cursor:pointer;transition:border-color 0.15s">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#22d3ee;margin-bottom:14px;font-weight:500">"{kw['keyword']}"</div>
          <div style="display:flex;gap:20px;margin-bottom:14px">
            <div style="flex:1">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px">Impressions</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:600;color:#e8f4fd;line-height:1">{kw['impressions']:,}</div>
            </div>
            <div style="flex:1">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px">Position</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:600;color:{color};line-height:1">{pos}</div>
            </div>
            <div style="flex:1">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px">CTR</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:600;color:#fbbf24;line-height:1">{kw['ctr']}%</div>
            </div>
          </div>
          <div style="height:1px;background:#1e2530;margin-bottom:12px"></div>
          <div style="font-size:11px;color:#4a5568;line-height:1.5">→ <span style="color:#c8d4e0">{kw['recommendation']}</span></div>
        </div>"""

    # ── Competitive table rows HTML ───────────────────────────────────────
    # Group by keyword for rowspan-like display
    seen_keywords = {}
    comp_rows_html = ""
    for r in comp_results[:12]:
        kw = r["keyword"]
        badge = threat_badge(r["threat"])
        is_first = kw not in seen_keywords
        seen_keywords[kw] = True
        kw_cell = f'<td style="font-family:\'IBM Plex Mono\',monospace;font-size:12px;color:#22d3ee;font-weight:500;padding:13px 20px;border-bottom:1px solid #1e2530">{kw}</td>' if is_first else f'<td style="padding:13px 20px;border-bottom:1px solid #1e2530"></td>'
        comp_rows_html += f"""
        <tr>
          {kw_cell}
          <td style="font-size:12px;color:#c8d4e0;padding:13px 20px;border-bottom:1px solid #1e2530">{r['competitor']}</td>
          <td style="padding:13px 20px;border-bottom:1px solid #1e2530">{badge}</td>
          <td style="font-size:11px;color:#4a5568;padding:13px 20px;border-bottom:1px solid #1e2530;max-width:280px">{r['reason']}</td>
        </tr>"""

    # ── Content plan cards HTML ───────────────────────────────────────────
    content_cards_html = ""
    priority_colors = {"P1": ("#f87171", "rgba(248,113,113,0.12)", "rgba(248,113,113,0.2)"),
                       "P2": ("#fbbf24", "rgba(251,191,36,0.12)", "rgba(251,191,36,0.2)")}
    for article in articles:
        p = article.get("priority", "P2")
        pc, pb, pbo = priority_colors.get(p, priority_colors["P2"])
        pos = article.get("current_position", 0)
        pos_c = pos_color(pos)
        content_cards_html += f"""
        <div style="background:#131820;border:1px solid #1e2530;border-radius:8px;padding:18px 20px">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px">
            <div style="font-size:12px;color:#e8f4fd;font-weight:500;line-height:1.4;flex:1;padding-right:12px">{article['title']}</div>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;padding:2px 7px;border-radius:3px;flex-shrink:0;background:{pb};color:{pc};border:1px solid {pbo}">{p}</span>
          </div>
          <div style="display:flex;gap:16px;margin-bottom:10px">
            <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px">Target Keyword</div><div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#e8f4fd;font-weight:500">{article['keyword']}</div></div>
            <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px">Est. Volume</div><div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#e8f4fd;font-weight:500">{article['estimated_volume']:,}/mo</div></div>
            <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px">Position</div><div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:{pos_c};font-weight:500">{pos}</div></div>
          </div>
          <div style="font-size:11px;color:#4a5568;font-style:italic">{article['intent']} — {article['brief'][:100]}...</div>
        </div>"""

    # ── Assemble full HTML ────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO Intelligence — {site_url}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0c0f; color:#c8d4e0; font-family:'IBM Plex Sans',sans-serif; font-size:13px; line-height:1.5; }}
  body::after {{ content:''; position:fixed; top:0; left:0; right:0; bottom:0; background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.03) 2px,rgba(0,0,0,0.03) 4px); pointer-events:none; z-index:9999; }}
  @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
  .fade {{ opacity:0; animation:fadeUp 0.4s ease forwards; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}
</style>
</head>
<body>

<!-- TOP BAR -->
<div style="background:#0f1218;border-bottom:1px solid #1e2530;padding:12px 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100">
  <div style="display:flex;align-items:center;gap:24px">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;color:#22d3ee;letter-spacing:0.12em;text-transform:uppercase">⬡ SEO Intelligence</div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#4a5568;background:#131820;border:1px solid #1e2530;padding:3px 10px;border-radius:3px">{site_url}</div>
  </div>
  <div style="display:flex;align-items:center;gap:20px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568">
    <span><span style="width:6px;height:6px;border-radius:50%;background:#34d399;display:inline-block;margin-right:6px;box-shadow:0 0 6px #34d399;animation:pulse 2s ease-in-out infinite"></span>GSC Connected</span>
    <span>Last run: {today}</span>
    <span>90-day window</span>
  </div>
</div>

<div style="max-width:1200px;margin:0 auto;padding:32px">

  <!-- KPIs -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:36px;margin-top:8px">
    {"".join([f'''<div class="fade" style="background:#131820;border:1px solid #1e2530;border-radius:8px;padding:16px 20px;position:relative;overflow:hidden;animation-delay:{d}s"><div style="position:absolute;top:0;left:0;right:0;height:2px;background:{c}"></div><div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">{l}</div><div style="font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:600;color:#e8f4fd;letter-spacing:-0.03em;line-height:1;margin-bottom:6px">{v}</div><div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#34d399">{s}</div></div>''' for l,v,s,c,d in [("Total Impressions", impressions_fmt, "↑ 90-day window", "#60a5fa", 0.05), ("Gap Zone Keywords", str(gap_count), "positions 5–20", "#34d399", 0.1), ("Avg Position", str(avg_pos), "all keywords", "#fbbf24", 0.15), ("Organic Clicks", clicks_fmt, "↑ 90-day window", "#a78bfa", 0.2)]])}
  </div>

  <!-- KEYWORD OPPORTUNITIES -->
  <div style="margin-bottom:36px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
      <div style="width:28px;height:28px;border-radius:6px;background:rgba(251,191,36,0.12);color:#fbbf24;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">◎</div>
      <div style="font-size:15px;font-weight:600;color:#e8f4fd">Keyword Opportunities</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;margin-left:auto">{gap_count} gap-zone keywords · {min(6, len(keywords))} shown · sorted by opportunity score</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
      {kw_cards_html}
    </div>
  </div>

  <!-- COMPETITIVE INTELLIGENCE -->
  <div style="margin-bottom:36px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
      <div style="width:28px;height:28px;border-radius:6px;background:rgba(248,113,113,0.12);color:#f87171;display:flex;align-items:center;justify-content:center;font-size:13px">✕</div>
      <div style="font-size:15px;font-weight:600;color:#e8f4fd">Competitive Intelligence</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;margin-left:auto">Who's Outranking You & Why</div>
    </div>
    <div style="background:#131820;border:1px solid #1e2530;border-radius:8px;overflow:hidden">
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#0f1218;border-bottom:1px solid #1e2530">
            <th style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:0.1em;padding:12px 20px;text-align:left;font-weight:400">Keyword</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:0.1em;padding:12px 20px;text-align:left;font-weight:400">Competitor</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:0.1em;padding:12px 20px;text-align:left;font-weight:400">Threat</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:0.1em;padding:12px 20px;text-align:left;font-weight:400">Why They Win</th>
          </tr>
        </thead>
        <tbody>{comp_rows_html}</tbody>
      </table>
    </div>
  </div>

  <!-- CONTENT PLAN -->
  <div style="margin-bottom:36px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
      <div style="width:28px;height:28px;border-radius:6px;background:rgba(52,211,153,0.12);color:#34d399;display:flex;align-items:center;justify-content:center;font-size:13px">✦</div>
      <div style="font-size:15px;font-weight:600;color:#e8f4fd">This Week's Content Plan</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;margin-left:auto">Generated from gap analysis · {today}</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">
      {content_cards_html}
    </div>
  </div>

</div>

<!-- FOOTER -->
<div style="border-top:1px solid #1e2530;padding:16px 32px;display:flex;align-items:center;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568">
  <span>SEO Intelligence · {site_url} · Powered by Claude Code + Google Search Console</span>
  <span>Next run scheduled: Next Monday · 09:00 AM</span>
</div>

</body>
</html>"""

    # Save dashboard
    output_path = Path("reports") / f"dashboard-{datetime.date.today().isoformat()}.html"
    Path("reports").mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"✅ Dashboard built: {output_path}")
    print(f"   Open in browser to view and record.")
    return str(output_path)


if __name__ == "__main__":
    build_dashboard()
