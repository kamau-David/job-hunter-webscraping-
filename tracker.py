"""
tracker.py

A tiny CSV-backed tracking sheet so you can see, at a glance, every
job the pipeline has found and generated materials for, plus your
own manual "applied / status" notes.

Columns: id, date_found, source, title, company, location, score,
         url, materials_folder, status
"""

from __future__ import annotations

import csv
import os
from datetime import date
from typing import Any

FIELDNAMES = [
    "id", "date_found", "source", "title", "company", "location",
    "score", "url", "materials_folder", "status",
]


def load_existing_ids(csv_path: str) -> set[str]:
    """Return the set of job ids already logged, so we never duplicate rows."""
    if not os.path.exists(csv_path):
        return set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["id"] for row in reader}


def append_entry(
    csv_path: str,
    job: dict[str, Any],
    score: int,
    materials_folder: str,
    status: str = "to_review",
) -> None:
    """Append one row. Creates the file with a header if it doesn't exist yet."""
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "id": job["id"],
            "date_found": date.today().isoformat(),
            "source": job.get("source", ""),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "score": score,
            "url": job.get("url", ""),
            "materials_folder": materials_folder,
            "status": status,
        })
