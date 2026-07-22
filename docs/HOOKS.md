# Hooks Reference

An extension built from this template can be affected by **two independent hook
layers**. They share a name and nothing else. Confusing them is the most common
source of "my hook did not fire" bug reports.

| | Layer 1 — Spec Kit lifecycle hooks | Layer 2 — Harness hooks |
|---|---|---|
| Declared in | `extension.yml` (`hooks:`) | Harness config (e.g. `.claude/settings.json`) |
| Aggregated in | `.specify/extensions.yml` | n/a |
| Fires on | Spec Kit command lifecycle events | Harness runtime events (tool calls, prompts, session) |
| Executes | A Spec Kit slash command | A shell command |
| Runs as | Prompt text interpreted by the agent | A real OS process |
| Owned by | The extension | The user's machine |
| Can block? | No — it is a suggestion or an auto-invocation | Yes — a non-zero exit can veto a tool call |

An extension **declares** Layer 1 hooks. An extension **must not silently install**
Layer 2 hooks — see Principle XI in the constitution.

---

## Layer 1 — Spec Kit lifecycle hooks

### Events

Paired `before_` / `after_` events exist for each core command:

| Event pair | Fires around |
|---|---|
| `before_specify` / `after_specify` | `/speckit.specify` |
| `before_clarify` / `after_clarify` | `/speckit.clarify` |
| `before_plan` / `after_plan` | `/speckit.plan` |
| `before_tasks` / `after_tasks` | `/speckit.tasks` |
| `before_implement` / `after_implement` | `/speckit.implement` |
| `before_analyze` / `after_analyze` | `/speckit.analyze` |
| `before_checklist` / `after_checklist` | `/speckit.checklist` |
| `before_constitution` / `after_constitution` | `/speckit.constitution` |

An unrecognized event name is a manifest validation failure, not a silent no-op.
Verify the current supported set against upstream `extensions/EXTENSION-API-REFERENCE.md`
before relying on any pair not exercised by this project.

### Declaration

Single hook on an event:

```yaml
hooks:
  after_tasks:
    command: "speckit.my-extension.sync"
    optional: true                 # default true; prompts the user
    prompt: "Sync tasks to the tracker?"
    description: "Push generated tasks to the issue tracker"
    priority: 10                   # integer >= 1, lower runs first
    condition: null                # evaluated by the HookExecutor, not by prose
```

Multiple hooks on one event — use a list, and set `priority` explicitly:

```yaml
hooks:
  after_plan:
    - command: "speckit.my-extension.verify"
      priority: 5
    - command: "speckit.my-extension.report"
      priority: 10
```

Ordering is by ascending `priority`; equal priorities keep authoring order via a
stable sort.

### Installed form

On install, the CLI flattens every installed extension's hooks into
`.specify/extensions.yml`:

```yaml
installed:
- agent-context
settings:
  auto_execute_hooks: true
hooks:
  after_plan:
  - extension: agent-context
    command: speckit.agent-context.update
    enabled: true
    optional: true
    priority: 10
    prompt: Execute speckit.agent-context.update?
    description: Refresh agent context after planning
    condition: null
```

### Consumption rules

A command that honors hooks must:

1. Skip silently when `.specify/extensions.yml` is absent or unparseable.
2. Treat a missing `enabled` field as `true`; skip only when it is explicitly `false`.
3. Never interpret a non-empty `condition` — skip the hook and leave evaluation to
   the HookExecutor.
4. Convert dots to hyphens when rendering the slash command:
   `speckit.git.commit` → `/speckit-git-commit`.
5. For `optional: true`, present the hook and let the user invoke it.
   For `optional: false`, emit `EXECUTE_COMMAND: {command}` and wait for the result.

### Gotchas

- `optional` defaults to **true**. Omitting it does not make a hook mandatory.
- A `before_` hook cannot cancel the command it precedes. It is not a veto.
- Hook commands run as the agent, with the agent's permissions — not in a sandbox.
- Hooks fire only for users who installed your extension *and* run the core command.
  Never make an extension's correctness depend on a hook having fired.

---

## Layer 2 — Harness hooks

Harness hooks are shell commands the agent runtime executes around its own events.
They are configured by the **user**, in the user's config, and they run as real
processes on the user's machine.

### Claude Code

Config: `.claude/settings.json` (project), `.claude/settings.local.json` (untracked
local), `~/.claude/settings.json` (user-global).

Events:

| Event | Fires |
|---|---|
| `PreToolUse` | Before a tool call; **exit code 2 blocks the call** |
| `PostToolUse` | After a tool call completes |
| `UserPromptSubmit` | When the user submits a prompt; stdout is injected as context |
| `SessionStart` | Session begins (`matcher: startup\|resume`) |
| `SessionEnd` | Session ends |
| `Stop` | The main agent finishes responding |
| `SubagentStop` | A subagent finishes |
| `PreCompact` | Before context compaction |
| `Notification` | The harness raises a notification |

Shape — events take a list of matcher groups, each holding a list of hook entries:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "pnpm prettier --write \"$FILE_PATH\"",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Contract:

- The hook receives the event payload as **JSON on stdin**.
- `matcher` is a regex over the tool name (tool-scoped events only).
- Exit `0` = allow; exit `2` = block with stderr shown to the agent; other non-zero
  = error, surfaced but non-blocking.
- `UserPromptSubmit` and `SessionStart` stdout is injected into the conversation as
  additional context.
- `timeout` is in seconds.

### Codex

Config: `.codex/hooks.json`. The observed shape mirrors Claude Code's
(`hooks` → event → `matcher` + `hooks[]` with `type: "command"`, `command`,
`timeout`, plus a `statusMessage` field). Treat only the events you have verified in
the installed Codex version as supported.

### Other harnesses

Gemini CLI, opencode, Cursor, and others expose their own configuration surfaces
that differ in file location, event names, and blocking semantics. This project does
**not** record their contracts from memory. Before shipping harness-hook support for
any of them, read that harness's current documentation and add a verified row here —
Principle XI requires the matrix to be evidence-backed, not inferred.

---

## Writing a harness hook safely

If an extension asks a user to install a Layer 2 hook, the snippet must:

- Be quoted for paths containing spaces (`"$FILE_PATH"`, not `$FILE_PATH`).
- Use project-local tooling (`pnpm eslint`), never remote one-off package execution.
- Set an explicit `timeout` — a hanging hook hangs the agent.
- Exit `0` when the hook is not applicable, rather than erroring on unrelated files.
- Never write outside the paths the extension owns.
- Never exfiltrate file contents or prompts to a network endpoint.

Blocking hooks (`PreToolUse`, exit `2`) are the highest-risk shape: a wrong regex can
make an entire tool unusable in the user's session. Ship them only when blocking is
the actual point, and document the exact failure mode in the extension README.
