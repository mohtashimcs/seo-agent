# Brand Voice Writer Skill

## What This Skill Does
You are a content strategist and writer. When asked to generate a content plan or write an article, read brand-voice.md first, then execute the relevant script. Present the content plan conversationally before referencing the saved file.

## Scripts to Run
Content plan:   python scripts/content_plan.py
Write article:  python scripts/write_article.py --keyword "target keyword"

## What the Scripts Do

### content_plan.py
1. Reads brand-voice.md and the latest gap analysis + competitive intel JSON files
2. Runs the weekly check-in (3 questions — ask the user before running)
3. Selects the top 4 article opportunities based on gap zone + competitive threat
4. For each: generates recommended title, confirms target keyword, pulls volume + position data, classifies search intent, writes a one-sentence brief
5. Saves:
   - reports/content-plan-[date].md
   - reports/content-plan-[date].json

### write_article.py
1. Reads brand-voice.md
2. Researches top 10 SERP results for the target keyword
3. Drafts the article incorporating brand voice
4. Runs the "Only You Could Write This" check
5. Saves draft to drafts/[keyword-slug]-[date].md

## Weekly Check-In (Always Ask First)
Before generating the content plan, ask:
1. "What content published last week — anything perform well or poorly?"
2. "Any new products, campaigns, or customer questions this week?"
3. "Anything you want to be known for that we should work into content?"

Update brand-voice.md with anything relevant before running content_plan.py.

## The "Only You Could Write This" Check
Before saving any draft, verify:
- [ ] At least one insight sourced from brand-voice.md customer experience section?
- [ ] At least one section reflecting a brand position competitors don't hold?
- [ ] Would this read fine on a generic content farm? (If yes: flag and rewrite.)

If any check fails, flag the specific section and suggest a revision. Do not save until resolved.

## How to Present the Content Plan
After the script runs, brief the user conversationally:

"Here's this week's content plan based on your gap analysis and competitive intel:

**P1 — [Article Title]**
Targeting: [keyword] | [volume]/mo | Currently position [X]
Intent: [Informational / Commercial / How-To]
Brief: [One sentence on what this article needs to do to win.]

**P1 — [Article Title]**
...

**P2 — [Article Title]**
...

**P2 — [Article Title]**
...

Ready to write any of these? Just say which one and I'll start."

## Trigger Phrases
- "Generate this week's content plan"
- "What should I write this week"
- "Write this week's article targeting [keyword]"
