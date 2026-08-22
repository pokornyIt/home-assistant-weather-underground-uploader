# Contributing

Contributions that keep the integration focused, hardware-independent, and
safe for Home Assistant users are welcome.

## Before starting

- Search the issue tracker for existing work.
- Open or discuss an issue before a large behavioral or architectural change.
- Keep one independently reviewable outcome per pull request.
- Do not add vendor-specific assumptions to the virtual-station model.
- Never include real Station IDs, Station Keys, upload URLs, or private
  operational data.

## Development setup

Use the Python version in `.python-version` and a project-local environment
managed by `uv`:

```bash
uv sync --locked
uv run pre-commit install
```

Do not install project tools with `pip` or add a `requirements.txt` file.

## Implementing changes

- Follow `AGENTS.md` and current Home Assistant custom-integration patterns.
- Keep configuration UI-only and asynchronous.
- Add or update tests for every behavior change.
- Treat the Station Key as a secret in code, tests, errors, logs, diagnostics,
  fixtures, and snapshots.
- Add every user-facing string to both `translations/en.json` and
  `translations/cs.json` with identical keys and placeholders.
- Update the README and changelog when behavior visible to users changes.

Run the complete local validation suite before opening a pull request:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
```

The HACS and hassfest GitHub Actions must also pass.

## Pull requests

Use an English, outcome-oriented title and description. Summarize user-visible
behavior, security-relevant decisions, validation results, and intentionally
deferred scope. Link the issue the pull request resolves.

## Security reports

Do not publish credentials or an exploitable secret-handling problem in a
public issue. Use GitHub's private vulnerability reporting for this repository
when available. For other security concerns, open a minimal issue that contains
no sensitive evidence so the maintainer can arrange a private channel.
