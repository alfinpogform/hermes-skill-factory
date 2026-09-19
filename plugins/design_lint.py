"""
Design Lint Plugin for Hermes
==============================
Validates a SKILL.md file against the Skill Factory design system
(docs/design-system/DESIGN_SYSTEM.md, docs/design-system/tokens.json).

Catches drift before it ships: missing frontmatter fields, out-of-taxonomy
casing, missing/misordered sections, non-kebab-case names, and reused/foreign
icons.

Install:
    cp design_lint.py ~/.hermes/plugins/

Usage (as a Hermes command):
    /design-lint <path/to/SKILL.md>

Usage (standalone CLI):
    python design_lint.py path/to/SKILL.md [more paths...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

TOKENS_PATH = Path(__file__).resolve().parent.parent / "docs" / "design-system" / "tokens.json"

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

ALLOWED_ICONS = {"🏭", "✅", "❌", "━"}
# Emoji-ish codepoints commonly seen in ad-hoc chat output; anything in this
# ranges that isn't in ALLOWED_ICONS is flagged as a foreign icon.
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)


def _load_tokens() -> dict[str, Any]:
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Minimal YAML-subset parser for the flat `key: value` / `key: [a, b]`
    frontmatter this repo uses. Not a general YAML parser by design — the
    design system deliberately keeps frontmatter flat and simple."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None

    data: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            data[key] = items
        else:
            data[key] = value.strip("\"'")
    return data


def lint_skill_text(text: str, tokens: dict[str, Any] | None = None) -> list[str]:
    """Lint SKILL.md content against the design system. Returns a list of
    human-readable issues; an empty list means the file is compliant."""
    tokens = tokens or _load_tokens()
    issues: list[str] = []

    frontmatter = _parse_frontmatter(text)
    if frontmatter is None:
        return ["missing or malformed frontmatter block (must start/end with '---')"]

    fm_rules = tokens["frontmatter"]
    for field in fm_rules["required"]:
        if field not in frontmatter or not frontmatter[field]:
            issues.append(f"frontmatter: missing required field '{field}'")

    if "category" in frontmatter and not KEBAB_RE.match(frontmatter["category"]):
        issues.append(f"frontmatter: category '{frontmatter['category']}' is not kebab-case")

    if "version" in frontmatter and not SEMVER_RE.match(frontmatter["version"]):
        issues.append(f"frontmatter: version '{frontmatter['version']}' is not semver (x.y.z)")

    if "tags" in frontmatter:
        tags = frontmatter["tags"]
        if isinstance(tags, list):
            for tag in tags:
                if not KEBAB_RE.match(tag):
                    issues.append(f"frontmatter: tag '{tag}' is not kebab-case")
            min_tags = fm_rules["rules"]["tags"]["minItems"]
            max_tags = fm_rules["rules"]["tags"]["maxItems"]
            if not (min_tags <= len(tags) <= max_tags):
                issues.append(
                    f"frontmatter: expected {min_tags}-{max_tags} tags, found {len(tags)}"
                )

    if frontmatter.get("generated_by") and not frontmatter.get("generated_at"):
        issues.append("frontmatter: 'generated_by' is set but 'generated_at' is missing")

    if "generated_at" in frontmatter and not DATE_RE.match(frontmatter["generated_at"]):
        issues.append(
            f"frontmatter: generated_at '{frontmatter['generated_at']}' is not YYYY-MM-DD"
        )

    section_rules = tokens["sections"]
    headings = HEADING_RE.findall(text)
    for required in section_rules["required"]:
        if required not in headings:
            issues.append(f"structure: missing required section '## {required}'")

    known_order = section_rules["order"]
    present_known = [h for h in headings if h in known_order]
    expected_relative = [h for h in known_order if h in present_known]
    if present_known != expected_relative:
        issues.append(
            "structure: sections are out of order "
            f"(found {present_known}, expected relative order {expected_relative})"
        )

    if "Anti-patterns" in headings:
        anti_section = text.split("## Anti-patterns", 1)[1]
        anti_section = anti_section.split("\n## ", 1)[0]
        for line in anti_section.splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "*")) and stripped.lstrip("-* ").strip():
                if not stripped.lstrip("-* ").startswith("❌"):
                    issues.append(f"voice: anti-pattern bullet missing '❌' prefix: {stripped!r}")

    for match in EMOJI_RE.finditer(text):
        if match.group(0) not in ALLOWED_ICONS:
            issues.append(
                f"iconography: '{match.group(0)}' is not in the allowed icon set {sorted(ALLOWED_ICONS)}"
            )

    return issues


def lint_skill_file(path: Path, tokens: dict[str, Any] | None = None) -> list[str]:
    return lint_skill_text(path.read_text(encoding="utf-8"), tokens)


def check_name(name: str, tokens: dict[str, Any] | None = None) -> list[str]:
    """Validate a skill/plugin identifier (not the frontmatter `name` field,
    which is Title Case — this is the kebab-case directory/command name)."""
    tokens = tokens or _load_tokens()
    pattern = re.compile(tokens["naming"]["pattern"])
    issues = []
    if not pattern.match(name):
        issues.append(f"naming: '{name}' is not kebab-case")
    if re.search(r"-v\d+$", name):
        issues.append(f"naming: '{name}' has a version suffix — versions belong in frontmatter")
    return issues


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python design_lint.py <SKILL.md> [more paths...]", file=sys.stderr)
        return 2

    tokens = _load_tokens()
    exit_code = 0
    for arg in argv:
        path = Path(arg)
        issues = lint_skill_file(path, tokens)
        if issues:
            exit_code = 1
            print(f"❌ {path}: {len(issues)} issue(s)")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"✅ {path}: compliant")
    return exit_code


# ---------------------------------------------------------------------------
# Hermes plugin registration
# ---------------------------------------------------------------------------

PLUGIN_NAME = "design-lint"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Validate a SKILL.md against the Skill Factory design system"


def register(hermes):
    """Register the /design-lint command with the Hermes agent."""

    @hermes.command(
        name="design-lint",
        description=PLUGIN_DESCRIPTION,
        usage="/design-lint <path/to/SKILL.md>",
    )
    async def cmd_design_lint(ctx, args: str = ""):
        path_str = args.strip()
        if not path_str:
            await ctx.reply("Usage: `/design-lint <path/to/SKILL.md>`")
            return

        path = Path(path_str).expanduser()
        if not path.is_file():
            await ctx.reply(f"❌ No such file: `{path}`")
            return

        issues = lint_skill_file(path)
        if not issues:
            await ctx.reply(f"✅ `{path}` is compliant with the design system.")
            return

        lines = [f"❌ `{path}` — {len(issues)} issue(s):", ""]
        lines += [f"- {issue}" for issue in issues]
        await ctx.reply("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
