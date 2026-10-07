# AGENTS.md

## Project Overview

`al-falak` is an offline Python library for Islamic astronomy (prayer times,
Qibla direction, Sunnah night markers). Pure standard library, zero runtime
dependencies. Pipeline architecture: coordinates + date + method/parameters →
`SolarTime` (transit, sunrise/sunset, hour angles) → `PrayerTimes`.

- Source: `src/alfalak/` (`astronomy/` pure math, `calculation/` config,
  `data/` validated types, `util/` helpers). Public API re-exported from
  `src/alfalak/__init__.py` (`__all__`); entry points `PrayerTimes`, `Qibla`,
  `SunnahTimes`, `CalculationMethod`, `CalculationParameters`, `Coordinates`.
- CLI: `python -m alfalak` (also installed as `al-falak` / `alfalak` scripts).
- Architecture detail: `ARCHITECTURE.md`. Human docs: `docs/user/`.
  Contributing (human-oriented): `CONTRIBUTING.md`. Security: `SECURITY.md`.
- Port lineage: detached fork of `alphahm/adhanpy`, itself a port of
  `batoulapps/adhan-java`. Cross-port behavior is a fidelity signal, not
  ground truth — verify algorithm changes against primary sources (Meeus,
  USNO, official Takwim values).

## Setup Commands

- Python >= 3.11 required. `uv` recommended, `pip` works.
- `uv venv && source .venv/bin/activate && uv pip install -e . -r requirements.txt`
- or `python3 -m venv venv && source venv/bin/activate && pip install -e . -r requirements.txt`
- Dev tools are pinned in `requirements.txt`: `black`, `pytest`, `pytest-cov`,
  `mypy`, `ruff`. Test doubles use stdlib `unittest.mock` only.

## Development Workflow

- Editable install once (`pip install -e .`); then run everything from repo root.
- No build step for development. Wheel build backend is `hatchling`
  (`packages = ["src/alfalak"]`); `py.typed` (PEP 561) must keep shipping —
  never remove it or add untyped public APIs.
- Design constraints (from `ARCHITECTURE.md`, enforced in review):
  - **Zero runtime dependencies** — stdlib only. Never add one.
  - All public APIs fully type-annotated (`mypy --disallow-untyped-defs` clean).
  - Errors via the `AlFalakError` hierarchy (`AstronomicalError`,
    `ConfigurationError`, `ValidationError`) — never bare `TypeError`/`RuntimeError`
    for user-facing failures.
  - Public API is minute-rounded UTC `datetime`s; keep that default.
  - New public API must be exported via `alfalak.__init__` `__all__`.

## Testing Instructions

- Run all tests with coverage: `pytest` (config in `pyproject.toml`:
  `--cov=alfalak --cov-branch`, `testpaths = "tests"`; CI additionally
  enforces `pytest --cov-fail-under=95`).
- Run without coverage: `pytest --no-cov`
- Single file: `pytest tests/test_prayer_times.py`
- Verbose: `pytest -v`
- Test layout mirrors source: `tests/astronomy/`, `tests/calculation/`,
  `tests/util/` plus top-level `test_*` modules; `tests/support.py` holds
  shared fixtures. Sweep suites (`test_parameterized_sweep.py`,
  `test_blackbox_sweep.py`) use fixed seeds — keep them deterministic.
- Golden tests cite primary sources (Meeus page + edition, paper table,
  Takwim URL + date). Preserve or strengthen source citations when touching goldens.
- DST edge-case precedent: `ZoneInfo America/New_York` spring-forward in
  `tests/test_sunnah_times.py`. Duration math belongs in UTC with `astimezone`
  only at output — keep that pattern.
- The commit should pass the whole suite before merge. Add or update tests for
  any behavior change, even if not asked.

## Code Style

- `ruff check src/ tests/` — lint gate is `F`, `E4/E7/E9` (see `pyproject.toml`).
- `black --check src/` — formatter; target `py311`.
- `mypy src` — must stay `--disallow-untyped-defs` clean.
- Narrow `except` clauses (never bare `except:`); keep existing error-type
  contracts (e.g. the internal isha-interval `ValueError` in `_set_isha` is
  load-bearing control flow — do not "fix" it into the public hierarchy).
- `CalculationParameters` copies method templates per instance — never alias
  shared `METHODS_PARAMETERS` objects into instances.

## Build and Deployment

- CI (`.github/workflows/test.yml`, runs on push, Python 3.11–3.14):
  `black --check src/` → `ruff check src/ tests/` → `mypy src` →
  `pytest --cov-fail-under=95`. Reproduce all four locally before pushing.
- Docs site: `.github/workflows/docs.yml`. Releases: `.github/workflows/release.yml`
  plus `docs/development/release/` notes (ephemeral — see below).
- `docs/user/v1.0.0/`, `docs/user/v1.1.0/`, `docs/user/v1.2.0/`,
  `docs/user/v1.2.1/` are frozen snapshots — never edit them; new user docs go in
  versionless `docs/user/` pages. Each release freezes its docs and registers
  the slug in `docs_site/versions.json` + `docs_site/src/content/versions/`.

## Pull Request Guidelines

- Title format: conventional prefix + scope, e.g. `feat:`, `fix:`, `docs:`,
  `refactor:`, `test:` (see `CONTRIBUTING.md`).
- Branch from `main`; required checks before submission: `ruff`, `black`,
  `mypy`, `pytest` (all green, same commands as CI).
- Describe the change and its test evidence. Behavior changes need updated
  goldens/invariants, not just "no crash" assertions.

## `docs/development/` Is Ephemeral — Hard Rule

- Everything under `docs/development/` (plans, milestone slices, baselines,
  test reports, release notes) is **scratch working material**: it may be
  edited, deleted, or left stale at any time, is **not** synced with the
  implementation, and is **not** shipped in releases.
- **Never mention, link to, import from, or otherwise reference any file in
  `docs/development/` from anywhere else**: no links in `README.md`,
  `docs/user/`, or any other documentation; no references in code, comments,
  or docstrings; no path strings or imports resolving into that folder.
- If durable knowledge currently living only in `docs/development/` belongs in
  a docstring or in `docs/user/`, **quote the relevant paragraph or reconstruct
  the documentation at the new location** — copy the content, never point at it.
- Conversely, never treat `docs/development/` as the source of truth when
  implementing: verify behavior against `src/`, `tests/`, and primary external
  sources. If a dev doc contradicts the code, the code wins until a deliberate
  change says otherwise.
- Do not create new cross-links *into* `docs/development/` either (e.g. don't
  add "see docs/development/..." pointers in new docs or commit messages
  beyond the ephemeral working context).

## Debugging and Troubleshooting

- Polar day/night surfaces as `AstronomicalError`, never NaN output —
  preserve that contract; `PolarCircleRule` (`NEAREST_LATITUDE` default,
  `NEAREST_DAY`, `MAKKAH`, `NONE`) is the resolution path.
- Ordering invariant on normal days:
  `fajr <= sunrise <= dhuhr <= asr <= maghrib <= isha`. Asr has two clamps
  (`asr < dhuhr` in `_set_asr`, `asr > maghrib` in `__init__`); keep both.
- `rounded_minute` is half-up with hour/day rollover — changes to rounding
  order (pre/post offsets, pre/post `astimezone`) shift every golden; decide
  explicitly and test it.
- Windows has no system IANA database: `ZoneInfo` needs the PyPI `tzdata`
  package there. That is an environment requirement, not a package dependency
  (see `SECURITY.md` scope notes).

## Security Considerations

- Report vulnerabilities via GitHub private vulnerability reporting
  (Security tab → Report a vulnerability), never a public issue. Supported:
  latest `1.x` and `main` between releases; upstream `adhanpy` is out of scope.
- Keep declared runtime dependencies at zero; offline and deterministic by
  design — no network calls, no secrets, no new I/O without explicit review.
