#!/bin/zsh
#
# Add pattern(s) to .gitignore, remove tracked files matching the NEW patterns
# (only those not already in .gitignore), commit the changes, and print
# a message telling you how to push.
#
# Usage:
#   ./git_ignore_and_clean.zsh [--repo] [--quarto] <pattern1> [pattern2 ...]
#
# Examples:
#   ./git_ignore_and_clean.zsh "*.log"
#   ./git_ignore_and_clean.zsh --repo "data/*.csv"
#   ./git_ignore_and_clean.zsh --repo --quarto
#
# Note: This script assumes you are in a Git repository and are authenticated to push.

# Check if the repository is clean before starting
if ! git diff-index --quiet HEAD --; then
    echo "🚨 Error: Your working directory is not clean. Please commit or stash your changes before running this script."
    exit 1
fi

function ignore_and_clean() {
    local repo_mode=false
    local quarto_mode=false

    # ------------------ Parse options ------------------
    while [[ "$1" == --* ]]; do
        case "$1" in
            --repo)
                repo_mode=true
                shift
                ;;
            --quarto)
                quarto_mode=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--repo] [--quarto] <pattern1> [pattern2 ...]"
                echo "  --repo    Use the repository root .gitignore (repo-level), not the cwd .gitignore."
                echo "  --quarto  Add common Quarto scratch patterns (_freeze/, _cache/, .quarto/, _extensions/, figure-pdf/)."
                return 0
                ;;
            *)
                echo "🚨 Error: Unknown option: $1"
                echo "Usage: $0 [--repo] [--quarto] <pattern1> [pattern2 ...]"
                return 1
                ;;
        esac
    done

    # Remaining args are user-specified patterns (may be empty if --quarto is used)
    local -a user_patterns=("$@")
    local -a all_patterns=()

    # Built-in Quarto scratch patterns (figure-html/ removed as requested)
    if $quarto_mode; then
        local -a quarto_patterns=(
            "_freeze/"
            "_cache/"
            ".quarto/"
            "_extensions/"
            "figure-pdf/"
        )
        all_patterns+=("${quarto_patterns[@]}")
    fi

    # Add any user-provided patterns
    all_patterns+=("${user_patterns[@]}")

    # Need at least one pattern total
    if (( ${#all_patterns[@]} == 0 )); then
        echo "🚨 Error: You must provide at least one pattern, or use --quarto."
        echo "Usage: $0 [--repo] [--quarto] <pattern1> [pattern2 ...]"
        return 1
    fi

    # ------------------ Determine repo root / gitignore path ------------------
    local gitignore_file
    local did_pushd=false

    if $repo_mode; then
        local repo_root
        repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
        if [[ $? -ne 0 || -z "$repo_root" ]]; then
            echo "❌ Failed to determine repository root. Are you inside a Git repository?"
            return 1
        fi
        echo "🔧 Mode: repo-level .gitignore"
        echo "Repo root: $repo_root"

        # Work from repo root so paths are consistent
        pushd "$repo_root" >/dev/null || {
            echo "❌ Failed to cd to repo root: $repo_root"
            return 1
        }
        did_pushd=true
        gitignore_file=".gitignore"
    else
        gitignore_file=".gitignore"
        echo "🔧 Mode: folder-level .gitignore (current directory)"
    fi

    echo "Using .gitignore: $gitignore_file"
    echo "--- Starting Git Ignore and Clean Workflow ---"
    echo "Patterns requested:"
    printf '   - %s\n' "${all_patterns[@]}"

    # Ensure .gitignore exists (before reading)
    if [[ ! -f "$gitignore_file" ]]; then
        touch "$gitignore_file"
    fi

    # ------------------ Identify NEW patterns ------------------
    local -a new_patterns=()
    local pattern

    echo "\n>>> 1. Determining which patterns are NEW (not already in .gitignore)..."

    for pattern in "${all_patterns[@]}"; do
        if grep -qxF -- "$pattern" "$gitignore_file" 2>/dev/null; then
            echo "   ✅ Already present: $pattern"
        else
            echo "   ➕ New pattern: $pattern"
            new_patterns+=("$pattern")
        fi
    done

    if (( ${#new_patterns[@]} == 0 )); then
        echo "ℹ️ No new patterns to add. Only deduping .gitignore and committing if needed."
    fi

    # ------------------ 2. Remove tracked files for NEW patterns only ------------------
    echo "\n>>> 2. Removing tracked files matching NEW patterns (git rm --cached)..."

    local -a files_to_untrack=()
    local f

    for pattern in "${new_patterns[@]}"; do
        while IFS= read -r f; do
            [[ -z "$f" ]] && continue
            files_to_untrack+=("$f")
        done < <(git ls-files --cached -- "$pattern")
    done

    # Deduplicate file list
    if (( ${#files_to_untrack[@]} > 0 )); then
        local -A seen_files
        local -a unique_files=()
        for f in "${files_to_untrack[@]}"; do
            [[ -n "${seen_files[$f]}" ]] && continue
            seen_files[$f]=1
            unique_files+=("$f")
        done

        echo "Found the following tracked files to remove from index (retaining local copy):"
        printf '   - %s\n' "${unique_files[@]}"

        git rm --cached -- "${unique_files[@]}"
        if [[ $? -eq 0 ]]; then
            echo "✅ Successfully removed matching files from Git index for NEW patterns."
        else
            echo "❌ git rm failed. Please review the previous error messages."
            $did_pushd && popd >/dev/null
            return 1
        fi
    else
        echo "✅ No tracked files found matching the NEW patterns. Skipping 'git rm --cached'."
    fi

    # ------------------ 3. Update .gitignore (append NEW patterns, then dedupe) ------------------
    echo "\n>>> 3. Updating .gitignore (append NEW patterns, then deduplicate)..."

    for pattern in "${new_patterns[@]}"; do
        echo "   ➕ Appending: $pattern"
        echo "$pattern" >> "$gitignore_file"
    done

    # Deduplicate .gitignore
    echo "   🧹 Deduplicating $gitignore_file..."
    local tmpfile
    tmpfile="${gitignore_file}.tmp.$$"
    awk '!seen[$0]++' "$gitignore_file" > "$tmpfile" && mv "$tmpfile" "$gitignore_file"

    git add "$gitignore_file"
    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to stage $gitignore_file."
        $did_pushd && popd >/dev/null
        return 1
    fi

    # ------------------ 4. Commit ------------------
    echo "\n>>> 4. Committing changes..."

    if git diff --cached --quiet --exit-code; then
        echo "⚠️ No staged changes detected to commit. Exiting commit phase."
    else
        # build commit message summarizing all patterns requested
        local joined_patterns
        joined_patterns=$(printf "%s, " "${all_patterns[@]}")
        joined_patterns=${joined_patterns%, }   # strip trailing ", "
        local commit_msg="chore: Ignore patterns: $joined_patterns and remove already-tracked instances (new patterns only)."

        git commit -m "$commit_msg"
        if [[ $? -eq 0 ]]; then
            echo "✅ Successfully committed with message:"
            echo "   $commit_msg"
        else
            echo "❌ Git commit failed."
            $did_pushd && popd >/dev/null
            return 1
        fi
    fi

    # ------------------ 5. Print push instructions (NO automatic push) ------------------
    echo "\n>>> 5. Push instructions (no automatic push performed)."

    # Try to infer whether main or master exists, just for a helpful hint
    local remote_branch_hint="main"
    if ! git show-ref --verify --quiet refs/remotes/origin/main && \
       ! git show-ref --verify --quiet refs/heads/main; then
        if git show-ref --verify --quiet refs/remotes/origin/master || \
           git show-ref --verify --quiet refs/heads/master; then
            remote_branch_hint="master"
        fi
    fi

    echo "👉 To push these changes, run (adjust branch if needed):"
    echo "   git push origin $remote_branch_hint"

    echo "\n--- Workflow Complete ---"

    $did_pushd && popd >/dev/null
}

# Execute the function with the provided arguments
ignore_and_clean "$@"
