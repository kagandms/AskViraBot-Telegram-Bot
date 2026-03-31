# Public Release Guide

This repository is technically ready for public visibility, but the current git
history should not be exposed as-is because it contains private author metadata
such as personal email addresses and local machine or network hostnames.

## Current Risk Summary

- runtime secrets are excluded from version control through `.gitignore`
- `.env.example` contains placeholders only
- CI uses dummy environment values
- the working tree passes `ruff check .` and `pytest`
- private metadata still exists in historical commits

## Recommended Publication Strategy

Prefer publishing a clean public repository instead of making the existing
private repository public in place.

Why:

- it avoids destructive history rewriting on the private working repository
- it prevents private commit metadata from becoming public
- it keeps legacy material and private experimentation out of the public record

## Safe Workflow

1. Create a new empty public GitHub repository.
2. Export the current working tree without `.git`, `.env`, caches, or
   `vira_backup_legacy/`.
3. Initialize a fresh git repository from that exported tree.
4. Configure a public-facing git identity before the first commit.
5. Make a single clean initial commit and push it to the new public repository.
6. Enable GitHub private vulnerability reporting before announcing the project.

## Example Commands

```bash
mkdir -p ../vira-public
rsync -av \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.ruff_cache' \
  --exclude 'vira_backup_legacy' \
  ./ ../vira-public/

cd ../vira-public
git init
git checkout -b main
git config user.name "kagandms"
git config user.email "your-public-email@example.com"
git add .
git commit -m "Initial public release"
git remote add origin https://github.com/<account>/<public-repo>.git
git push -u origin main
```

## Pre-Public Checklist

- rotate any secrets that were ever stored outside version control but used in
  local backups or legacy directories
- verify that `vira_backup_legacy/` stays out of the exported public tree
- confirm that repository settings do not expose private issue templates,
  actions variables, or branch names you do not want public
- choose whether the project should remain source-available only or later move
  to an open-source license
