---
name: git-workflow
description: Standardize day-to-day Git collaboration with a safe workflow for creating branches, committing changes, pushing to remote, syncing with upstream, and merging branches. Use when Codex needs to execute or review Git operations for feature development, bug fixes, hotfixes, pull request preparation, conflict handling, or branch cleanup, especially when clear commit hygiene and team-safe defaults are required.
---

# Git Workflow

## Overview

Use this skill to run a predictable Git collaboration flow with minimal risk.  
Follow repository-specific rules first; if the repo has no explicit convention, use the defaults below.

## Quick Start

For a new task, execute:

```bash
git fetch origin
git switch main
git pull --ff-only
git switch -c feature/<short-topic>
```

After coding:

```bash
git status
git add -p
git commit -m "feat(scope): 中文摘要"
git push -u origin feature/<short-topic>
```

Before opening/updating a PR:

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

## Branch Creation

Use branch names:
- `feature/<topic>` for new features
- `fix/<topic>` for bug fixes
- `hotfix/<topic>` for urgent production issues
- `chore/<topic>` for maintenance

Keep branch lifespan short and focused on one logical change set.

## Commit Rules

Create atomic commits:
- Include one coherent change per commit.
- Separate refactor and behavior change into different commits.
- Stage intentionally with `git add -p` instead of broad `git add .` when possible.

Use commit message format:

```text
type(scope): 中文摘要
```

Recommended `type` values:
- `feat`
- `fix`
- `refactor`
- `docs`
- `test`
- `chore`

Write summaries in imperative mood and keep them under about 72 characters.

## Push Rules

Push new branches with upstream:

```bash
git push -u origin <branch>
```

For later updates:

```bash
git push
```

Avoid force push on shared branches (`main`, `develop`, release branches).  
When rebasing your own feature branch, only use:

```bash
git push --force-with-lease
```

## Merge And Rebase

Default integration strategy:
- Rebase feature branch onto latest `origin/main` before merge.
- Prefer PR-based merge instead of direct merge to protected branches.
- Prefer squash merge when each PR should become one clean commit.

For local branch merge (when explicitly needed):

```bash
git switch main
git pull --ff-only
git merge --no-ff feature/<topic>
git push
```

## Conflict Handling

When rebase or merge conflicts happen:
1. Run `git status` to list conflicted files.
2. Resolve conflict markers in each file.
3. Run tests/build checks.
4. Continue:

```bash
git add <resolved-files>
git rebase --continue
```

Abort if needed:

```bash
git rebase --abort
```

## Personal Preferences (Default)

Apply these preferences unless the user or repo rules override them:
- Sync with remote (`fetch` + `pull --ff-only`) before creating or merging branches.
- Commit early, commit small, avoid giant mixed commits.
- Use Chinese in commit messages by default.
- Run lint/tests before each commit when available.
- Avoid committing lockfile churn unless dependencies actually changed.
- Never commit secrets, keys, `.env` files, or large generated artifacts.
- Use PR titles aligned with commit intent and explain the "why" in PR description.
- Delete merged branches to keep local and remote clean.

Post-merge cleanup:

```bash
git switch main
git pull --ff-only
git branch -d feature/<topic>
git push origin --delete feature/<topic>
```

## Safety Checklist

Before commit:
- Verify `git status` contains only intended files.
- Verify diff with `git diff --staged`.

Before push:
- Verify target branch with `git branch --show-current`.
- Verify remote with `git remote -v`.

Before merge:
- Verify latest base branch is pulled.
- Verify CI/tests are green.
