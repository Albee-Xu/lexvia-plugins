---
name: australian-minimum-pay
description: Research Australian legal minimum wages for any profession, with optional location, experience, employer industry, duties and other conditions. Verify Fair Work award coverage and exclusions, determine the classification, download the applicable pay guide and calculate full-time minimum pay in a sourced Markdown report. Use for statutory or award minimum-pay questions, rather than market salary benchmarking.
---

# Australian Minimum Pay

Produce a researched minimum-pay report, rather than only a research plan. Use the supplied profession and optional conditions. Keep coverage, classification, workload and arithmetic traceable to current official evidence.

## Inputs and defaults

Require only the profession to begin. Use visible conversation details before asking questions.

Collect employer industry and activities, duties, location, experience and recognised service, qualifications, age where relevant, employment category, roster, assessment date and agreement status when available. Ask a small, bundled set of questions only when missing facts materially change coverage or classification; continue independent research while awaiting answers when possible.

If information remains unavailable:

- Use Australia-wide scope; do not substitute the user's home city.
- Assess full-time ordinary-time gross base pay before tax, excluding employer superannuation and separately payable extras.
- Use the current client-local date unless the user specifies a date or historical period.
- Treat an adult aged 21+ and ordinary daytime work as disclosed conditional assumptions where necessary. Do not infer age from a career label such as “junior”.
- Preserve supplied experience, including overseas experience. Do not invent years, duties, qualifications, registration or a service increment.
- Mark unknown agreement coverage and material role assumptions. Give supported conditional scenarios instead of an unconditional legal minimum when these facts matter.

## Files and browsing

Create a task-specific directory under the task workspace's `tmp/`, such as `tmp/minimum-pay-<occupation>-<run-id>/`, before saving intermediate material. Put **every intermediate file there**, including downloads, cached pages, PDF renders, screenshots, text extracts, calculation work, temporary scripts, browser profiles and download staging. Do not use the skill directory or final-output directory for intermediate material.

Generate plans, notes, extracts and reports only as Markdown. Preserve downloaded official sources unchanged in their original formats inside `tmp/`; an original source PDF is not a generated report. Keep only the completed Markdown report in the chosen final-output location, normally `output/minimum-pay-<occupation>-<location>.md`. Include the original official guide URL in it; do not copy a source PDF into `output/`.

Prefer official search/retrieval tools and direct HTTP downloads. If a browser is needed, explicitly launch it in **headless mode**, with its temporary state under `tmp/`. A hidden tab or `visible: false` alone does not establish headless mode. Do not use a browser interface that cannot meet this requirement. Use another retrieval route or report the access limitation.

## 1. Browse for the award and check exclusions

Start research on [FWO Awards](https://www.fairwork.gov.au/employment-conditions/awards), award summaries and the award finder. Search the profession, duty synonyms and employer industry. Consider industry awards first, then occupational awards where relevant.

Read the actual award's coverage clause, definitions, exclusions, classification structure and competing-coverage rules, following the official award-text link. Require both positive coverage evidence and an exclusion review. Check broader excluded categories as well as the exact title. Absence of a keyword exclusion is not proof of coverage.

Record the selected award's full name, code, supporting clauses and rejected plausible alternatives. If excluded, reject the candidate rather than selecting it for convenient rates.

Check national-system jurisdiction and any applicable registered agreement or other displacing instrument. Use location and employer context for this check; do not add a city-based wage premium without a governing provision.

Read the [FWO classification guidance](https://www.fairwork.gov.au/employment-conditions/awards/award-classifications) alongside coverage research. Use [FWO's Fair Work system guidance](https://www.fairwork.gov.au/about-us/workplace-laws/fair-work-system) when jurisdiction needs clarification.

### Alternative routes

- If no award applies, verify award-free status and use the current applicable National Minimum Wage Order/FWO wage source. Report award, award classification and award pay guide as **not applicable**; do not download an unrelated guide.
- If an enterprise agreement or state instrument applies, research that instrument and relevant statutory floors. Identify any agreement classification and wage schedule. Do not present the modern-award guide alone as the employee's actual entitlement.
- If coverage is unresolved, document the competing routes and missing facts. Do not claim a definitive classification or minimum salary.

## 2. Find the pay guide by award code and download it

For an applicable award, open the exact [FWO pay guides index](https://www.fairwork.gov.au/pay-and-wages/minimum-wages/pay-guides). Match the award code and name, then follow the advertised guide download link. Do not guess a download endpoint.

Save the unchanged guide inside the run's `tmp/` directory. If the link returns an HTML download page, follow its observed download link or redirect using direct retrieval where possible. Check the response/file signature and readability; do not label HTML as a PDF.

Record the guide's exact title, code, publication/version information, rates' commencement date, first-full-pay-period rule where applicable, download URL, local `tmp/` filename and retrieval date.

Check the official award text and current FWO notices for later or staged variations. For historical work, obtain the version applicable to the requested period. Never infer rate currency from a familiar filename or assume that every increase starts on 1 July. If downloading fails, state that clearly.

## 3. Determine the classification

Extract classification labels and pay points from the guide. Read full definitions in the award itself; the pay guide may not contain them.

Apply the five FWO stages:

1. Find the definitions.
2. Apply award-specific classification instructions.
3. Assess the whole role using duties, competence, qualifications, experience and supervision.
4. Compare the candidate with neighbouring classifications.
5. Explain the outcome and any employer notification requirement in the report; do not send it to anyone.

Map decisive requirements to supplied facts with clause references. Distinguish classification level from experience/service pay point. Apply recognised-service, progression and higher-duty provisions exactly as written. Do not convert experience into a higher level automatically, discount overseas experience without a source, or classify solely from the title. Do not invent a percentage-match scoring rule.

Explain why neighbouring levels fit less well. Keep classification provisional when material facts remain unknown.

## 4. Establish full-time workload

Read the instrument's full-time and ordinary-hours clauses. Record weekly paid ordinary hours, roster averaging and relevant day/shift conditions. Use 38 hours only when supported by the governing source, or label it as a conditional analytical assumption.

Identify unpaid breaks and separately payable hours. Do not subtract paid annual leave from a full-year base-pay conversion.

## 5. Locate and verify the wage row

Identify the applicable adult/junior/apprentice/trainee category, stream, level, pay point and employment-type table. Record page, section/table, row, column, rate, unit and effective date.

For a PDF, inspect the complete relevant page, including headings and footnotes; visually check the table when extraction could confuse columns. Verify against the award minimum-rate clause or FWO Pay and Conditions Tool using matching conditions.

Resolve discrepancies using the governing instrument and effective variation before a definitive answer. Never substitute casual rates or double-count an all-purpose allowance.

## 6. Calculate pay

Use decimal arithmetic and the instrument's stated wage basis and rounding rules:

- Use an expressly prescribed annual minimum where applicable.
- Otherwise convert the published full-time weekly rate: `weekly × 52`.
- If only an hourly rate is applicable, use `hourly × confirmed ordinary hours/week × 52`.
- Show substituted amounts, units, intermediate results and rounding. Do not choose the cheaper of inconsistent hourly and weekly conversions.
- Explain differences caused by published hourly rounding. Apply any explicit annual rounding rule before comparing with a published annual figure.
- Label a simple conversion as an annual equivalent at the selected rate. For an actual period spanning rate changes or progression dates, calculate each segment separately.

Identify employer superannuation, leave loading, allowances, penalties and overtime separately. Calculate extras only from verified entitlements and stated roster/leave assumptions; otherwise explain what is needed. Do not treat a base annual figure as an automatically compliant all-inclusive annualised wage. Consult [FWO annualised wages guidance](https://www.fairwork.gov.au/pay-and-wages/minimum-wages/annualised-wages-and-salaries) when relevant.

## 7. Deliver the report

Read and fill [assets/report-template.md](assets/report-template.md). It generalises the junior-accountant example's structure. Keep its section order and evidence tables, adapting the pay-guide and classification sections to award-free, agreement or state-system outcomes. Replace all placeholders. Omit irrelevant calculation examples, not material uncertainty.

Include official source links, access dates and exact clause/page locators. Separate user-confirmed facts from assumptions. State whether the result is supported, conditional or unresolved, and what fact would change it.

Give a brief chat answer with the amount, classification, workload, guide name/effective date, arithmetic, material conditions and a link to the completed Markdown report. Never claim a download, visual check or verification that did not occur.

Before delivery, confirm that the code matches the guide, exclusions were checked, classification and pay point match the duties, rates apply on the assessment date, hours and rounding are supported, additions are identified and every intermediate file is under `tmp/`.

## Gotchas
- When an industry award can not be found, stop the workflow and report the missing award. Do not assume a generic award applies. 
