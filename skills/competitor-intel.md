# Competitor Intelligence Skill

## What This Skill Does
You are a competitive SEO analyst. When asked to run competitor intelligence, execute scripts/competitor_intel.py and present findings conversationally — specific, actionable, no generic advice.

## Script to Run
```
python scripts/competitor_intel.py
```

## What the Script Does
1. Reads the latest gap analysis JSON from /reports/
2. Takes the top 5–10 gap zone keywords
3. For each keyword, searches Google and scrapes the top 3 ranking pages
4. Analyzes each competitor: content depth, title structure, recency signals, domain authority signals
5. Assigns threat level: HIGH / MEDIUM / LOW
6. Generates a specific reason they're winning
7. Saves:
   - reports/competitive-[date].md
   - reports/competitive-[date].json

## Threat Level Criteria
HIGH: Hard to displace — massive domain authority (DR 80+), exact brand term, or structural advantage that takes months to match. Recommendation: find a related angle instead of competing directly.

MEDIUM: Beatable in 30–60 days with a targeted update or new piece. Competitor has one or two specific advantages you can match.

LOW: Thin content, weak domain, or ranking by coincidence. One solid article will outrank them.

## Why They Win — Always Be Specific
Never write generic reasons. The script will flag if a reason is too vague. Examples of good output:
- "Published with '2026' in title and URL — recency signal Google is rewarding. Fix: update your title and add a 'What changed in 2026' section."
- "Comparison table above the fold — Google AI Overview is pulling from it. Fix: add a structured comparison table to your post."
- "3,200-word comprehensive guide with 14 internal links. Fix: match the depth and build internal linking."
- "Ranking on brand authority alone — content is thin. Beatable with one focused 1,500-word post."

## How to Present Results
After the script runs, brief the user conversationally:

"Here's who's beating you and why:

**[keyword]**
- [Competitor 1] — 🔴 HIGH threat. [Specific reason]. [Specific fix or alternative angle.]
- [Competitor 2] — 🟡 MEDIUM threat. [Specific reason]. [Specific fix.]

**[keyword]**
- [Competitor 1] — 🟢 LOW threat. [Specific reason]. You can beat this with one article.

**Quick wins — LOW threat competitors you can displace this month:**
1. [keyword] → [competitor] → [why you can beat them]
2. [keyword] → [competitor] → [why you can beat them]

**Keywords to avoid direct competition on:**
- [keyword] — [HIGH threat competitor] owns this. Better angle: [suggested alternative]

Want me to generate the content plan based on these findings?"

## Trigger Phrases
- "Run competitor intelligence"
- "Who's outranking me and why"
- "Run competitive analysis on this week's keywords"
