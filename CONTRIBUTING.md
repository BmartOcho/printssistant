
# Contributing Guidelines (Internal)

Thanks for helping build the Prepress Helper MVP. This is currently a **closed-source** project; do not share code outside the team.

## Branching & PRs
- Protect `main`. Develop on feature branches: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`.
- Require at least one approving review.
- Keep PRs small and focused.

## Commits
Use **Conventional Commits**:
- `feat:` new feature
- `fix:` bug fix
- `docs:`, `chore:`, `refactor:`, `test:` etc.

## Python style
- Python 3.11+
- Format with `black` and `isort`; lint with `flake8` (optional in MVP).
- Docstrings: Google or NumPy style.

## Tests
- Use `pytest`. Place tests under `tests/` mirroring `src/` structure.

## Secrets
- Do **not** commit secrets. Use `.env` locally and GitHub Actions secrets in CI (when added).

## Issue labels (suggested)
- `area:xml`, `area:skills`, `area:kb`, `area:api`, `area:cli`
- `type:bug`, `type:feature`, `type:docs`, `type:refactor`
