"""Enable `python -m resume_extractor ...` as a CLI entry point."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
