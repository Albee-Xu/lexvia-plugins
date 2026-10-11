---
name: meeting-minutes
description: Turn meeting transcript text pasted or uploaded by the user into concise, actionable Chinese meeting-minutes PDFs, extracting decisions, action items, owners, deadlines, risks, and open questions.
---

# Meeting Minutes Automation

Use this skill for transcript text pasted directly into chat or supplied as an uploaded UTF-8 `.txt` file. Do not ask users to place material in a particular folder. This skill does not process recordings or call external transcription services.

## Input and output

1. Treat the complete text pasted in chat or the uploaded `.txt` file as the source of record. If no text is provided, ask the user to paste the complete transcript or upload a UTF-8 `.txt` file.
2. Preserve uncertainty that affects a decision, owner, deadline, or commitment. When information is insufficient, use `待确认` according to these rules; never guess.
3. Create `会议产出/YYYY-MM-DD/` in the current workspace using the actual meeting date. If that date is unknown, use the current date only for the folder name and show `待确认` as the meeting date in the minutes.
4. If the target date folder already exists, stop and ask the user to select another output location or confirm how to proceed. Never overwrite existing meeting material.
5. Generate `会议纪要.pdf`, return it as a chat attachment, and save it in the output folder. If no writable workspace is available, ask the user to provide one or specify an output path.
6. For an uploaded source file, copy it into the output folder as `听写原文.txt`. Do not separately save text pasted in chat unless the user explicitly asks.

## Content rules

Read [content rules](references/content_rules.md), [the minutes template](references/meeting_minutes_template.md), and [the PDF layout specification](references/pdf_layout.md) before drafting. Extract only confirmed decisions, action items, owners, deadlines, existing-task status, risks, blockers, and open questions; do not paraphrase the transcript sentence by sentence.

The fixed internal roster is `Fred`, `Eva`, `CC`, `Yuri`, `Winona`, `Albee`, `Austin`, and `William`.

- Match internal names case-insensitively. Correct a phonetic, mixed-script, abbreviated, or misspelled name only when it uniquely and clearly identifies a roster member.
- Never force a client, supplier, or other external person onto the internal roster. Preserve the transcribed name and state the relationship where useful.
- When the transcript explicitly assigns work to a roster member, retain that name. Map a first-person commitment only with direct evidence of the speaker identity; otherwise use `待确认` for the owner.
- Do not guess between similar names. List only attendees supported explicitly by the transcript.

## PDF delivery

Use the [branded Word template](assets/Logo%20Template.docx) with the layout specification to create the final PDF. Preserve its headers, footers, background, and page settings. Render and inspect the PDF for Chinese-font support, tables, wrapping, pagination, headers, footers, and readability on every page.

The final PDF must contain the five required sections and tables. Markdown or DOCX drafts are temporary only; do not retain `会议纪要.md` in the output folder. Before delivery, verify that:

1. No facts, decisions, owners, deadlines, or speaker identities were invented.
2. Proposals and confirmed decisions are clearly distinguished.
3. Action items identify deliverables, and identify owners and dates only when supported by evidence.
4. The risk table contains only material unresolved matters that affect a decision, schedule, budget, or delivery.
5. `会议纪要.pdf` was delivered both as a chat attachment and as a workspace copy.
