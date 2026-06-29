"""
matcher.py

Scores each job against the user's profile.json so we only spend
API calls / effort generating materials for jobs worth applying to.

Score logic (simple and transparent on purpose — easy to tweak):
    +2  for each must_have_keyword found       (missing ALL of them -> disqualified)
    +1  for each nice_to_have_keyword found
    +1  if a target_title is a substring of the job title
    -3  for each exclude_keyword found          (usually disqualifies on its own)
    -2  if remote_only is true and the job isn't remote
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoredJob:
    job: dict[str, Any]
    score: int
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def qualifies(self) -> bool:
        return self.score >= 0  # disqualification is handled via a large negative score


def _haystack(job: dict[str, Any]) -> str:
    """Combine the searchable text fields of a job into one lowercase string."""
    parts = [
        job.get("title", ""),
        job.get("description", ""),
        " ".join(job.get("tags", [])),
    ]
    return " ".join(parts).lower()


def score_job(job: dict[str, Any], profile: dict[str, Any]) -> ScoredJob:
    text = _haystack(job)
    score = 0
    matched: list[str] = []

    must_have = [k.lower() for k in profile.get("must_have_keywords", [])]
    if must_have and not any(k in text for k in must_have):
        return ScoredJob(job=job, score=-999, matched_keywords=[])

    for kw in must_have:
        if kw in text:
            score += 2
            matched.append(kw)

    for kw in profile.get("nice_to_have_keywords", []):
        if kw.lower() in text:
            score += 1
            matched.append(kw)

    for title in profile.get("target_titles", []):
        if title.lower() in job.get("title", "").lower():
            score += 1
            matched.append(f"title:{title}")

    for kw in profile.get("exclude_keywords", []):
        if kw.lower() in text:
            score -= 3

    if profile.get("remote_only") and not job.get("remote", False):
        score -= 2

    return ScoredJob(job=job, score=score, matched_keywords=matched)


def rank_jobs(jobs: list[dict[str, Any]], profile: dict[str, Any]) -> list[ScoredJob]:
    """Score every job, drop disqualified/low ones, sort best-first."""
    min_score = profile.get("min_score_to_apply", 1)
    scored = [score_job(j, profile) for j in jobs]
    qualifying = [s for s in scored if s.qualifies and s.score >= min_score]
    qualifying.sort(key=lambda s: s.score, reverse=True)
    return qualifying
