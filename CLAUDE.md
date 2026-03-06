# SEO Agent — mikefutia.com

## What This Project Is
An SEO intelligence system that connects to Google Search Console, identifies keyword gaps, maps competitors, and generates a weekly content plan and HTML dashboard — all from a single prompt.

## Session Start Protocol
At the start of every session:
1. Read the skill file(s) relevant to today's task
2. Read brand-voice.md before any content task
3. Check /reports/ for the most recent outputs before running downstream skills

## Skills Available
- skills/gap-finder.md — keyword discovery, gap zone analysis, action recommendations
- skills/competitor-intel.md — competitive intelligence, threat levels, why they win
- skills/brand-writer.md — content planning, article writing, brand voice

## Key Commands
- "Run this week's gap analysis" → reads skills/gap-finder.md, runs scripts/gap_finder.py
- "Run competitor intelligence" → reads skills/competitor-intel.md, runs scripts/competitor_intel.py
- "Generate this week's content plan" → reads skills/brand-writer.md, runs scripts/content_plan.py
- "Build the dashboard" → runs scripts/build_dashboard.py using this week's reports
- "Run the full weekly workflow" → runs all four in sequence, builds dashboard at the end

## File Structure
skills/             — skill instruction files (Claude reads these before acting)
scripts/            — Python scripts Claude executes to produce outputs
reports/            — weekly outputs saved as .md and .json files
drafts/             — article drafts pending review
brand-voice.md      — brand voice profile (update weekly)
.env                — API credentials (never commit this)

## API Credentials (set in .env)
GSC_CLIENT_SECRET_FILE=credentials.json   # Google OAuth client secret
GSC_SITE_URL=sc-domain:mikefutia.com      # Your Search Console property
DATAFORSEO_LOGIN=your_login               # Optional — enhances volume data
DATAFORSEO_PASSWORD=your_password         # Optional

## Output Format Rule
Every script saves two files:
1. A human-readable .md report → /reports/
2. A machine-readable .json data file → /reports/
The dashboard builder reads the .json files to render the HTML output.
