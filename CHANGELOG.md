# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project constitution (`.specify/memory/constitution.md`) defining thirteen
  principles for authoring Spec Kit extensions.
- `docs/HOOKS.md` — reference for both hook layers: Spec Kit lifecycle hooks
  declared in `extension.yml`, and harness hooks that execute shell commands.
- `docs/PACKAGING.md` — reference for all four distribution forms the `specify`
  CLI supports, verified against specify-cli 0.11.3.
- `scripts/validate-extension.py` — manifest, command-namespacing, hook, and
  script-parity validation.
- `scripts/check-placeholders.sh` — guards against template placeholders
  surviving into a release.
- `scripts/install-test.sh` — the install → list → info → remove cycle.
- GitHub Actions CI running lint, manifest validation, the placeholder guard,
  and the install-test cycle on every pull request.
- Vendored `caveman` skill from `juliusbrussee/caveman` (MIT) with provenance.
- Six community Spec Kit extensions installed as the project baseline:
  `worktrees`, `ship`, `critique`, `staff-review`,
  `speckit-superpowers-bridge`, and `onboard`.
