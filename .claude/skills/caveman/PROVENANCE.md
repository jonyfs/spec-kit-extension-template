# Provenance

This skill is vendored, unmodified, from an upstream project.

- **Upstream**: https://github.com/juliusbrussee/caveman
- **Path**: `skills/caveman/`
- **Commit**: `0d95a81d35a9f2d123a5e9430d1cfc43d55f1bb0` (2026-07-03)
- **Vendored on**: 2026-07-21
- **License**: MIT (see `LICENSE`, copied from the upstream repository root)

## Why vendored

The same skill is also available as a global Claude Code plugin. It is copied here
so that anyone cloning this repository gets the project's expected communication
style without installing the plugin separately.

## Updating

Re-copy `skills/caveman/` from upstream and update the commit hash above. Do not
edit `SKILL.md` in place — local divergence from upstream is not tracked anywhere.

## Scope

Only `SKILL.md` and `README.md` are vendored. Upstream also ships agents
(`cavecrew-*`), slash commands, hooks, and a `caveman-compress` skill with Python
scripts — none of those are installed here.
