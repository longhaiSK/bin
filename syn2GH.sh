#!/usr/bin/env bash

# ---------- Load PATH from your login/interactive config ----------
# We haven't enabled `set -u` yet; keep it that way while sourcing.
# Also relax -e during sourcing so harmless failures don't kill the script.
set +e

# If your PATH is defined in one of these, it will be loaded here.
for f in "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.profile"; do
  [ -f "$f" ] && . "$f"
done

set -e
export PATH

# ---------------------------------------------------------------

# -------------------------------------------------------

# ---------- Defaults ----------
: "${REPO_DIR:=/Users/lol553/Github}"   # not used below, kept for compatibility
: "${REMOTE:=origin}"
: "${BRANCH:=main}"
: "${GIT_SSH_COMMAND:=ssh}"
# -----------------------------

# Now enable nounset (after defaults are in place)
set -u

# ---------- Config ----------
# Update this if your repos live elsewhere on Syzygy (e.g., "$HOME/projects")
declare -a ROOTS=(
  "$HOME/Github"
)
EXCLUDE_REGEX='(/\.venv/|/node_modules/|/\.cargo/)'
# ----------------------------

# ---------- Colors ----------
C_BLUE=$'\033[0;34m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[0;33m'
C_RED=$'\033[0;31m'
C_NONE=$'\033[0m'
# ---------------------------

# ---------- Commit message ----------
if [[ -n "${1:-}" ]]; then
  COMMIT_MSG="$1"
else
  COMMIT_MSG="syn2GH.sh commit from $(hostname)"
fi
# -----------------------------------

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

  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo -e "${C_YELLOW}  ! Not a git repo (skipping)${C_NONE}"
    return
  fi

  local BRANCH_NAME
  BRANCH_NAME=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)
  if [[ -z "$BRANCH_NAME" ]]; then
    echo -e "${C_YELLOW}  ! Detached HEAD (skipping)${C_NONE}"
    return
  fi

  if ! git remote get-url origin >/dev/null 2>&1; then
    echo -e "${C_YELLOW}  ! No 'origin' remote (skipping)${C_NONE}"
    return
  fi

  local TRACKING_REF
  TRACKING_REF=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)
  if [[ -z "$TRACKING_REF" ]]; then
    local DEFAULT_REMOTE_BRANCH
    DEFAULT_REMOTE_BRANCH=$(git remote show origin 2>/dev/null | awk '/HEAD branch/ {print $NF}')
    if [[ -n "$DEFAULT_REMOTE_BRANCH" ]]; then
      if git branch --set-upstream-to="origin/${DEFAULT_REMOTE_BRANCH}" "$BRANCH_NAME" >/dev/null 2>&1; then
        TRACKING_REF="origin/${DEFAULT_REMOTE_BRANCH}"
      fi
    fi
  fi

  local OLD_HEAD NEW_HEAD
  OLD_HEAD=$(git rev-parse HEAD 2>/dev/null)
  git fetch origin >/dev/null 2>&1 || true
  if [[ -n "$TRACKING_REF" ]]; then
    if ! git pull --rebase --autostash origin "$BRANCH_NAME" >/dev/null 2>&1; then
      echo -e "${C_RED}  ! Pull failed. Resolve conflicts and re-run.${C_NONE}"
      errors+=("$repo_dir: pull failed")
      return
    fi
  fi
  NEW_HEAD=$(git rev-parse HEAD 2>/dev/null)
  if [[ "$OLD_HEAD" != "$NEW_HEAD" ]]; then
    echo -e "${C_BLUE}1) Pull:${C_GREEN} ↓ Changes pulled:${C_NONE}"
    git log --pretty=format:"      %C(yellow)%h%C(reset) - %s %C(cyan)(%an, %ar)%C(reset)" "$OLD_HEAD".."$NEW_HEAD"
  else
    echo -e "${C_BLUE}1) Pull:${C_GREEN} ✓ Up-to-date with remote.${C_NONE}"
  fi

  git add -A
  if ! git diff --staged --quiet; then
    echo -e "${C_BLUE}2) Stage:${C_GREEN} Staged diff:${C_NONE}"
    git diff --staged --stat | sed "s/.*/   ${C_RED}&${C_NONE}/"
  else
    echo -e "${C_BLUE}2) Stage:${C_GREEN} ✓ Nothing to stage.${C_NONE}"
  fi

  if ! git diff --staged --quiet; then
    local COMMIT_OUTPUT
    COMMIT_OUTPUT=$(git commit -m "$COMMIT_MSG" 2>&1) || {
      echo -e "${C_BLUE}3) Commit:${C_RED} ! Commit FAILED. Details:${C_NONE}"
      echo -e "$COMMIT_OUTPUT"
      errors+=("$repo_dir: commit failed")
      return
    }
    echo -e "${C_BLUE}3) Commit:${C_GREEN} ✓ Committed successfully.${C_NONE}"
  else
    echo -e "${C_BLUE}3) Commit:${C_GREEN} ✓ Nothing to commit.${C_NONE}"
  fi

  local TO_PUSH
  if [[ -n "$TRACKING_REF" ]]; then
    TO_PUSH=$(git log --pretty=format:"      %C(yellow)%h%C(reset) - %s %C(cyan)(%an, %ar)%C(reset)" "${TRACKING_REF}"..HEAD 2>/dev/null || true)
  else
    TO_PUSH=$(git log --pretty=format:"      %C(yellow)%h%C(reset) - %s %C(cyan)(%an, %ar)%C(reset)" "origin/$BRANCH_NAME"..HEAD 2>/dev/null || true)
  fi

  if [[ -n "$TO_PUSH" ]]; then
    local PUSH_OUTPUT
    if ! PUSH_OUTPUT=$(git push origin "$BRANCH_NAME" 2>&1); then
      echo -e "${C_BLUE}4) Push:${C_RED} ↑ Push FAILED. Details:${C_NONE}"
      echo -e "$TO_PUSH"
      echo -e "${C_RED}--- Git Error Output ---${C_NONE}"
      echo -e "$PUSH_OUTPUT"
      echo -e "${C_RED}------------------------${C_NONE}"
      errors+=("$repo_dir: push failed")
      return
    fi
    echo -e "${C_BLUE}4) Push:${C_GREEN} ✓ Pushed successfully.${C_NONE}"
  else
    echo -e "${C_BLUE}4) Push:${C_GREEN} ✓ Already in sync.${C_NONE}"
  fi
}

# ---------- Build repo list (no mapfile) ----------
declare -a all_git_dirs=()
for root in "${ROOTS[@]}"; do
  [[ -d "$root" ]] || continue
  tmp_file="$(mktemp)"
  find "$root" -type d -name .git -prune -print 2>/dev/null \
    | sed 's/\/\.git$//' \
    | grep -vE "${EXCLUDE_REGEX}" \
    | sort > "$tmp_file"
  last_line=""
  while IFS= read -r line; do
    if [[ "$line" != "$last_line" ]]; then
      all_git_dirs+=("$line")
      last_line="$line"
    fi
  done < "$tmp_file"
  rm -f "$tmp_file"
done

if [[ ${#all_git_dirs[@]} -eq 0 ]]; then
  echo -e "${C_YELLOW}No git repositories found under configured ROOTS.${C_NONE}"
  exit 0
fi

# ---------- Process each repo ----------
for repo in "${all_git_dirs[@]}"; do
  process_repo "$repo"
done

