# Weekly Reports and PDFs

Use this file when a user asks for a weekly report, a weekly PDF, or scheduled reporting.

## Per-user state

Create the following automatically in the user's local project directory on first use. Do not show it to the user or require manual edits.

```text
.migration-watch/
├── monitoring-state.json
└── weekly-report-state.json
```

These files record the monitoring start time, reported item IDs, report versions, run results, and next scheduled run. They are local runtime data and are never committed with the plugin.

## Period and timing

- Use `Australia/Sydney`, including daylight saving time.
- A full reporting week is Monday 00:00:00 through Sunday 23:59:59.
- Generate the PDF at 08:00 every Monday for the immediately preceding week.
- If monitoring starts mid-week, the first report begins at the actual start time and ends that Sunday at 23:59:59. Do not present pre-start information as monitored during that period.
- All later reports use full calendar weeks.

## Content and PDF

- Include only official, verified items first seen, materially updated, or effective during the reporting period.
- Repeat an item only for a material rule, effective-date, transition, or official-version change.
- Put inaccessible or unverified items under “观察项”; do not present them as confirmed.
- Produce a PDF even if there is no verified material change.
- Use `references/logo template.docx` and write the PDF to `outputs/weekly/` in the user's project directory. Create that directory if needed.
- Name reports `澳大利亚移民政策周报_YYYY-MM-DD至YYYY-MM-DD_v{version}.pdf`.
- Save the reporting range, item IDs, path, version, and visual-review outcome in the weekly state file.

## Codex scheduled tasks

Create or update scheduled tasks only when the user explicitly requests automation. Use the same local project directory for both tasks:

1. Daily or weekday monitoring: verify official sources, update state, and notify only for an eligible immediate alert.
2. Weekly reporting: every Monday at 08:00 Sydney time, generate the previous week's PDF.

Use the local project directory rather than a separate worktree so the user's state persists across runs.
