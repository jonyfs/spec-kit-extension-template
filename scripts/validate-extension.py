#!/usr/bin/env python3
"""Validate a Spec Kit extension package against the constitution's hard rules.

Enforces, per .specify/memory/constitution.md:
  I.   Manifest Is the Contract     - required fields, id pattern, version
                                      specifier shape, every referenced path exists
  II.  Namespaced Commands          - ^speckit\\.{id}\\.[a-z0-9-]+$, no core shadowing
  III. Obvious Placeholders         - template markers must not survive into a release
  V.   Cross-Platform Script Parity - bash and powershell variants come in pairs
  VIII.Semantic Versioning          - X.Y.Z with no prefix or suffix

Usage:
    validate-extension.py <extension-dir> [<extension-dir> ...]
    validate-extension.py --release <extension-dir>   # also fail on placeholders

Exit codes: 0 = all valid, 1 = at least one error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not a package problem
    sys.exit("PyYAML is required: pip install pyyaml")

ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
COMMAND_PATTERN = re.compile(r"^speckit\.[a-z0-9-]+\.[a-z0-9-]+$")
# A version specifier with no spaces, e.g. >=0.2.0 or >=0.2.0,<2.0.0
SPECKIT_VERSION_PATTERN = re.compile(r"^(?:[<>=!~]=?\d+\.\d+\.\d+)(?:,[<>=!~]=?\d+\.\d+\.\d+)*$")

CORE_COMMANDS = {
    "speckit.constitution",
    "speckit.specify",
    "speckit.clarify",
    "speckit.plan",
    "speckit.tasks",
    "speckit.analyze",
    "speckit.checklist",
    "speckit.implement",
}

KNOWN_HOOK_EVENTS = {
    f"{phase}_{cmd}"
    for phase in ("before", "after")
    for cmd in (
        "specify",
        "clarify",
        "plan",
        "tasks",
        "implement",
        "analyze",
        "checklist",
        "constitution",
    )
}

PLACEHOLDER_MARKERS = (
    "CUSTOMIZE:",
    "my-extension",
    "Your Name",
    "your-org",
    "REPLACE THIS",
)

REQUIRED_EXTENSION_FIELDS = (
    "id",
    "name",
    "version",
    "description",
    "author",
    "repository",
    "license",
)


class Findings:
    def __init__(self, label: str) -> None:
        self.label = label
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def report(self) -> bool:
        """Print findings. Return True when the package is valid."""
        if not self.errors and not self.warnings:
            print(f"  OK  {self.label}")
            return True
        print(f"      {self.label}")
        for message in self.errors:
            print(f"  ERR   {message}")
        for message in self.warnings:
            print(f"  WARN  {message}")
        return not self.errors


def check_manifest_shape(manifest: dict, found: Findings) -> str:
    """Principle I + VIII. Returns the extension id (empty when unusable)."""
    if manifest.get("schema_version") != "1.0":
        found.error(f'schema_version must be "1.0", got {manifest.get("schema_version")!r}')

    extension = manifest.get("extension") or {}
    for field in REQUIRED_EXTENSION_FIELDS:
        if not extension.get(field):
            found.error(f"extension.{field} is required")

    ext_id = str(extension.get("id", ""))
    if ext_id and not ID_PATTERN.match(ext_id):
        found.error(f"extension.id {ext_id!r} must match ^[a-z0-9-]+$")

    version = str(extension.get("version", ""))
    if version and not VERSION_PATTERN.match(version):
        found.error(f"extension.version {version!r} must be X.Y.Z with no prefix or suffix")

    requires = manifest.get("requires") or {}
    speckit_version = str(requires.get("speckit_version", ""))
    if not speckit_version:
        found.error("requires.speckit_version is required")
    elif not SPECKIT_VERSION_PATTERN.match(speckit_version):
        found.error(
            f"requires.speckit_version {speckit_version!r} must be a specifier with no "
            "spaces, e.g. >=0.2.0 or >=0.2.0,<2.0.0"
        )

    return ext_id


def check_commands(manifest: dict, ext_id: str, root: Path, found: Findings) -> None:
    """Principle I + II."""
    provides = manifest.get("provides") or {}
    commands = provides.get("commands") or []
    hooks = manifest.get("hooks") or {}

    if not commands and not hooks:
        found.error("provides.commands or hooks must declare at least one entry")

    for command in commands:
        name = str(command.get("name", ""))
        if not COMMAND_PATTERN.match(name):
            found.error(f"command name {name!r} must match ^speckit\\.[a-z0-9-]+\\.[a-z0-9-]+$")
        elif ext_id and name.split(".")[1] != ext_id:
            found.error(f"command {name!r} namespace must equal extension.id {ext_id!r}")
        if name in CORE_COMMANDS:
            found.error(f"command {name!r} shadows a core Spec Kit command")

        for alias in command.get("aliases") or []:
            alias = str(alias)
            if not COMMAND_PATTERN.match(alias):
                found.error(f"alias {alias!r} must match the namespaced command pattern")
            elif ext_id and alias.split(".")[1] != ext_id:
                found.error(f"alias {alias!r} namespace must equal extension.id {ext_id!r}")
            if alias in CORE_COMMANDS:
                found.error(f"alias {alias!r} shadows a core Spec Kit command")

        command_file = command.get("file")
        if not command_file:
            found.error(f"command {name!r} is missing its file")
        elif not (root / command_file).is_file():
            found.error(f"command {name!r} references missing file {command_file}")

    for config in provides.get("config") or []:
        template = config.get("template")
        if template and not (root / template).is_file():
            found.error(f"config {config.get('name')!r} references missing template {template}")


def check_hooks(manifest: dict, found: Findings) -> None:
    """Principle IV + XI: known events, and auto-executing hooks are visible."""
    declared_commands = {
        str(c.get("name", "")) for c in (manifest.get("provides") or {}).get("commands") or []
    }

    for event, value in (manifest.get("hooks") or {}).items():
        if event not in KNOWN_HOOK_EVENTS:
            found.error(f"hook event {event!r} is not a recognized Spec Kit lifecycle event")

        entries = value if isinstance(value, list) else [value]
        for entry in entries:
            if not isinstance(entry, dict):
                found.error(f"hook on {event!r} must be a mapping")
                continue

            command = str(entry.get("command", ""))
            if not command:
                found.error(f"hook on {event!r} is missing its command")
            elif declared_commands and command not in declared_commands:
                found.warn(f"hook on {event!r} calls {command!r}, which this extension does not provide")

            priority = entry.get("priority")
            if priority is not None and (not isinstance(priority, int) or priority < 1):
                found.error(f"hook on {event!r} has priority {priority!r}; must be an integer >= 1")
            if len(entries) > 1 and priority is None:
                found.error(f"hook on {event!r} shares the event but declares no explicit priority")

            if entry.get("optional") is False:
                found.warn(
                    f"hook on {event!r} is optional: false (auto-executes). Principle IV requires "
                    "this to be read-only or confined to owned paths, and justified in the README"
                )
            elif entry.get("optional", True) and not entry.get("prompt"):
                # The CLI synthesizes "Execute {command}?" when no prompt is given,
                # so this is not fatal — but a hand-written prompt explains WHY the
                # user would want it, which the synthesized one cannot.
                found.warn(f"optional hook on {event!r} has no prompt; the CLI will synthesize a generic one")


def check_script_parity(root: Path, found: Findings) -> None:
    """Principle V."""
    bash_dir = root / "scripts" / "bash"
    ps_dir = root / "scripts" / "powershell"
    if not bash_dir.is_dir() and not ps_dir.is_dir():
        return

    bash_names = {p.stem for p in bash_dir.glob("*.sh")} if bash_dir.is_dir() else set()
    ps_names = {p.stem for p in ps_dir.glob("*.ps1")} if ps_dir.is_dir() else set()

    for name in sorted(bash_names - ps_names):
        found.error(f"scripts/bash/{name}.sh has no scripts/powershell/{name}.ps1 counterpart")
    for name in sorted(ps_names - bash_names):
        found.error(f"scripts/powershell/{name}.ps1 has no scripts/bash/{name}.sh counterpart")


def check_release_readiness(root: Path, found: Findings) -> None:
    """Principle III + VII + VIII, enforced only for a release candidate."""
    for required in ("README.md", "LICENSE", "CHANGELOG.md"):
        if not (root / required).is_file():
            found.error(f"{required} is required before release")

    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix not in {".md", ".yml", ".yaml", ".json", ".sh", ".ps1", ".py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for marker in PLACEHOLDER_MARKERS:
            if marker in text:
                rel = path.relative_to(root)
                found.error(f"{rel} still contains the template placeholder {marker!r}")
                break


def validate(root: Path, release: bool) -> bool:
    found = Findings(str(root))
    manifest_path = root / "extension.yml"

    if not manifest_path.is_file():
        found.error("extension.yml not found at the package root")
        return found.report()

    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        found.error(f"extension.yml is not valid YAML: {exc}")
        return found.report()

    ext_id = check_manifest_shape(manifest, found)
    check_commands(manifest, ext_id, root, found)
    check_hooks(manifest, found)
    check_script_parity(root, found)
    if release:
        check_release_readiness(root, found)

    return found.report()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="Extension package directories")
    parser.add_argument(
        "--release",
        action="store_true",
        help="Also require README/LICENSE/CHANGELOG and fail on surviving template placeholders",
    )
    args = parser.parse_args()

    print(f"Validating {len(args.paths)} extension package(s)")
    results = [validate(path, args.release) for path in args.paths]

    failed = results.count(False)
    if failed:
        print(f"\n{failed} of {len(results)} package(s) failed validation")
        return 1
    print(f"\nAll {len(results)} package(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
