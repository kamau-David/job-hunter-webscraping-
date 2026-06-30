"""
main.py

Job Hunter — finds jobs matching your profile, generates a tailored
resume + cover letter + notes for each, and logs everything to a
tracking CSV. You only need to review and hit apply.

Usage:
    python main.py                      # run with defaults
    python main.py --limit 5            # only process the top 5 matches
    python main.py --no-ai              # use offline templates, skip Claude API
    python main.py --profile my.json    # use a different profile file

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="sk-ant-..."   # skip this if using --no-ai
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from job_sources import fetch_all_jobs
from matcher import rank_jobs
from tracker import load_existing_ids, append_entry
import generator as gen

OUTPUT_DIR = "output"
TRACKER_CSV = os.path.join(OUTPUT_DIR, "tracker.csv")


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:60]


def save_materials(job: dict, materials: dict[str, str]) -> str:
    folder_name = f"{slugify(job.get('company', 'company'))}_{slugify(job.get('title', 'role'))}"
    folder_path = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, "resume.md"), "w", encoding="utf-8") as f:
        f.write(materials["resume"])
    with open(os.path.join(folder_path, "cover_letter.md"), "w", encoding="utf-8") as f:
        f.write(materials["cover_letter"])
    with open(os.path.join(folder_path, "notes.md"), "w", encoding="utf-8") as f:
        f.write(
            f"# {job.get('title')} @ {job.get('company')}\n\n"
            f"Source: {job.get('source')}\n"
            f"URL: {job.get('url')}\n\n"
            f"{materials['notes']}\n"
        )
    return folder_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated job-hunt pipeline.")
    parser.add_argument("--profile", default="profile.json", help="Path to profile JSON.")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs to generate materials for.")
    parser.add_argument("--no-ai", action="store_true", help="Skip Claude API, use offline templates.")
    args = parser.parse_args()

    if not os.path.exists(args.profile):
        sys.exit(f"Profile file not found: {args.profile}")
    with open(args.profile, encoding="utf-8") as f:
        profile = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Fetching jobs from RemoteOK, Arbeitnow, and We Work Remotely...")
    jobs = fetch_all_jobs()

    print("Scoring jobs against your profile...")
    ranked = rank_jobs(jobs, profile)
    print(f"{len(ranked)} jobs qualify (score >= {profile.get('min_score_to_apply', 1)}).")

    already_seen = load_existing_ids(TRACKER_CSV)
    new_ranked = [r for r in ranked if r.job["id"] not in already_seen]
    print(f"{len(new_ranked)} of those are new (not already tracked).")

    generator = None if args.no_ai else gen.ApplicationGenerator()

    processed = 0
    for scored in new_ranked:
        if processed >= args.limit:
            break
        job = scored.job
        print(f"\n-> [{scored.score}] {job['title']} @ {job['company']} ({job['source']})")

        try:
            if generator is not None:
                materials = generator.generate_all(job, profile)
            else:
                materials = gen.template_fallback(job, profile)
        except RuntimeError as exc:
            print(f"   AI generation unavailable ({exc}). Falling back to template.")
            materials = gen.template_fallback(job, profile)

        folder = save_materials(job, materials)
        append_entry(TRACKER_CSV, job, scored.score, folder)
        print(f"   Saved materials to: {folder}")
        processed += 1

    print(f"\nDone. {processed} application package(s) generated.")
    print(f"Tracking sheet: {TRACKER_CSV}")


if __name__ == "__main__":
    main()
