# Skill Factory Design System

This repo has no pixels — its "UI" is Markdown skill files, YAML frontmatter,
and chat-style CLI output. Those surfaces were already following a consistent
but implicit design language across `skills/skill-factory/SKILL.md`,
`templates/`, `plugins/skill_factory.py`, and `examples/generated/`. This
document extracts that language into explicit tokens and components so every
future skill, plugin, and generated artifact stays consistent without
re-deriving the conventions each time.

Machine-readable form: [`tokens.json`](./tokens.json).
Enforcement: [`plugins/design_lint.py`](../../plugins/design_lint.py).

---

## 1. Principles

1. **Silent by default, visible on demand.** Background behavior (observation,
   tracking) produces no output. Only explicit triggers (a command, a
   threshold, a wrap-up) surface a message.
2. **Propose, don't impose.** Anything generated on the user's behalf is
   presented as a reviewable proposal with an explicit accept/skip choice,
   never auto-committed silently.
3. **One thing at a time.** A single proposal, a single confirmation, a single
   next-step question — never stacked walls of output.
4. **Every message ends actionable.** Status output always closes with either
   a concrete next command or an explicit "nothing to do" state — never a
   dead end.

## 2. Frontmatter schema (metadata tokens)

Every skill file (hand-written or generated) declares the same ordered
frontmatter block:

| Field | Type | Required | Rule |
|---|---|---|---|
| `name` | string | yes | Title Case, human-readable |
| `version` | semver string | yes | starts at `1.0.0` |
| `category` | string | yes | kebab-case, from the category taxonomy (§5) |
| `description` | string | yes | one line, no trailing period |
| `tags` | array | yes | 3–6 kebab-case tags |
| `author` | string | no | present on hand-authored skills |
| `generated_by` | string | no | present only on machine-generated skills, e.g. `skill-factory` |
| `generated_at` | date `YYYY-MM-DD` | no | required if `generated_by` is set |

## 3. Document structure (layout tokens)

A `SKILL.md` body is a fixed sequence of sections. A section may be omitted
only if the skill genuinely has nothing to say there (e.g. no anti-patterns
yet) — order is never reshuffled:

1. `# {Title}` + 2–3 sentence lede (what it does, why it exists)
2. `## When to Activate` — bullet list of trigger conditions
3. `## Workflow` — one or more `### Phase N: {Name}` blocks, each with a
   `**Steps:**` numbered list and an optional `**Before moving on:**`
   checklist (`- [ ]`)
4. `## Quality Checklist` — `- [ ]` items, checked before the workflow counts
   as done
5. `## Examples` — one or more `### Example N: {Scenario}` drawn from a real
   session, never hypothetical
6. `## Anti-patterns` — bullet list, each item prefixed `❌`
7. `## Integration` — bullets naming related skills/tools

## 4. Voice & tone tokens

- **Imperative, second person** for instructions ("Run `pytest`", not "The
  user should run pytest").
- **Concrete over abstract.** A step names the actual command, not a
  paraphrase of it.
- **The *why*, not just the *what*.** Steps and examples carry the reasoning
  a future reader needs to adapt the workflow, not just the literal commands.
- **No filler affirmations.** Status and confirmation messages state the
  result plainly (`✅ Skill 'x' written to ...`) without congratulatory
  language.

## 5. Naming & taxonomy tokens

| Rule | Good | Bad |
|---|---|---|
| kebab-case identifiers | `git-pr-workflow` | `GitPRWorkflow` |
| descriptive, not generic | `python-env-setup` | `setup` |
| domain-qualified | `docker-debug-cycle` | `debugging` |
| no version suffix in the name | `api-testing` | `api-testing-v2` |

Sanitization rule (canonical implementation in `_sanitize_name`,
`plugins/skill_factory.py`): lowercase → strip non `[a-z0-9\s-]` → collapse
whitespace/underscore runs to `-` → collapse repeated `-` → trim leading and
trailing `-`.

Category taxonomy is open but flat — one segment, kebab-case (`meta`,
`software-development`, `custom`, …), mapped directly to a directory:
`~/.hermes/skills/<category>/<skill-name>/SKILL.md`.

## 6. Iconography tokens

A fixed, small icon vocabulary — never introduce a new icon for a meaning
already covered below, and never reuse one of these for a different meaning:

| Icon | Meaning | Where |
|---|---|---|
| 🏭 | Skill Factory brand / section header | banners, status messages |
| ✅ | Success / completed action | confirmations |
| ❌ | Anti-pattern / failure | anti-pattern lists, error replies |
| ━ (U+2501) | Banner rule | proposal banner top/bottom border |
| `[ ]` / `[x]` | Checklist item, unchecked/checked | quality gates |

## 7. CLI output components

### 7.1 Proposal banner

The one high-ceremony surface in the system — reserved for the moment the
factory asks for a decision:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏭 SKILL FACTORY — New Skill Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I noticed you repeatedly [observed workflow].

Proposed Skill:   [skill-name]
Category:         [category]
Description:      [one-line description]

What it captures:
  1. [step]

Generate:
  [A] SKILL.md only
  [B] plugin.py only
  [C] Both (recommended)
  [D] Skip

Reply with A, B, C, or D (or just "yes" for C).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Rules: exactly one banner in flight at a time; 37-character rule width;
label column aligned at column 19 (`Proposed Skill:` / `Category:` /
`Description:` each padded to that width).

### 7.2 Status reply

Low-ceremony, no banner — a bolded 🏭-prefixed header line, then a flat bullet
list of numbers, then an italic next-action hint:

```
🏭 **Skill Factory Status**

- Session duration: {n} min
- Events tracked: {n}
- Skills in queue: {n}
- Skills generated: {n}

_Skill Factory is watching silently. Run `/skill-factory propose` to surface a proposal now._
```

### 7.3 Confirmation reply

```
✅ **Skill '{name}' saved!**

Files written:
- `{path}`

Run `hermes skills reload` or restart Hermes to activate.
```

### 7.4 Error reply

```
❌ {what failed}: {reason}
```

### 7.5 Shell installer output

Terminal (non-chat) scripts use ANSI color, not emoji, keyed by severity, each
line prefixed with the plugin's bracketed name:

| Role | Color | Prefix |
|---|---|---|
| info | green (`\033[0;32m`) | `[skill-factory] ` |
| warn | yellow (`\033[1;33m`) | `[skill-factory] ` |
| error | red (`\033[0;31m`), to stderr, exits non-zero | `[skill-factory] ` |

## 8. Anti-patterns for this design system itself

- ❌ A new emoji invented for a meaning §6 already covers
- ❌ A generated `SKILL.md` that skips straight from frontmatter to
  `## Workflow` without `## When to Activate`
- ❌ A proposal banner with more than one skill offered at a time
- ❌ A status/confirmation reply that doesn't end in a next action
- ❌ A skill or plugin name that isn't kebab-case
