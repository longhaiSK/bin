#!/usr/bin/env bash

# ---------- Defaults & Argument Parsing ----------
COMMIT_MSG="syn2GH.sh commit from $(hostname)"
discard_changes=false

# Loop through all arguments to find the commit message and --discard flag
for arg in "$@"; do
  if [[ "$arg" == "--discard" ]]; then
    discard_changes=true
  else
    # Assume the first non-flag argument is the commit message
    if [[ "$COMMIT_MSG" == "syn2GH.sh commit from $(hostname)" ]]; then
        COMMIT_MSG="$arg"
    fi
  fi
done
# -----------------------------------------------

# Enable strict mode
set -u

# ---------- Config ----------
declare -a ROOTS=("${githubroot:-$HOME/Github}")

EXCLUDE_REGEX='(/\.venv/|/node_modules/|/\.cargo/)'
# ----------------------------

# ---------- Colors ----------
C_BLUE=$'\033[0;34m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[0;33m'
C_RED=$'\033[0;31m'
C_NONE=$'\033[0m'
# ---------------------------

# ---------- Header with timestamp ----------
START_TS="$(TZ='America/Regina' date '+%Y-%m-%d %H:%M:%S %Z')"
echo -e "${C_BLUE}syn2GH.sh start:${C_NONE} ${C_YELLOW}${START_TS}${C_NONE} on ${C_GREEN}$(hostname)${C_NONE}"
# ------------------------------------------

declare -a errors=()

process_repo() {
  local repo_dir="$1"
  echo
  echo -e "${C_BLUE}Repo: ${C_YELLOW}${repo_dir}${C_NONE}"

  cd "$repo_dir" || { echo -e "${C_RED}  ! Cannot enter directory${C_NONE}"; errors+=("$repo_dir: cd failed"); return; }

  # Basic Git repo checks (unchanged)
  if ! git rev-parse --git-dir >/dev/null 2>&1; then echo -e "${C_YELLOW}  ! Not a git repo (skipping)${C_NONE}"; return; fi
  local BRANCH_NAME
  BRANCH_NAME=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)
  if [[ -z "$BRANCH_NAME" ]]; then echo -e "${C_YELLOW}  ! Detached HEAD (skipping)${C_NONE}"; return; fi
  if ! git remote get-url origin >/dev/null 2>&1; then echo -e "${C_YELLOW}  ! No 'origin' remote (skipping)${C_NONE}"; return; fi

  local OLD_HEAD NEW_HEAD
  OLD_HEAD=$(git rev-parse HEAD 2>/dev/null)
  
  echo -e "${C_BLUE}1) Pull:${C_NONE} Attempting to pull with rebase..."

  # --- MODIFIED CONFLICT HANDLING BLOCK ---
  if ! git pull --rebase --autostash origin "$BRANCH_NAME" >/dev/null 2>&1; then
    # This block runs ONLY if the pull failed.
    
    if [[ "$discard_changes" == true ]]; then
      # --- SCENARIO 1: --discard flag is used ---
      echo -e "${C_YELLOW}  ! --discard flag detected. Automatically discarding local changes...${C_NONE}"
      git rebase --abort &>/dev/null || true
      git fetch origin >/dev/null 2>&1
      git reset --hard "origin/${BRANCH_NAME}" >/dev/null 2>&1
      echo -e "${C_GREEN}  ✓ Successfully reset local branch to match the remote.${C_NONE}"
    else
      # --- SCENARIO 2: Default behavior on conflict ---
      echo -e "${C_RED}  ! Pull failed due to a conflict in the following files:${C_NONE}"
      
      # Use 'git diff' to get a reliable list of unmerged (conflicted) files.
      while IFS= read -r file; do
          echo -e "${C_YELLOW}    - ${file}${C_NONE}"
      done < <(git diff --name-only --diff-filter=U)

      echo -e "${C_BLUE}  Please resolve these conflicts manually OR re-run with the --discard option.${C_NONE}"
      
      # Abort the rebase to leave the repo in a clean, pre-pull state.
      git rebase --abort &>/dev/null || true
      
      errors+=("$repo_dir: pull conflict")
      return
    fi
  fi
  # --- END OF MODIFIED BLOCK ---

  # The rest of the script continues as before...
  NEW_HEAD=$(git rev-parse HEAD 2>/dev/null)
  if [[ "$OLD_HEAD" != "$NEW_HEAD" ]]; then
    echo -e "${C_GREEN}  ↓ Changes were pulled or repo was reset.${C_NONE}"
  else
    echo -e "${C_GREEN}  ✓ Up-to-date with remote.${C_NONE}"
  fi

  git add -A
  if ! git diff --staged --quiet; then
    echo -e "${C_BLUE}2) Stage:${C_GREEN} Staged diff present.${C_NONE}"
  else
    echo -e "${C_BLUE}2) Stage:${C_GREEN} ✓ Nothing to stage.${C_NONE}"
  fi

  if ! git diff --staged --quiet; then
    git commit -m "$COMMIT_MSG" >/dev/null 2>&1 && echo -e "${C_BLUE}3) Commit:${C_GREEN} ✓ Committed successfully.${C_NONE}" || echo -e "${C_BLUE}3) Commit:${C_RED} ! Commit FAILED.${C_NONE}"
  else
    echo -e "${C_BLUE}3) Commit:${C_GREEN} ✓ Nothing to commit.${C_NONE}"
  fi

  if git log "origin/${BRANCH_NAME}"..HEAD &>/dev/null; then
      if git push origin "$BRANCH_NAME" >/dev/null 2>&1; then
          echo -e "${C_BLUE}4) Push:${C_GREEN} ✓ Pushed successfully.${C_NONE}"
      else
          echo -e "${C_BLUE}4) Push:${C_RED} ↑ Push FAILED.${C_NONE}"
          errors+=("$repo_dir: push failed")
      fi
  else
      echo -e "${C_BLUE}4) Push:${C_GREEN} ✓ Already in sync.${C_NONE}"
  fi
}

# --- This part is unchanged ---
# Build and process repo list
declare -a all_git_dirs=()
for root in "${ROOTS[@]}"; do
  [[ -d "$root" ]] || continue
  while IFS= read -r dir; do
    [[ -n "$dir" ]] && all_git_dirs+=("$dir")
  done < <(find "$root" -type d -name .git -prune -print 2>/dev/null | sed 's#/\.git$##' | grep -vE "${EXCLUDE_REGEX}" | sort)
done
if [[ ${#all_git_dirs[@]} -eq 0 ]]; then echo -e "${C_YELLOW}No git repositories found.${C_NONE}"; exit 0; fi
for repo in "${all_git_dirs[@]}"; do process_repo "$repo"; done
if [[ ${#errors[@]} -gt 0 ]]; then
    echo -e "\n${C_RED}--- SCRIPT FINISHED WITH ERRORS ---${C_NONE}"; for err in "${errors[@]}"; do echo -e "${C_RED}- ${err}${C_NONE}"; done; exit 1
fi
echo -e "\n${C_GREEN}--- SCRIPT FINISHED SUCCESSFULLY ---${C_NONE}"