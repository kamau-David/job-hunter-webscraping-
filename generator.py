"""
generator.py

Uses the Claude API to turn (job, profile) into three ready-to-use documents:
  - a tailored resume summary/bullets
  - a cover letter
  - a short "application notes" cheat sheet (why you're a fit, what to
    highlight in the application form, likely screening questions)

Requires the ANTHROPIC_API_KEY environment variable. If it's not set,
each method raises a clear RuntimeError so main.py can fall back or
tell the user what to do, instead of failing silently.

Install: pip install anthropic
"""

from __future__ import annotations

import os
import json
from typing import Any

try:
    import anthropic
except ImportError:  # handled gracefully at call time
    anthropic = None

MODEL = "claude-sonnet-4-6"


class ApplicationGenerator:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def client(self):
        if anthropic is None:
            raise RuntimeError(
                "The 'anthropic' package isn't installed. Run: pip install anthropic"
            )
        if not self.api_key:
            raise RuntimeError(
                "No Anthropic API key found. Set the ANTHROPIC_API_KEY environment "
                "variable (get a key at https://console.anthropic.com/)."
            )
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _ask(self, system: str, user: str, max_tokens: int = 900) -> str:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()

    def generate_all(self, job: dict[str, Any], profile: dict[str, Any]) -> dict[str, str]:
        """Returns {"resume": ..., "cover_letter": ..., "notes": ...}."""
        context = (
            f"CANDIDATE BASE RESUME / BACKGROUND:\n{profile.get('base_resume', '')}\n\n"
            f"CANDIDATE SKILLS: {', '.join(profile.get('skills', []))}\n"
            f"CANDIDATE LOCATION: {profile.get('location', '')}\n\n"
            f"JOB TITLE: {job.get('title')}\n"
            f"COMPANY: {job.get('company')}\n"
            f"LOCATION: {job.get('location')}\n"
            f"JOB DESCRIPTION:\n{job.get('description', '')[:4000]}\n"
        )

        resume = self._ask(
            system=(
                "You are an expert resume writer. Given a candidate's background and a "
                "specific job description, produce a tailored resume section: a 2-3 line "
                "professional summary followed by 5-8 tailored bullet points (using the "
                "candidate's REAL experience only, reworded/reordered to match the job's "
                "priorities — never invent experience, skills, or metrics the candidate "
                "didn't have). Plain text, ready to paste."
            ),
            user=context,
        )

        cover_letter = self._ask(
            system=(
                "You are an expert cover letter writer. Write a concise, genuine, "
                "non-generic cover letter (250-350 words) for this candidate and job. "
                "No clichés like 'I am writing to express my interest'. Be specific "
                "about why this role and company fit the candidate's real background. "
                "Sign off with the candidate's name only — no placeholder brackets."
            ),
            user=context,
            max_tokens=700,
        )

        notes = self._ask(
            system=(
                "You are a job application strategist. Given this candidate and job, "
                "produce a short cheat sheet with three sections:\n"
                "1. Why you're a fit (3 bullets, honest, no exaggeration)\n"
                "2. What to emphasize in application forms/screening questions\n"
                "3. Possible gaps or things to be ready to address\n"
                "Keep it tight and practical."
            ),
            user=context,
            max_tokens=500,
        )

        return {"resume": resume, "cover_letter": cover_letter, "notes": notes}


def template_fallback(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, str]:
    """
    Offline, no-API fallback so the pipeline still produces *something*
    usable if there's no API key configured yet.
    """
    name = profile.get("name", "")
    resume = (
        f"{name}\n{profile.get('base_resume', '')}\n\n"
        f"Relevant skills for this role: "
        f"{', '.join(profile.get('skills', []))}"
    )
    cover_letter = (
        f"Dear {job.get('company', 'Hiring Team')} team,\n\n"
        f"I'm interested in the {job.get('title')} position. {profile.get('base_resume', '')}\n\n"
        f"I'd welcome the chance to discuss how my background fits this role.\n\n"
        f"Best regards,\n{name}"
    )
    notes = (
        f"Matched job: {job.get('title')} at {job.get('company')}.\n"
        f"Review the job description and manually tailor the above before sending — "
        f"this is a template fallback (no ANTHROPIC_API_KEY configured)."
    )
    return {"resume": resume, "cover_letter": cover_letter, "notes": notes}
