# Job Hunter

An automated pipeline that finds jobs matching your profile, and generates
a tailored resume, cover letter, and application notes for each one — so
your job is just to review and click apply.

## How it works

1. **`job_sources.py`** pulls fresh listings from three free, public,
   scraping-friendly sources: RemoteOK, Arbeitnow, and We Work Remotely.
2. **`matcher.py`** scores every job against your `profile.json` (skills,
   keywords, excluded terms) and keeps only the ones worth your time.
3. **`generator.py`** sends each qualifying job + your base resume to the
   Claude API, which writes a tailored resume section, a real cover
   letter, and a short "why you fit / what to emphasize" cheat sheet.
4. **`tracker.py`** logs every job to `output/tracker.csv` so nothing
   gets generated twice and you can track application status yourself.
5. **`main.py`** runs the whole pipeline end to end.

## Setup

```bash
cd job_hunter
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Get a Claude API key at https://console.anthropic.com/ and set it:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # Windows (PowerShell): $env:ANTHROPIC_API_KEY="sk-ant-..."
```

## Customize your profile

Edit `profile.json`:
- `base_resume` — a paragraph describing your real background (don't
  embellish — the AI will tailor wording/emphasis, not invent facts)
- `skills`, `target_titles`, `must_have_keywords`, `nice_to_have_keywords`
- `exclude_keywords` — e.g. "senior", "5+ years" if you want to skip those
- `remote_only` — set to `false` if you also want local/hybrid Kenyan jobs
  (note: only Arbeitnow returns non-remote roles currently)

## Run it

```bash
python main.py                 # generate materials for up to 10 new matches
python main.py --limit 3       # just the top 3
python main.py --no-ai         # skip the API, use simple offline templates
```

Each match gets a folder under `output/<company>_<title>/` containing:
- `resume.md`
- `cover_letter.md`
- `notes.md`

And a row is added to `output/tracker.csv` with the job's score, link,
and a `status` column you can hand-edit (`to_review`, `applied`,
`rejected`, `interview`, etc.).

## Notes & things to extend next

- **Rate/cost**: each job costs 3 Claude API calls. Start with `--limit 3`
  while testing.
- **Add sources**: Adzuna and Jooble have free tiers but need an API key —
  easy to add another `fetch_x()` function in `job_sources.py` following
  the same normalized dict shape.
- **Never auto-apply**: this tool deliberately stops at "materials ready" —
  you review and submit. Some job boards' ToS forbid automated
  applications, and a human sanity-check on AI-written cover letters is
  always worth it.
- **Good next Python exercises**: add pagination to the Arbeitnow fetcher,
  add a `--keywords` CLI override, or swap the CSV tracker for SQLite.
