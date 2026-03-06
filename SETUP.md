# Setup Guide

## Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

## Step 2 — Google Search Console OAuth (10 minutes)

1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Go to **APIs & Services → Library**
4. Search "Google Search Console API" → Enable it
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → OAuth client ID**
7. Application type: **Desktop app**
8. Download the JSON file → rename it `credentials.json`
9. Place `credentials.json` in the root of this project folder

## Step 3 — Set your .env file
```bash
cp .env.example .env
```
Edit `.env` and set:
- `GSC_SITE_URL` — your Search Console property URL
  - For domain properties: `sc-domain:yourdomain.com`
  - For URL-prefix properties: `https://www.yourdomain.com/`

## Step 4 — First run (triggers OAuth browser login)
```bash
python scripts/gap_finder.py
```
A browser window will open asking you to authorize with your Google account.
After authorizing, a `token.pickle` file is saved — you won't need to re-authorize.

## Step 5 — Tell Claude Code to run the workflow
Open Claude Code in this project folder and type:
```
Run this week's gap analysis
```
Claude will read skills/gap-finder.md, run the script, and brief you on findings.

## Step 6 — Run the full weekly workflow
```
Run the full weekly workflow
```
Claude will run all three scripts in sequence and build the dashboard at the end.

## Optional — DataForSEO setup
Sign up at https://dataforseo.com (pay-per-use, ~$50/month for typical usage)
Add your login and password to `.env`:
```
DATAFORSEO_LOGIN=your@email.com
DATAFORSEO_PASSWORD=yourpassword
```
This unlocks real search volume data and competitor backlink analysis.
Without it, the system uses GSC impression data as a volume proxy — still very useful.
