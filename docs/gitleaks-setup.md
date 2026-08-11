# Block secrets at commit time (gitleaks)

A `pre-commit` hook scans **only your staged changes** with
[gitleaks](https://github.com/gitleaks/gitleaks) and refuses the commit if it finds a
credential. Works the same from the terminal, VS Code Source Control, or Claude Code —
all shell out to the same `git` binary. Typical cost on a normal diff: **~25 ms**.

## Enable it (run once per clone)

`core.hooksPath` is local git config, so cloning does not carry it — every teammate must
run this one command after cloning:

```bash
./hooks/install.sh
```

It does two jobs: wires `core.hooksPath` at `hooks/`, **and** installs gitleaks if it is
missing (Homebrew first, falling back to the official release tarball into `~/.local/bin`,
which the hooks already have on their `PATH`). No separate `brew install` step is needed.
It is idempotent, skips itself in CI (`$CI` set), and refuses to run if another hook
manager (husky/lefthook) already owns the repo.

Check both halves took:

```bash
git config --get core.hooksPath   # -> hooks
gitleaks version                  # -> a version, not "command not found"
```

If the installer could not get gitleaks (unsupported platform, no network), **every commit
is blocked** until you install it manually — the hook fails closed on purpose, since a
commit that can't be scanned is not allowed through. Windows: install gitleaks separately
from https://github.com/gitleaks/gitleaks#installing (the installer's auto-download does
not cover Windows).

## What runs

| Hook | When | Action |
|---|---|---|
| `hooks/pre-commit` | every commit | `gitleaks git --staged` on the staged diff — blocks on a finding |
| `hooks/pre-merge-commit` | `git merge` | delegates to `pre-commit` (git skips pre-commit for merge commits) |

## When it blocks you

Output names the rule, file and line, secret redacted:

```
Finding:     token = "REDACTED"
RuleID:      generic-api-key
File:        some-util/config.py
Line:        1
```

**Real secret:** remove it, read it from an env var / secret manager, and rotate it —
assume anything typed into a file is already leaked.

**False positive:** add a value-anchored allowlist to `.gitleaks.toml` (create it at repo
root) that matches the harmless *value*, not the file path. Path-based allowlists hide
every finding of that rule in the file and will mask a real credential later.

```toml
[extend]
useDefault = true

[[allowlists]]
description = "Fake key used in unit tests"
targetRules = ["generic-api-key"]
regexes = ['''^test_dummy_key_1234$''']
```

**Emergency bypass:** `GITLEAKS_SKIP=1 git commit ...`

## What this does not cover

Local guard against honest mistakes, not an enforcement boundary:

- `git commit --no-verify` skips all hooks.
- `git rebase` / `git cherry-pick` replay commits without running `pre-commit`.
- Teammates who never ran `install.sh` have no protection.
- Secrets already in history are untouched — this only scans what you are about to commit.

The only unbypassable layer is a server-side CI scan plus branch protection requiring it.
