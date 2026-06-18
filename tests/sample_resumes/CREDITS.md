# Sample resume credits & licenses

Every resume used in this project is a **public university template, an open-source
résumé-template example, or a synthetic resume generated for this project.** None of
them is a real individual's private data. Identities shown in third-party templates
are either fictional (university examples) or the template authors' own
publicly-published demo résumés.

Licenses were verified against each source repository on **2026-06-18**.

## PDF samples — `tests/sample_resumes/`

| File | Source | What it is | License / terms |
|---|---|---|---|
| `clean_resumes_sample2.pdf` | [University of Illinois Career Center — sample resumes](https://www.careercenter.illinois.edu/sites/default/files/2023-03/Sample%20Resumes-Handout.pdf) | "Mary Smith" — a **fictional** single-column example resume from a public career-center handout | © University of Illinois; public educational handout, fictional example. Included as a benchmark fixture with attribution. |
| `clean_resumes_sample3.pdf` | [University of Florida Career Center — Resume Examples](https://career.ufl.edu/wp-content/uploads/2023/07/Resume-Examples-Updated.pdf) | A 17-page handout of **fictional** example resumes across majors | © University of Florida; public educational handout, fictional examples. Included as a benchmark fixture with attribution. |
| `colored_iconfonts_resume_sample1.pdf` | [Awesome-CV by posquit0](https://github.com/posquit0/Awesome-CV) | The colored / icon-font designed résumé template (author's demo, "Byungjin Park") | **LPPL-1.3c** (LaTeX Project Public License v1.3c) — verified from the repo's `LICENCE`. |
| `multi_column_resume_sample2.pdf` | [Deedy-Resume by Debarghya Das](https://github.com/deedy/Deedy-Resume) | The asymmetric two-column résumé template (author's own demo résumé) | **Apache-2.0** — verified from the repo. |

> **License note:** Awesome-CV is **LPPL-1.3c**, *not* MIT — verified directly from
> its `LICENCE` file. The university handouts are public educational materials (not
> open-source-licensed); they are redistributed here as small benchmark fixtures with
> attribution and contain only fictional example data.

## Synthetic text resumes — `eval/text_resumes/`

`syn_a.txt` … `syn_d.txt` (with exact gold labels in `eval/gold/`) were **generated
for this project**. All names, emails, phone numbers, and employers are invented —
**no real PII**. They exist to give the accuracy eval a clean, reproducible set with
known-correct answers.
