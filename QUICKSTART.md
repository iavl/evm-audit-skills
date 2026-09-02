# Quick Start

## 1. Install the suite

Keep the repository together under your Codex skills directory. For a fresh
installation:

```bash
git clone https://github.com/iavl/evm-audit-skills-standalone ~/.codex/skills/evm-audit-skills
for skill in ~/.codex/skills/evm-audit-skills/skills/evm-audit-*; do
  ln -s "$skill" ~/.codex/skills/"$(basename "$skill")"
done
```

If the suite is already checked out, use that directory instead of cloning.

## 2. Start the audit

Use `evm-audit-master` unless you have a specific Domain in mind. Give Codex a
local Solidity repository or repository URL, for example:

```text
Audit this Solidity repository with evm-audit-master: /path/to/project
```

## 3. Read the artifacts

Choose an external sibling run directory, for example:

```text
../<repo>-audit-run/
```

The target/build tree is authoritative input and the run directory is mutable
authoring state; equal or descendant run paths are rejected.

Open `AUDIT-REPORT.md` for the final findings. Supporting Recon, routing,
runtime, Domain Resolution, Domain Context, and review evidence is kept beside
it; only `CONFIRMED` records enter the final report. Required context and
unresolved Deferred Domains prevent a clean completion.
