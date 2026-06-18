"""Command-line entry point: extract structured data from a resume file.

Reads a resume (`.pdf` or `.txt`), extracts a schema-validated `Resume`, and prints
it as JSON. Choose a provider, or use the reliability fallback chain.

Examples:
    uv run resume-extractor resume.pdf --provider gemini     # Gemini multimodal PDF
    uv run resume-extractor resume.pdf --provider groq       # pypdf text -> Groq
    uv run resume-extractor resume.txt --provider github     # text -> GitHub Models
    uv run resume-extractor resume.pdf --fallback            # Gemini -> Groq -> GitHub
    uv run resume-extractor resume.txt --provider groq --cost  # + token usage & $ est.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .costs import cost_usd, usage_from_completion
from .extract import (
    extract_resume,
    extract_resume_from_pdf,
    extract_resume_from_pdf_text,
    extract_resume_with_usage,
)
from .ingest import pdf_to_text
from .providers import PROVIDERS
from .reliability import AllProvidersFailed, extract_with_fallback
from .schema import Resume

_EPILOG = """\
providers:
  gemini   native structured outputs + multimodal PDF (the only PDF-native path)
  groq     llama-3.3-70b-versatile  (text-only; PDFs read via pypdf)
  github   openai/gpt-4o-mini       (text-only; PDFs read via pypdf)

The output is JSON on stdout; diagnostics go to stderr.
"""


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="resume-extractor",
        description="Extract clean, schema-validated structured data from a resume.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", help="path to a resume .pdf or .txt")
    p.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default="gemini",
        help="provider to use (default: gemini)",
    )
    p.add_argument(
        "--fallback",
        action="store_true",
        help="try the provider chain gemini -> groq -> github on failure/refusal",
    )
    p.add_argument(
        "--cost",
        action="store_true",
        help="also print token usage + hypothetical $ (text path only)",
    )
    return p


def _extract_single(path: Path, provider: str, is_pdf: bool) -> Resume:
    if is_pdf:
        if PROVIDERS[provider].multimodal_pdf:
            return extract_resume_from_pdf(path)  # Gemini: PDF direct
        return extract_resume_from_pdf_text(path, provider=provider)
    return extract_resume(path.read_text(encoding="utf-8"), provider=provider)


def main(argv: list[str] | None = None) -> int:
    # Resumes carry emoji / non-Latin glyphs; force UTF-8 so Windows cp1252 won't choke.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 — best-effort; not all streams support it
        pass

    args = _build_parser().parse_args(argv)
    path = Path(args.file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    is_pdf = path.suffix.lower() == ".pdf"
    text_path_cost = (
        args.cost
        and not args.fallback
        and (not is_pdf or not PROVIDERS[args.provider].multimodal_pdf)
    )

    try:
        if args.fallback:
            source = str(path) if is_pdf else path.read_text(encoding="utf-8")
            result = extract_with_fallback(source, is_pdf=is_pdf)
            print(
                f"# served by {result.provider} "
                f"(fallbacks={result.fallback_count}, refusals={result.refusals})",
                file=sys.stderr,
            )
            resume = result.resume
        elif text_path_cost:
            text = pdf_to_text(path) if is_pdf else path.read_text(encoding="utf-8")
            resume, completion = extract_resume_with_usage(text, args.provider)
            usage = usage_from_completion(args.provider, completion)
            print(
                f"# {args.provider}: in={usage.input_tokens} out={usage.output_tokens} "
                f"~${cost_usd(args.provider, usage):.6f}/resume",
                file=sys.stderr,
            )
        else:
            if args.cost:
                print(
                    "# note: --cost is text-path only; ignored for the multimodal "
                    "PDF path",
                    file=sys.stderr,
                )
            resume = _extract_single(path, args.provider, is_pdf)
    except RuntimeError as exc:  # e.g. missing API key
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except AllProvidersFailed as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — surface a clean message, not a traceback
        print(f"error: extraction failed: {exc}", file=sys.stderr)
        return 1

    print(resume.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
