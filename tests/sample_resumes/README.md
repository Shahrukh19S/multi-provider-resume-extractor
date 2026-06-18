# sample_resumes

Drop resume **PDF** files here to exercise Milestone 3 (PDF ingestion) and, later,
the Milestone 7 eval set.

- The PDF tests in `tests/test_pdf_ingestion.py` auto-discover `*.pdf` here and
  **skip** if none are present.
- A **messy, multi-column** resume is the most useful sample — it's where the
  Gemini multimodal path is expected to beat flat `pypdf` text extraction (the M3
  trade-off recorded in `BENCHMARK.md`).

## Privacy

Real resumes contain personal data. For a **public** repo, prefer **synthetic or
redacted** resumes. By default `tests/sample_resumes/*.pdf` is git-ignored (see
`.gitignore`) so real PDFs stay local; force-add a clearly-synthetic sample if you
want one committed (`git add -f tests/sample_resumes/synthetic.pdf`).
