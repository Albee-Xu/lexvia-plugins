# Monitoring Operations

Use this file for ongoing monitoring, scheduled tasks, and periodic reports. One-off policy questions do not need persistent state.

## Run sequence

1. Read `.migration-watch/monitoring-state.json` in the user's chosen project directory. If it does not exist, create it as a baseline; never ask the user to create or edit JSON.
2. Check relevant federal sources, state and territory nomination sources, then assessing-authority and English-rule sources.
3. Compare prior verified facts, update dates, and sent alerts. A changed timestamp or layout is not evidence of a rule change.
4. Verify, classify, and report eligible changes. Record source failures; never treat a failed fetch as no change.

## State requirements

The state file is the single deduplication record for that user and project. Different users must not share it. Store only timestamps, official URLs, verified summaries, access failures, and alert IDs; never store personal application data.

Use a stable alert ID based on the topic, visa/state, and effective date. Preserve history when an item is revised; add a new status instead of overwriting the prior alert.

## Limits

- A before/after claim needs both an official current source and reliable prior evidence. Otherwise say the new rule is confirmed but the prior version is not verified.
- Treat consultation papers, budgets, and media as proposed or leads until an implementing official source exists.
- Explain state and federal rules separately when their scopes differ.
- After three consecutive failed checks of a core source, disclose the limitation in the next eligible report.
- Use `Australia/Sydney` for all timestamps. Keep publication and effective dates separate.
- `.migration-watch/` is per-user runtime data and must not be committed with the plugin.
