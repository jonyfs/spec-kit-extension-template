# Packaging & Distribution Reference

Every way the `specify` CLI can install an extension, and what each one requires the
package to look like.

Verified against **specify-cli 0.11.3** by reading `specify extension --help`,
`specify_cli/extensions.py`, and the upstream catalog files. Re-verify after a CLI
upgrade — Principle XII forbids recording a form from memory.

---

## The four distribution forms

| Form | Command | Package shape | Network |
|---|---|---|---|
| Local directory | `specify extension add --dev <path>` | An unpacked directory | No |
| Custom URL | `specify extension add <id> --from <url>` | A ZIP over HTTPS | Yes |
| Catalog | `specify extension add <id>` | ZIP referenced by catalog `download_url` | Yes |
| Bundled | ships inside the CLI package | Directory inside `specify_cli` | No |

All four converge on the same code path — `install_from_directory` — so the on-disk
layout requirements are identical for every form. Only the delivery differs.

### Shared options for `extension add`

| Option | Effect |
|---|---|
| `--dev` | Install from a local directory instead of resolving a catalog entry |
| `--from TEXT` | Install from a custom URL |
| `--force` | Overwrite an already-installed extension |
| `--priority INTEGER` | Resolution priority, **lower = higher precedence**, default `10`, must be ≥ 1 |

---

## Form 1 — Local directory (`--dev`)

The development and testing form. Required by Principle VII before any release.

```bash
specify extension add --dev /path/to/my-extension
specify extension list
specify extension info my-extension
specify extension remove my-extension --force
```

Registry records `"source": "local"`.

Required layout — the directory root is the extension root:

```text
my-extension/
├── extension.yml            # required, at the root
├── README.md                # required by Principle VII
├── LICENSE                  # required by Principle VII
├── CHANGELOG.md             # required by Principle VIII
├── commands/
│   └── my-command.md
├── scripts/
│   ├── bash/*.sh            # required together (Principle V)
│   └── powershell/*.ps1
└── config-template.yml      # if provides.config is declared
```

## Form 2 — Custom URL (`--from`)

```bash
specify extension add my-extension --from https://example.com/my-extension-1.0.0.zip
```

Same ZIP contract as the catalog form below.

## Form 3 — Catalog

```bash
specify extension search <query> --tag <tag> --author <author> --verified
specify extension list --available
specify extension list --all
specify extension add <id>
specify extension update <id>          # or omit the id to update all
```

### ZIP contract

- The archive is downloaded to the CLI cache as `{extension-id}-{version}.zip`.
- `extension.yml` MUST be at the archive root **or** inside a **single** top-level
  directory. Two or more top-level directories with no root manifest fails with
  `No extension.yml found in ZIP file`.
- Paths escaping the extraction root are rejected (Zip Slip protection).
- `download_url` MUST be HTTPS. Plain HTTP is rejected except for `localhost`,
  `127.0.0.1`, and `::1`.
- GitHub release asset URLs are resolved through the GitHub API automatically.

Build it so the root is the manifest's directory:

```bash
cd my-extension && zip -r ../my-extension-1.0.0.zip . -x '.git/*'
```

### Catalog entry

Two upstream catalogs exist: `extensions/catalog.json` (core, bundled) and
`extensions/catalog.community.json` (third-party). A community entry:

```json
{
  "name": "AI-Driven Engineering (AIDE)",
  "id": "aide",
  "description": "...",
  "author": "mnriem",
  "version": "1.0.0",
  "download_url": "https://github.com/.../releases/download/aide-v1.0.0/aide.zip",
  "repository": "https://github.com/mnriem/spec-kit-extensions",
  "homepage": "...",
  "documentation": ".../README.md",
  "changelog": ".../CHANGELOG.md",
  "license": "MIT",
  "category": "process",
  "effect": "read-write",
  "requires": { "speckit_version": ">=0.2.0" },
  "provides": { "commands": 7, "hooks": 0 },
  "tags": ["workflow", "planning"],
  "verified": false,
  "downloads": 0,
  "stars": 0,
  "created_at": "2026-03-18T00:00:00Z",
  "updated_at": "2026-03-18T00:00:00Z"
}
```

`provides` in the **catalog** carries counts; `provides` in **`extension.yml`**
carries the actual definitions. They are different shapes with the same name.

Submission goes through the upstream repository's extension-submission issue
template (`.github/ISSUE_TEMPLATE/extension_submission.yml`).

### Private and third-party catalogs

```bash
specify extension catalog add https://example.com/catalog.json \
  --name my-catalog --priority 5 --install-allowed --description "Internal"
specify extension catalog list
specify extension catalog remove my-catalog
```

Stored in `.specify/extension-catalogs.yml`. Catalog URLs MUST be HTTPS.
`--install-allowed` defaults to **off** — a catalog added without it is browsable
but its extensions cannot be installed.

## Form 4 — Bundled

Extensions shipped inside the `specify_cli` package (`agent-context`, `assess`,
`bug`, `git`, …) are marked `"bundled": true` in `catalog.json` and carry no
`download_url`. Attempting to download one errors and directs the user to reinstall
the CLI. Not a form a third-party extension can use.

---

## Post-install state

| Path | Content |
|---|---|
| `.specify/extensions/{id}/` | The installed extension and its config |
| `.specify/extensions/.registry` | Version, source, `manifest_hash`, enabled, priority, registered commands/skills, `installed_at` |
| `.specify/extensions.yml` | `installed:` list, `settings:`, flattened `hooks:` |
| `.specify/extension-catalogs.yml` | Custom catalogs, if any |
| `{agent commands dir}/` | Generated command files, e.g. `.claude/commands/speckit.{id}.{cmd}.md` |

Configuration precedence, lowest to highest:

1. `defaults` in `extension.yml`
2. `.specify/extensions/{id}/{id}-config.yml` (project, committed)
3. `.specify/extensions/{id}/local-config.yml` (gitignored)
4. `SPECKIT_{EXT_ID}_{KEY}` environment variables

## Lifecycle management

```bash
specify extension disable <id>            # keep installed, stop registering
specify extension enable <id>
specify extension set-priority <id> <n>   # lower wins on command-name conflicts
specify extension remove <id> --keep-config
```

---

## Security notes

- The downloaded ZIP is **not** verified against a publisher signature or a catalog
  checksum. The only transport guarantee is HTTPS.
- `manifest_hash` in `.registry` is computed from the manifest *after* install. It
  detects local tampering afterwards; it does not authenticate the download.
- Consequently, adding a catalog with `--install-allowed` grants that catalog's
  operator code-execution reach into the project. Treat it as a trust decision.

## Release checklist

1. `extension.yml` version bumped per Principle VIII; `CHANGELOG.md` entry in the
   same change.
2. `specify extension add --dev .` → `list` → run **every** command and hook →
   `remove`. (Principle VII)
3. Build the ZIP with the manifest at the archive root.
4. Tag `v{version}` and attach the ZIP as a GitHub release asset.
5. Install the released ZIP via `--from <asset-url>` in a clean project to prove the
   published artifact, not just the working tree.
6. Submit or update the catalog entry, `download_url` pointing at the release asset.

## Worked example: this repository's own release

The `trace` extension in `template/` was released and verified through step 5, so the
checklist above is exercised rather than aspirational:

```bash
# 4. Build with the manifest at the archive root
cd template && zip -qr /tmp/trace-1.0.0.zip . -x '.git/*'
unzip -l /tmp/trace-1.0.0.zip | head    # extension.yml must be the first entry

# 4. Tag and attach
gh release create trace-v1.0.0 /tmp/trace-1.0.0.zip

# 5. Prove the PUBLISHED artifact, not the working tree
specify init proof --integration claude --ignore-agent-tools && cd proof
specify extension add trace --from https://github.com/jonyfs/spec-kit-extension-template/releases/download/trace-v1.0.0/trace-1.0.0.zip
specify extension list          # -> Feature Traceability Check (v1.0.0)
specify extension remove trace --force
```

Step 5 is the one that matters and the one most often skipped. `--dev` passing proves
the working tree parses. It does not prove `extension.yml` sits at the archive root, that
the release URL resolves, or that the CLI's GitHub asset resolution finds it. Those are
the only paths a stranger will ever use.
