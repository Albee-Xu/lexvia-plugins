# Verification and filling gates

Record validation is necessary but does not establish source truth. The agent must inspect the cited material and make the semantic decisions. Helpers cannot prove that an excerpt is true, exhaustive or correctly interpreted.

Before exporting fill values:

1. Source IDs and hashes match the manifest; every selected value has a matching accepted evidence/user-answer record and a usable native locator. Derivatives have original lineage and reported losses.
2. Subject, role, field and value agree across evidence and answer records. Conflicts, missing values, unreadable sources, manual actions and inactive branches are not exported.
3. The selected profile matches the actual template hash and supported version. Every exported mapping is mechanically verified and target compatibility has been established. Unverified sample mappings are never exportable.
4. Applicability, requiredness, choice exclusivity, types/length/date rules and repeated-slot capacity are checked where represented in the profile. Do not invent missing rules just to mark validation complete.
5. Signatures and signing dates are excluded. Consent/declaration/authority-dependent selections need explicit matching user answers with the correct scope.

Use the authorized Anthropic PDF skill to perform the actual fill. For interactive fields inspect its extracted IDs, pages and allowed export values. For flat/annotation workflows use its structural/visual coordinates and placement checks. Do not use the coordinator to replace these operations.

After filling, reopen the actual saved output. Compare stored `/V` values and effective parent/widget values, and confirm appearances show the intended result. A radio group's several widgets are not independent answers. Duplicate logical names without clear hierarchy need investigation. An annotation output has annotation/text/visual checks rather than interactive field readback.

Render all affected pages and inspect at sufficient resolution using file/image-reading tools without opening an app. Check names/identifiers, choice marks, glyphs, text fit, wrapped lines, overflow, untouched inactive sections and signature areas. If no visual inspection method is available, mark rendering/visual QA pending; do not claim completion based on pixels existing. Programmatic bounds checks supplement, not replace, visual inspection.

Upstream helper messages matter: some bounding-box errors may be printed without a failing process code, and the convenience renderer may downscale pages. Read actual output, inspect actual dimensions, and use high-resolution crops for small fields. Resolve actual dependency filenames/commands at setup rather than copying documentation typos.

Keep `qa.readback`, `qa.rendered`, and `qa.originals` honest: pending, pass or fail as permitted by the schema. Preserve a draft when useful, but prominently report unresolved QA and gaps. Verify original hashes again after all operations. Never deliver a renamed blank form as a completed draft or call an unverified repair successful.

Reference: [Anthropic PDF form workflow](https://github.com/anthropics/skills/blob/main/skills/pdf/forms.md), [pypdf forms](https://pypdf.readthedocs.io/en/stable/user/forms.html). The PDF dependency remains separate and retains its own terms.
