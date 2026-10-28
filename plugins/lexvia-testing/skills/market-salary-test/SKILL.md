---
name: market-salary-test
description: "Research Australian market salaries from a job title and produce a dated report recommending a gross annual base salary range and target, with traceable numerical sources. Use for market salary tests, labour salary tests, salary benchmarking, hiring offers, or pay reviews in Australia. Can support preliminary AMSR research for employer-sponsored visas; does not perform labour market testing."
---

# Australian Market Salary Test

## Overview
Turn a job name into a researched salary recommendation. The only required user input is the job name. Produce the report, rather than returning a research plan or asking the user to collect evidence.

## Input and defaults

Use explicit details in the request or relevant visible context. Otherwise proceed with these disclosed assumptions:

- Geography: Australia-wide. Do not silently substitute the user's home city. Use geographically broad evidence and explain any concentration in particular cities.
- Role: the ordinary interpretation of the title, at a competent established level, preserving words such as junior, senior, apprentice, regional, or manager.
- Employment: permanent full-time employee; use 38 ordinary hours per week as an analytical assumption only where the occupation's conditions do not establish another basis.
- Pay: AUD gross annual base salary before tax, excluding employer superannuation, variable bonuses, commissions, overtime and non-cash benefits. List those separately when relevant.
- Purpose: general salary benchmarking. Do not infer a visa subclass, employer, internal comparator, qualifications or experience history.

If a title has materially different interpretations, identify the most likely one and make the assumption visible. For genuinely different occupations, provide separately sourced scenarios instead of blending their salaries. Do not block on an optional location or experience question. If no job name can be identified at all, ask for it.

## Temp and output conventions
- Use `tmp/intermediate/` for intermediate files
- Write final artifacts under `output/`
- Output: a complete Word report file with a brief chat summary, in the user's language. Follow any requested file format instead. keep the report's sources usable outside the chat.

## Research workflow

### 1. Define a comparison cohort

Briefly describe the likely duties and seniority. Identify close title synonyms and a relevant occupation profile. Classification codes are optional; if used, verify the classification and edition. National occupation medians can cover a broader group than the requested job and are contextual evidence unless the match is close.

### 2. Retrieve current public evidence

Browse on every run. Start with the original publisher and open the actual page, advertisement, table or PDF that contains the figures. Search results and locate evidence; snippets alone do not establish verified pay. Record the access date separately from the data reference period or publication date.

Aim for several distinct employers' recent salary-disclosed advertisements (at least 4) and an independent salary guide or government dataset. This is a practical target, not a statutory sample size. Use what is available and explain shortfalls. Prefer ads from the last six months and the newest suitable survey; older government data may be useful with its reference period disclosed. Do not estimate historical data forward using an invented growth rate.

Useful public starting points:

| Source | Use | Limitation |
| --- | --- | --- |
| [Jobs and Skills Australia](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles) | Occupation earnings and role context | Check occupation aggregation, employee population, earnings definition and reference period. |
| [ABS Employee Earnings and Hours](https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/employee-earnings-and-hours-australia/latest-release) | Official earnings statistics | Match full-time/part-time and ordinary/total earnings; do not treat a broad average as a precise job rate. |
| [SEEK job advertisements](https://www.seek.com.au/) and employers' public careers pages | Actual advertised salary ranges and role requirements | Confirm disclosed pay, location, hours, seniority and package wording. Deduplicate reposts. |
| [INDEED job advertisements](https://www.indeed.com.au/)| Actual advertised salary ranges and role requirements | Confirm disclosed pay, location, hours, seniority and package wording. Deduplicate reposts. |
| [Hays Salary Guide](https://www.hays.com.au/salary-guide), [Robert Half Salary Guide](https://www.roberthalf.com/au/en/insights/salary-guide), [Michael Page salary tool](https://www.michaelpage.com.au/salary-comparison-tool) | Role and location benchmarks | Verify edition, salary basis and methodology. Prefer publicly accessible tables or calculators; do not submit personal details to download a guide. |
| [Fair Work Pay Calculator](https://calculate.fairwork.gov.au/) and [agreement search guidance](https://www.fairwork.gov.au/employment-conditions/agreements/finding-an-agreement) | Minimum pay and conditions | A legal floor is different from the observed market distribution. Check coverage and classification before asserting a minimum. |

Use first-party data, reputable remuneration surveys and original job ads. Aggregator self-reports can supplement, but should not dominate the recommendation. A republished ABS/JSA figure is one underlying source, not independent corroboration. For SEEK and INDEED salary summaries, inspect the pay-basis caveat instead of assuming all entries exclude super.

When a site is blocked, use another public source or an accessible original document. Do not bypass access controls. Label inaccessible or snippet-only evidence as unverified and exclude it from calculation. If live research is unavailable, report that limitation and any verified dated evidence; never invent a current salary range to satisfy the output format.

### 3. Build an evidence register

For each source retain: source ID, publisher and page title, direct URL, access date, publication/data period, occupation and location, duties/seniority match, employment type/hours, original amount and unit, super/package treatment, normalized amount if valid, and inclusion/exclusion reason.

Separate high-match market evidence, contextual evidence, and minimum-pay evidence. Avoid broad title-only matches, duplicates from one employer, executive/entry-level extremes, contractor day rates, or commission-led earnings in a standard permanent base-salary cohort.

### 4. Normalize without hiding assumptions

- Annual salary: retain its stated basis. Weekly earnings: multiply by 52; hourly employee base pay: multiply by stated ordinary weekly hours and 52. Identify annualized estimates and cite their inputs. An annualized total-earnings statistic remains total earnings, not base pay.
- For a package consisting only of base salary plus employer super, derive base as `package / (1 + applicable super rate)` only after verifying both the package composition and the applicable rate from the ATO. Do not apply this to packages with unspecified benefits, variable pay or other components.
- Unknown super treatment, unknown hours, casual loading, contractor GST/leave differences, or unclear ordinary-versus-total earnings: show the figure separately and omit it from the base-pay calculation unless the necessary components can be verified. Do not normalize with guessed deductions.
- Do not treat an advertised range midpoint as an observed employee salary, a survey percentile as a range endpoint, or a national median as a local job offer.

### 5. Derive the recommendation

Use the closest comparable evidence as the primary cohort. Show how its observed ranges and typical figures support the recommended lower bound, upper bound and target. Keep the target inside the recommended range.

For a coherent group of at least three distinct, comparable salary-range ads, the median of the lower endpoints and median of the upper endpoints can provide a useful central advertised band; the median of the ad midpoints can provide a tentative target. Label these as calculated summaries of the sampled advertisements, not population percentiles. Cross-check with a suitable survey and disclose the number of underlying ads. Do not give the ad sample more weight merely because it has more rows than a representative survey.

If evidence formats, seniority or locations differ substantially, keep separate cohorts and justify the selected range from the strongest evidence. Do not mechanically average unrelated datasets, pool entry-level with senior roles, use the global minimum/maximum as the suggested band, or add a made-up percentage around a single median. Describe source disagreement and its likely cause. Avoid arbitrary city adjustments.

Distinguish the observed market range from a compliant hiring recommendation. Check the likely award/agreement as far as the title permits; coverage depends on duties and the employer's industry. If no classification can be verified, state that the minimum-pay check is unresolved. Do not describe a benchmark as a compliance pass or disguise a legal/visa threshold as observed market pay.

Use whole-dollar precision for auditable source calculations; round recommendations to a sensible level, usually AUD 1,000, without rounding a confirmed legal minimum down. Express confidence as high/moderate/low with concrete reasons, not an invented numerical confidence interval. If only one defensible figure exists, label it as a reference point and state that a supported range could not be established. With no usable figures, say evidence is insufficient.

### 6. Produce and check the report

Use [references/report-template.md](references/report-template.md) as the report structure. Every salary figure must have either a direct source ID or an explicit calculation tied to source IDs. Include direct public URLs and dates in the file, not only chat-specific citation tokens. Include a full evidence table and enough arithmetic to reproduce the recommendation. Use browsing citations in the chat where supported.

Default filename: `market-salary-<job-slug>-DD-MM-YYYY.docx`, dated in the user's timezone. Open with the recommended annual base-pay range and target, pay basis, geography and confidence; follow with assumptions, evidence and reasoning. Keep the key conclusions readable before the evidence appendix.

Before delivery, check that citations actually contain the stated figures; units and super treatment agree; the target lies inside the range; excluded evidence did not enter calculations; and defaults are disclosed. Do not present a research target as a statutory requirement or invent figures when sources are sparse.

## Migration use

Only when the user requests sponsorship, AMSR or a particular visa, read [references/migration-check.md](references/migration-check.md) and verify current rules. With only a job name, produce the public benchmark and identify missing employer-specific evidence; do not claim to have completed or certified a nomination-ready AMSR assessment. Labour market testing is a separate workflow.


## Constraints
- Never invoke user interface tools such as Microsoft Word. 
- When needed to invoke browser, invoke it in headless mode and never use a GUI. 
