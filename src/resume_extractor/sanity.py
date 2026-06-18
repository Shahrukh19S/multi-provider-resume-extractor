"""Milestone 1 sanity check: confirm keys load from .env and Gemini responds.

Mirrors SETUP.md §6 (free-tier stack) — a one-line "hello" call to the PRIMARY
provider, Google Gemini, through the official google-genai SDK. Extraction wiring
(instructor + native structured outputs) arrives in Milestone 2; this is purely a
connectivity/credentials smoke test.

Run it directly:  uv run python -m resume_extractor.sanity
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .config import GEMINI_MODEL, TEMPERATURE


def hello_gemini() -> str:
    """Send a one-line prompt to Gemini and return its text reply.

    Raises RuntimeError if GEMINI_API_KEY is not present after loading .env.
    """
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to .env (see .env.example)."
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with exactly: hello from gemini",
        config=types.GenerateContentConfig(temperature=TEMPERATURE),
    )
    return (response.text or "").strip()


def main() -> None:
    print(f"Calling {GEMINI_MODEL} ...")
    print(hello_gemini())


if __name__ == "__main__":
    main()
