# Contributing

Thank you for contributing to Home Assistant Weather Underground Uploader.
Keep changes focused on composing Home Assistant entities into a virtual
Weather Underground Personal Weather Station and uploading its observations.
The [README](README.md) describes supported behavior and current limitations.

## Before starting

Search existing issues before opening a new one. Use the structured bug or
feature form and provide only the requested information. For a non-trivial
change, agree on the scope in an issue before investing in implementation.

Small documentation corrections can go directly to a pull request. Keep each
issue and pull request independently reviewable and avoid unrelated refactoring.

## Development environment

Development is supported on the Python version pinned in `.python-version`.
Install [uv](https://docs.astral.sh/uv/), clone the repository, and create the
locked project environment:

```bash
uv sync --locked
uv run pre-commit install
```

Do not use `pip install` or add `requirements.txt` for project tooling. Declare
development tools in `pyproject.toml` and keep `uv.lock` synchronized.

## Implement and test

Follow [AGENTS.md](AGENTS.md), current Home Assistant asynchronous integration
patterns, and the existing module boundaries. One config entry must continue
to represent one independent Weather Underground station. Do not introduce
assumptions about a particular weather device, vendor, or source integration.

Add or update deterministic tests for behavior changes. Tests must not contact
live Home Assistant services or Weather Underground, use real credentials, or
wait on wall-clock time. Run the complete local validation suite before
submitting:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
```

Pull requests also run CI, hassfest, and HACS validation. A check that could not
be run must be reported accurately in the pull request.

## Documentation and translations

Update documentation when configuration, behavior, requirements, or user
expectations change. Keep English and Czech translation files synchronized for
every user-facing integration string. Use English for code, comments, tests,
logs, errors, configuration, documentation, commits, and pull requests.

## Secrets and security

Treat a Weather Underground Station Key as a password. Never submit a real
Station ID or Station Key, a complete upload URL containing credentials, an
access token, or private operational data in an issue, pull request, commit,
log, screenshot, fixture, or diagnostics attachment. Review diagnostics before
sharing because station and entity identifiers may reveal details about an
installation.

If a key was exposed, rotate it before doing anything else. Report an ordinary
bug through the bug form using only redacted evidence. Do not publish details
of a suspected security vulnerability in a public issue; use the repository's
private **Security > Report a vulnerability** option when GitHub presents it.
If that option is unavailable, open a public issue that requests a private
contact channel but contains no vulnerability details or sensitive evidence.

## Pull requests and releases

Link the relevant issue, summarize the observable result, list validation, and
state whether the change is backward compatible. Update documentation, tests,
and translations in the same pull request when applicable.

Maintainers apply the most relevant standard label used by the generated
release changelog:

- `enhancement` for features and user-visible improvements;
- `bug` for fixes;
- `documentation` for documentation-only changes.

Maintenance and unlabeled changes use the release changelog's catch-all
category. See [RELEASING.md](RELEASING.md) for versioning and release-note
preparation.
