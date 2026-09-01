---
name: hacs-check
description: Audit the current HACS publication and branding status for this repository using the Codex GitHub capability.
metadata:
  short-description: Audit current HACS publication status
---

# HACS Check

Run a fresh HACS status audit for `pokornyIt/home-assistant-weather-underground-uploader` whenever the user invokes `HACS check`.

## Required behavior

- Query GitHub on every invocation. Do not rely on prior conversation state.
- Use the GitHub capability exposed by the Codex/VS Code extension. Never use, require, install, or shell out to `gh`.
- Inspect issue #31, including its state, latest comments, linked or replacement submission PR in `hacs/default`, PR state, reviews, requested changes, maintainer comments, CI/check status, and any action required from `pokornyIt`.
- Follow newly linked replacement PRs when the active HACS submission changes.
- Inspect `hacs/frontend#937` and `hacs/integration#5228`, then follow relevant newer issues or PRs mentioned in their current comments.
- Determine whether custom-integration-local `brand/` assets are supported and whether branding affects HACS inclusion or only icon presentation.
- Distinguish HACS blockers, items waiting for HACS maintainers, items waiting for other upstream maintainers, and actions required from `pokornyIt`.
- Do not recommend pinging or commenting on a HACS submission PR when current bot or maintainer instructions say to wait in the review queue.

## Output

Answer in Czech and keep the report concise. Use exactly these sections:

```markdown
### HACS inclusion
<current state>

### Branding
<current state>

### Akce pro tebe
<none / concrete steps>

### Změny od poslední kontroly
<meaningful changes if determinable; otherwise say that no reliable previous state is available>
```

If a previous HACS-check result is present in the current Codex context, compare it and report meaningful changes. Otherwise explicitly state that no reliable previous state is available.
