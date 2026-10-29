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
- Purpose: Finding the **minimum** salary for a given role. Do not infer a visa subclass, employer, internal comparator, qualifications or experience history.

If a title has materially different interpretations, identify the most likely one and make the assumption visible. For genuinely different occupations, provide separately sourced scenarios instead of blending their salaries. Do not block on an optional location or experience question. If no job name can be identified at all, ask for it.

## Temp and output conventions
- Use `tmp/intermediate/` for intermediate files
- Write final artifacts under `output/`
- Output: a complete Word report file, in the user's language. Follow any requested file format instead. keep the report's sources usable outside the chat.

## Research workflow

### 1. Define a comparison cohort

Briefly describe the likely duties and seniority. Identify close title synonyms and a relevant occupation profile. Classification codes are optional; if used, verify the classification and edition. National occupation medians can cover a broader group than the requested job and are contextual evidence unless the match is close.

### 2. Retrieve current public evidence
Browse on every run. Start with the original publisher and open the actual page, advertisement, table or PDF that contains the figures. Search results and locate evidence; snippets alone do not establish verified pay. Record the access date separately from the data reference period or publication date.

#### 2.1 Find Industry and Occupational Awards from Fair Work
- Use the `australian-minimum-pay` skill to find a minimum annual base salary for the occupation. If no award is found, report the missing award in the final output and skip to the next step to find multiple salary surveys.

#### 2.2 Collect Multiple Salary Surveys
- Collect at least three reputable salary survey, guide, or review that include the occupation with given conditions(experience level, location, etc.). Prefer surveys with a clear methodology, sample size, and date. Use the most recent edition available. 
- Surveys should come from different platforms. Examples of reputable salary surveys include Hays Salary Guide, Robert Half Salary Guide, Michael Page Salary Tool, and other publicly available salary guides. Avoid using self-reported aggregator data as the primary source.

#### 2.3 Collect Job Advertisements
Aim for several distinct employers' recent salary-disclosed advertisements (at least 10). Prefer ads from the last six months and the newest suitable survey. Do not estimate historical data forward using an invented growth rate.

Useful public starting points:

| Source | Use | Limitation |
| --- | --- | --- |
| [Jobs and Skills Australia](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles) | Occupation earnings and role context | Check occupation aggregation, employee population, earnings definition and reference period. |
| [ABS Employee Earnings and Hours](https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/employee-earnings-and-hours-australia/latest-release) | Official earnings statistics | Match full-time/part-time and ordinary/total earnings; do not treat a broad average as a precise job rate. |
| [SEEK job advertisements](https://www.seek.com.au/) and employers' public careers pages | Actual advertised salary ranges and role requirements | Confirm disclosed pay, location, hours, seniority and package wording. Deduplicate reposts. |
| [INDEED job advertisements](https://www.indeed.com.au/)| Actual advertised salary ranges and role requirements | Confirm disclosed pay, location, hours, seniority and package wording. Deduplicate reposts. |
| [LINKEDIN job advertisements](https://www.linkedin.com/jobs/view/)| Actual advertised salary ranges and role requirements | Confirm disclosed pay, location, hours, seniority and package wording. Deduplicate reposts. |

Use first-party data, reputable remuneration surveys and original job ads. Aggregator self-reports can supplement, but should not dominate the recommendation. A republished ABS/JSA figure is one underlying source, not independent corroboration. For SEEK and INDEED salary summaries, inspect the pay-basis caveat instead of assuming all entries exclude super.

When possible, collect two to three job ads from different job ad plaforms. 

When a site is blocked, use another public source or an accessible original document. Do not bypass access controls. Label inaccessible or snippet-only evidence as unverified and exclude it from calculation. If live research is unavailable, report that limitation and any verified dated evidence; never invent a current salary range to satisfy the output format.

### 3. Build an evidence register for Job Advertisements and Salary Surveys

For each source retain: source ID, publisher and page title, direct URL, access date, publication/data period, occupation and location, duties/seniority match, employment type/hours, original amount and unit, super/package treatment, normalized amount if valid, and inclusion/exclusion reason.

Separate high-match market evidence, contextual evidence, and minimum-pay evidence. Avoid broad title-only matches, duplicates from one employer, executive/entry-level extremes, contractor day rates, or commission-led earnings in a standard permanent base-salary cohort.

### 4. Normalize without hiding assumptions

- Annual salary: retain its stated basis. Weekly earnings: multiply by 52; hourly employee base pay: multiply by stated ordinary weekly hours and 52. Identify annualized estimates and cite their inputs. An annualized total-earnings statistic remains total earnings, not base pay.
- For a package consisting only of base salary plus employer super, derive base as `package / (1 + applicable super rate)` only after verifying both the package composition and the applicable rate from the ATO. Do not apply this to packages with unspecified benefits, variable pay or other components.
- Unknown super treatment, unknown hours, casual loading, contractor GST/leave differences, or unclear ordinary-versus-total earnings: show the figure separately and omit it from the base-pay calculation unless the necessary components can be verified. Do not normalize with guessed deductions.
- Do not treat an advertised range midpoint as an observed employee salary, a survey percentile as a range endpoint, or a national median as a local job offer.

### 5. Produce and check the report

Use [references/report-template.md](references/report-template.md) as the report structure. Summarize the minimum pay report from step 2.1 and put it in the report. Show the specific minimum pay amount, the source, the date, and how it was derived. 

Every salary figure must have either a direct source ID or an explicit calculation tied to source IDs. Include direct public URLs and dates in the file, not only chat-specific citation tokens. Include a full evidence table and enough arithmetic to reproduce the recommendation. Use browsing citations in the chat where supported.

Obtain the report generated from step 2.1 and attach it to end of the final report. 

Default filename: `market-salary-<job-slug>-DD-MM-YYYY.docx`, dated in the user's timezone.

Before delivery, check that citations actually contain the stated figures; units and super treatment agree; excluded evidence did not enter calculations; and defaults are disclosed. Do not present a research target as a statutory requirement or invent figures when sources are sparse.

## Migration use

Only when the user requests sponsorship, AMSR or a particular visa, read [references/migration-check.md](references/migration-check.md) and verify current rules. With only a job name, produce the public benchmark and identify missing employer-specific evidence; do not claim to have completed or certified a nomination-ready AMSR assessment. Labour market testing is a separate workflow.


## Constraints
- Never invoke user interface tools such as Microsoft Word. 
- When needed to invoke browser, invoke it in headless mode and never use a GUI. 
