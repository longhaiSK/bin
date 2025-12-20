#!/usr/bin/env bash

# Use nounset (exit on unset vars)
set -u

# ---------- Configuration ----------
# Auto-detect folder name (GitHub vs Github vs github)
if [ -d "${HOME}/GitHub" ]; then
    SEARCH_ROOT="${HOME}/GitHub"
elif [ -d "${HOME}/Github" ]; then
    SEARCH_ROOT="${HOME}/Github"
elif [ -d "${HOME}/github" ]; then
    SEARCH_ROOT="${HOME}/github"
else
    SEARCH_ROOT="${HOME}/Github" # Fallback
fi

# ---------- Argument Parsing ----------
SYNC_ALL=false
if [[ "${1:-}" == "-a" ]]; then
    SYNC_ALL=true
    shift # Remove -a from the arguments list
fi

# The first remaining argument is the commit message
COMMIT_MSG="${1:-git_sync from $(hostname)}"

# ---------- Colors ----------
C_BLUE=$'\033[0;34m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[0;33m'
C_RED=$'\033[0;31m'
C_NONE=$'\033[0m'
C_CYAN=$'\033[0;36m'
# -----------------------------

# Function to process a single repository
process_repo() {
    local repo_path="$1"
    
    # Use a subshell to avoid changing the directory of the main script
    (
        cd "$repo_path" || exit 1

        echo -e "\n${C_CYAN}-------------------------------------------------------${C_NONE}"
        echo -e "${C_CYAN}Repo: ${C_YELLOW}${repo_path}${C_NONE}"
        
        # Check if inside git tree
        if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            echo -e "${C_RED}Error: Not a git repository.${C_NONE}"
            exit 1
        fi

        # 0) Auto-convert HTTPS to SSH (Github only)
        local remote_url
        remote_url=$(git remote get-url origin 2>/dev/null || true)

        if [[ "$remote_url" == https://github.com/* ]]; then
            echo -e "${C_BLUE}0) Converting HTTPS to SSH...${C_NONE}"
            local user_repo="${remote_url#https://github.com/}"
            local ssh_url="git@github.com:${user_repo}"
            
            if git remote set-url origin "$ssh_url"; then
                echo -e "${C_GREEN}   ✓ Remote updated to SSH.${C_NONE}"
            else
                echo -e "${C_RED}   ! Failed to update remote.${C_NONE}"
            fi
        fi

        # Determine branch
        local BRANCH_NAME
        BRANCH_NAME=$(git symbolic-ref --quiet --short HEAD 2>/dev/null)
        
        if [ -z "$BRANCH_NAME" ]; then
            echo -e "${C_RED}Error: Detached HEAD or no branch found.${C_NONE}"
            exit 1
        fi

        # 1) Pull
        echo -e "${C_BLUE}1) Pulling changes from origin/${BRANCH_NAME}...${C_NONE}"
        if ! git pull --rebase --autostash origin "$BRANCH_NAME"; then
            echo -e "${C_RED}Pull failed (Conflict?). Skipping rest of sync.${C_NONE}"
            exit 1
        fi

        # 2) Stage
        echo -e "${C_BLUE}2) Staging all changes...${C_NONE}"
        git add -A

        # 3) Commit
        if git diff --staged --quiet; then
            echo -e "${C_BLUE}3) Commit: ${C_GREEN}Nothing to commit.${C_NONE}"
        else
            echo -e "${C_BLUE}3) Committing with message: \"${COMMIT_MSG}\"${C_NONE}"
            if ! git commit -m "$COMMIT_MSG"; then
                 echo -e "${C_RED}Commit failed.${C_NONE}"
                 exit 1
            fi
        fi

        # 4) Push
        echo -e "${C_BLUE}4) Pushing to origin/${BRANCH_NAME}...${C_NONE}"
        if ! git push origin "$BRANCH_NAME"; then
            echo -e "${C_RED}Push failed. Check connection/permissions.${C_NONE}"
            exit 1
        fi
        
        echo -e "${C_GREEN}✓ Sync completed for $(basename "$repo_path")${C_NONE}"
    )
}

# --- Execution Logic ---

if [ "$SYNC_ALL" = true ]; then
    echo -e "${C_GREEN}=== Starting Batch Git Sync (ALL) in: ${SEARCH_ROOT} ===${C_NONE}"
    
    # Find all directories containing .git and process them
    find "$SEARCH_ROOT" -maxdepth 3 -type d -name ".git" -prune | sort | while read -r gitdir; do
        repo_root=$(dirname "$gitdir")
        process_repo "$repo_root"
    done
    echo -e "\n${C_GREEN}=== All Repositories Processed ===${C_NONE}"
else
    # Default mode: Sync only the current repository
    echo -e "${C_GREEN}=== Syncing Current Repository ===${C_NONE}"
    
    # Get the root of the current git repo
    CURRENT_REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
    
    if [ -n "$CURRENT_REPO_ROOT" ]; then
        process_repo "$CURRENT_REPO_ROOT"
    else
        echo -e "${C_RED}Error: You are not inside a git repository.${C_NONE}"
        echo -e "${C_YELLOW}Use '-a' to sync all repositories in ${SEARCH_ROOT}${C_NONE}"
        exit 1
    fi
fi