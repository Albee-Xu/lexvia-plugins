---
name: australia-migration-watch
description: Monitor material Australian immigration-policy changes from official sources and produce verified Chinese alerts and branded weekly PDF reports. Use for visa, skilled migration, state nomination, occupation, fee, English, and processing-rule updates; not for personal eligibility advice.
---

# Australian Migration Policy Watch

Verify public Australian migration-policy changes for Chinese readers. Report only evidence-based facts; do not assess an individual's eligibility, prospects, or application strategy.

## Sources, state, and scope

- Read [official sources](references/sources.md) before monitoring. Only Australian federal, state, territory, legislative, or directly linked official materials prove a policy change.
- For recurring monitoring, follow [operations](references/operations.md). For weekly reports and PDFs, follow [weekly-report](references/weekly-report.md).
- Do not retain passports, visa numbers, ImmiAccount details, finances, or application documents.
- Monitor material changes to allocations, program openings or closures, occupation lists and assessing authorities, visa eligibility and conditions, fees, English rules, state nomination, processing priorities, legislation, and transition arrangements.

## Verification

For every candidate change, confirm the official title and URL, publication/update date, effective date or deadline, affected cohort, and a reliable before/after difference. Use one of: effective, announced-not-effective, proposed, or unverified. Do not infer a difference from a page redesign, ordinary processing-time movement, commentary, or an inaccessible source.

State nomination and a federal visa grant are separate outcomes. If a prior rule cannot be verified, say so rather than claiming a comparison.

## Outputs

### Material-change alert

Alert only for high-impact changes, or medium-impact changes with a deadline. Do not repeat an alert unless the rule, effective date, transition arrangement, or official version materially changes.

```markdown
⚠️ [Visa/state/policy]: rule update

- Status: effective / effective YYYY-MM-DD / proposed / unverified
- Published: YYYY-MM-DD; effective/deadline: YYYY-MM-DD or not stated
- Affected: visa, occupation, state program, or cohort
- Change: verified difference from the prior rule
- Check: official condition, evidence, or deadline to confirm

[Official source](URL)
```

### Weekly PDF

Include only verified changes first seen, updated, or effective in the reporting period. If no material change is verified, still produce a PDF and state in Chinese: “本周期未发现已核实的重大政策变化”. Do not fill the report with old news.

Use `references/logo template.docx` as the fixed company template. Store PDFs and state in the user's local project directory, never in the plugin directory. Render and visually inspect every PDF page, including the logo, Chinese text, page numbers, links, and overflow.

Append to Chinese reader-facing alerts and reports:

> 本内容仅整理公开政策资讯，不构成移民或法律建议；请以官方原文及个人情况为准。
