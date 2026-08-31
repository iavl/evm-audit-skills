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

The run is written to:

```text
audits/<repo>-<UTC timestamp>/
```

Open `AUDIT-REPORT.md` for the final findings. Supporting Recon, routing,
runtime, and review evidence is kept beside it; only `CONFIRMED` records enter
the final report.
