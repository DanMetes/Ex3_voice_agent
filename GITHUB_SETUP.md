# 🧠 Voice Agent EX3 — GitHub Setup Guide

This document explains how to prepare, initialize, and push the **Voice Agent EX3** folder to GitHub so it’s fully versioned, CI-ready, and easy to collaborate on.

## 🔧 1. Prerequisites
- **Git** (https://git-scm.com/downloads)
- **VS Code** (https://code.visualstudio.com/)
- **Python 3.11+** (https://www.python.org/downloads/)
- **GitHub CLI (optional)**: `winget install GitHub.cli`

## 📁 2. Open the Project in VS Code
1. Unzip `voice_agent_ex3_github_ready.zip`.
2. Open **VS Code → File → Open Folder...** → select `voice_agent_ex3`.
3. You should see files like:
   ```
   main.py
   requirements.txt
   README.md
   .gitignore
   LICENSE
   client/
   src/
   ```

## 🧹 3. Check Hygiene Files (already included)
- `.gitignore` — ignores virtual envs, cache, audio artifacts, etc.
- `LICENSE` — MIT license
- `.editorconfig` — consistent formatting
- `.gitattributes` — enforces LF line endings
- `.vscode/settings.json` — local Python settings
- `.github/workflows/ci.yml` — GitHub Actions workflow for CI

## 🚀 4. Initialize Git
Open the VS Code **Terminal** (Ctrl+`) and run:
```bash
cd voice_agent_ex3
git init
git add .
git commit -m "feat: initial commit - EX3 voice agent project setup"
```

## 🌐 5. Create the Remote Repository
### Option A — Using GitHub CLI
```bash
# remove the stale lock dir mentioned in the error (path may differ); run as administrator in win power shell
Remove-Item 'C:\ProgramData\chocolatey\lib\03fa614411207ddb46e8aca6ad6abb2721319062' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'C:\ProgramData\chocolatey\lib\gh' -Recurse -Force -ErrorAction SilentlyContinue
choco upgrade chocolatey -y
choco install gh -y

gh auth login
# GitHub.com → HTTPS → login via browser
cd "C:\Users\danme\OneDrive\Desktop\AI Engeneering\EX3\"
gh repo create eEx3_voice_agent --source . --public --push

```
# Push netx changes
# See what changed
git status
# Stage your changes (use -A to include new/renamed/deleted files)
git add -A
# Commit them
git commit -m "Added new markdown files2"
# Update your local branch with remote (avoids push rejects)
git pull --rebase origin $(git rev-parse --abbrev-ref HEAD)
# Push your committed changes
git push origin HEAD


# I github repo renamed
# See current remotes
git remote -v
# Set origin to the NEW repo URL (HTTPS example)
git remote set-url origin https://github.com/DanMetes/Ex3_voice_agent.git
# (SSH example)
# git remote set-url origin git@github.com:<USER>/<NEW_REPO_NAME>.git
# Verify
git remote -v

### Option B — Using GitHub Website
1. Create a new repository `voice_agent_ex3` (no README/license/gitignore).
2. Then run:
```bash
git remote add origin https://github.com/<your-username>/voice_agent_ex3.git
git branch -M main
git push -u origin main
```

## 🧪 6. Verify GitHub Actions (CI)
After pushing, open the repo → **Actions** tab. The workflow **“CI”** should run on `main` and pass.

## 🧠 7. Recommended Next Steps
- Add shields to README:
  ```markdown
  ![CI](https://github.com/<your-username>/voice_agent_ex3/actions/workflows/ci.yml/badge.svg)
  ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
  ```
- Protect `main` (require PRs and passing CI).
- Add `DEVELOPMENT.md` (local run notes) and `CONTRIBUTING.md` (PR/branch conventions).
- Optional pre-commit: `black`, `ruff`, `isort`.

---

**Maintainer:** Dan  
**License:** MIT  
**Version:** 1.0 (Nov 2025)
