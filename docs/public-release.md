# Public Release Guide

This repository is technically ready for public visibility, but the original git
history should not be exposed as-is because it contained private author metadata
such as personal email addresses and local machine or network hostnames.

## Current Risk Summary

- runtime secrets are excluded from version control through `.gitignore`
- `.env.example` contains placeholders only
- CI uses dummy environment values
- the working tree passes `ruff check .` and `pytest`
- private metadata existed in historical commits

## Publication Strategies

There are two valid publication strategies:

1. Create a new public repository from a clean export.
2. Rewrite the existing private repository to a new clean root commit.

The first option remains the lowest-risk choice because it avoids any residual
object-retention behavior on the hosting provider.

## Current Repository State

This repository has already been sanitized in place by replacing `main` with a
single clean root commit that uses a public-safe author identity.

The previous private history is retained only in local-only backups:

- local branch: `backup/private-history-20260331-205718`
- local bundle: `../vira-private-history-20260331-205718.bundle`

These backups must not be pushed to a public remote.

## Safe Workflow

For an in-place rewrite on the existing repository:

1. Create a local-only backup branch and bundle from the private history.
2. Configure a public-facing git identity before creating the new commit.
3. Create an orphan branch from the current working tree.
4. Commit the sanitized working tree as a new root commit.
5. Replace `main` locally with the new root commit.
6. Force-push `main` to the remote.
7. Enable GitHub private vulnerability reporting before announcing the project.

## Example Commands

```bash
git branch backup/private-history-<timestamp> <old-private-head>
git bundle create ../vira-private-history-<timestamp>.bundle --all
git config user.name "kagandms"
git config user.email "your-public-email@example.com"
git checkout --orphan public-main
git add -A
git commit -m "Initial public release"
git branch -D main
git branch -m main
git push --force-with-lease origin main
```

## Pre-Public Checklist

- rotate any secrets that were ever stored outside version control but used in
  local backups or legacy directories
- verify that `vira_backup_legacy/` stays out of the exported public tree
- do not push the local backup branch or the local bundle file
- confirm that repository settings do not expose private issue templates,
  actions variables, or branch names you do not want public
- understand that some git hosting providers may retain unreachable objects for
  a period after force-push or ref deletion
- choose whether the project should remain source-available only or later move
  to an open-source license
