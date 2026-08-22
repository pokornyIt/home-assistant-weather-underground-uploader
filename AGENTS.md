# Repository Instructions

## Scope and source of truth

These instructions apply to the entire repository.

GitHub issue #1 defines the product scope and issues #2 through #7 define the
incremental implementation roadmap. Read the active issue and the remaining
roadmap issues before making architectural decisions. Implement only the active
issue unless the user explicitly expands the scope.

The integration represents a virtual Weather Underground Personal Weather
Station composed from arbitrary Home Assistant entities. Do not introduce
dependencies on particular devices, vendors, or source integrations.

## Communication and language

- Communicate with the user in Czech.
- Write source code and technical artifacts in English.
- Use English for identifiers, comments, docstrings, tests, logs, errors,
  configuration comments, documentation, commit messages, and pull request
  text.
- Use `pokornyIt` whenever the repository owner or author's name is required.

## Home Assistant architecture

- Target Home Assistant 2026.7 or newer and its supported Python version.
- Follow current Home Assistant developer documentation and native integration
  patterns.
- Keep the integration under
  `custom_components/weather_underground_uploader/`.
- Use the domain `weather_underground_uploader`.
- Use config entries, config flow, translations, and asynchronous APIs.
- Configuration is UI-only. Do not add YAML configuration.
- One config entry represents exactly one Weather Underground station. Multiple
  independent config entries must remain supported.
- Use the Station ID as the stable config-entry unique ID and reject duplicate
  stations cleanly.
- Treat the Station Key as a secret. Never expose it in logs, diagnostics,
  exceptions, examples, fixtures, snapshots, or test failure output.
- Use Home Assistant's shared HTTP infrastructure for future network access.
- Keep setup, unload, reload, and future resource cleanup lifecycle-safe.

## Code organization

Keep responsibilities in focused modules. Maintain clear boundaries between:

- Home Assistant lifecycle;
- configuration and options flows;
- entity mapping;
- validation and unit normalization;
- Weather Underground protocol and HTTP access;
- upload scheduling;
- operational entities;
- diagnostics.

Do not place unrelated behavior into `__init__.py` or `config_flow.py`. Avoid
premature abstractions and do not implement roadmap work before its issue.

## Python toolchain and style

- Use the Python version pinned in `.python-version`.
- Use `uv` for dependency management, environments, locking, and tool
  execution.
- Keep the project environment in `.venv`.
- Declare development dependencies in `pyproject.toml` and keep `uv.lock`
  synchronized.
- Do not use `pip install` or add `requirements.txt` for project tooling.
- Do not add a production dependency without a concrete need and an
  explanation in the change summary.
- Add precise type annotations and concise English docstrings to integration
  code.
- Prefer small, async, deterministic functions and Home Assistant helpers.
- Do not perform blocking I/O.

## Security

- Never commit real Weather Underground credentials or operational data that
  may contain private information.
- Never log complete Weather Underground request URLs because they may contain
  credentials.
- Redact secrets before producing diagnostics, exceptions, or debug output.
- Tests must use clearly synthetic values and must not print or snapshot secret
  fields.

## Testing and validation

Add or update tests with each behavior change. Use Home Assistant test helpers
and fixtures for config flows and config entries. Tests must not require live
Home Assistant services, Weather Underground access, real credentials, network
access, or wall-clock waiting.

For a normal Python change, run all configured checks:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
```

Run HACS and hassfest validation when their workflows or local tooling are
introduced. Do not report a check as passing if it could not be run.

## Change discipline

- Inspect the working tree before editing and preserve unrelated user changes.
- Make focused changes and avoid unrelated refactoring.
- Do not edit generated files manually when a generator is available.
- Keep manifest metadata, translations, tests, and documentation consistent.
- Record meaningful implementation progress in the active GitHub issue when
  the user requests issue-based tracking.
- Do not mark work complete before relevant validation passes.
- Report implemented behavior, architectural decisions, validation results,
  and intentionally deferred roadmap work.
