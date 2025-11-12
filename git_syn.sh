#!/usr/bin/env bash

set -eu # Exit on error, exit on unset variable

# ---------- Colors & Commit Message ----------
C_BLUE=$'\033[0;34m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[0;33m'
C_RED=$'\033[0;31m'
C_NONE=$'\033[0m'
COMMIT_MSG="${1:-git_syn.sh from $(hostname)}"
# ---------------------------------------------

echo -e "${C_BLUE}--- Starting Git Sync for current directory ---${C_NONE}"

# Check if we are in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${C_RED}Error: Not a git repository.${C_NONE}"
    exit 1
fi

# --- Git Logic (pull, stage, commit, push) ---
BRANCH_NAME=$(git symbolic-ref --quiet --short HEAD)

echo -e "${C_BLUE}1) Pulling changes from origin...${C_NONE}"
if ! git pull --rebase --autostash origin "$BRANCH_NAME"; then
    echo -e "${C_RED}Pull failed. Please resolve conflicts manually.${C_NONE}"
    exit 1
fi

echo -e "${C_BLUE}2) Staging all changes...${C_NONE}"
git add -A

if git diff --staged --quiet; then
    echo -e "${C_BLUE}3) Commit: ${C_GREEN}Nothing to commit.${C_NONE}"
else
    echo -e "${C_BLUE}3) Committing with message: \"${COMMIT_MSG}\"${C_NONE}"
    git commit -m "$COMMIT_MSG"
fi

echo -e "${C_BLUE}4) Pushing to origin...${C_NONE}"
if ! git push origin "$BRANCH_NAME"; then
    echo -e "${C_RED}Push failed. Please check remote connection and permissions.${C_NONE}"
    exit 1
fi

echo -e "\n${C_GREEN}--- Sync completed successfully. ---${C_NONE}"
