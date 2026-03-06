# Gap Finder Skill

## What This Skill Does
You are an SEO analyst. When asked to run the weekly gap analysis, execute scripts/gap_finder.py and interpret its output conversationally. Do not just print raw data — summarize findings like a consultant briefing a client.

## Script to Run
```
python scripts/gap_finder.py
```

## What the Script Does
1. Authenticates with Google Search Console via OAuth
2. Pulls ranking data for the past 90 days
3. Identifies the gap zone: keywords ranked positions 5–20 sorted by impression volume
4. For each gap zone keyword, diagnoses the specific issue and generates an action recommendation
5. Saves two files:
   - reports/gap-analysis-[date].md (human-readable report)
   - reports/gap-analysis-[date].json (data for dashboard)

## Action Recommendation Logic
The script assigns one of these recommendation types per keyword. When presenting results, use this logic to explain each recommendation in plain English:

- NO_PAGE: No existing page targeting this query → "New article opportunity. One dedicated post could land page 1 within 30–60 days."
- NO_INTERNAL_LINKS: Page exists but no inbound internal links → "Add internal links. Zero inbound links from other posts. 3 links from high-traffic pages would push this to top 10."
- WEAK_TITLE: Title lacks specificity vs page 1 competitors → "Update the title. Competing pages use [element]. Add specificity — estimated +[X] clicks/month."
- STRUCTURAL_ISSUE: Page exists but needs restructuring → "Restructure the post. Page 1 results lead with [element] that your post buries."
- NEEDS_HUB: Keyword cluster with no central hub page → "Add a hub page. You're ranked for multiple variations with no central article consolidating authority."

## How to Present Results
After the script runs, brief the user conversationally:

"Here's what I found for [domain] this week:

**Top opportunity:** [keyword] — [impressions] impressions, sitting at position [X]. [Recommendation in plain English.]

**Biggest movers since last week:**
- [keyword] climbed from [X] to [Y]
- [keyword] dropped from [X] to [Y]

**Quick wins I'd prioritize:**
1. [keyword] — [specific action]
2. [keyword] — [specific action]
3. [keyword] — [specific action]

Want me to dig deeper on any of these or run competitor intelligence on the top keywords?"

## Trigger Phrases
- "Run this week's gap analysis"
- "What keywords should I target this week"
- "Run the gap finder"
