#!/bin/sh

#!/usr/bin/env bash
set -euo pipefail

# Defaults
GITHUB_USER="longhaiSK"
DIR_ARG=""
FORCE=0

# Workspace root (env var 'githubroot' if set; else ~/Github)
GITHUB_ROOT="${githubroot:-$HOME/Github}"
mkdir -p "$GITHUB_ROOT"
cd "$GITHUB_ROOT"

print_usage() {
  cat <<'EOF'
Usage:
  init_git.sh <repo[/sub/dir]> [--user <github_user>|-u <github_user>] [--force|-f]

Examples:
  # Clone entire repo
  init_git.sh longhaiSK.github.io

  # Clone only a subdirectory via sparse-checkout
  init_git.sh longhaiSK.github.io/teaching/stat845_rdemo

  # Use a different GitHub username
  init_git.sh some-repo/path --user otherUser

  # Overwrite existing local folder if present
  init_git.sh longhaiSK.github.io/teaching/stat845_rdemo --force
EOF
}

# --- Parse args: first non-option is DIR_ARG ---
if [[ $# -eq 0 ]]; then
  echo "Error: missing <repo[/sub/dir]>."
  print_usage
  exit 1
fi

# Grab first non-option as DIR_ARG, then shift it away
case "${1:-}" in
  -*)
    echo "Error: first argument must be <repo[/sub/dir]>, not an option."
    print_usage
    exit 1
    ;;
  *)
    DIR_ARG="$1"
    shift
    ;;
esac

# Remaining options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --user|-u)
      [[ $# -ge 2 ]] || { echo "Error: --user requires a value"; exit 1; }
      GITHUB_USER="$2"; shift 2 ;;
    --force|-f)
      FORCE=1; shift ;;
    -h|--help)
      print_usage; exit 0 ;;
    *)
      echo "Unknown option: $1"
      print_usage; exit 1 ;;
  esac
done

# Normalize DIR_ARG (tolerate accidental leading './' or '/')
DIR_ARG="${DIR_ARG#./}"
DIR_ARG="${DIR_ARG#/}"

# Split DIR_ARG into repo and optional subpath
REPO="${DIR_ARG%%/*}"
SUBPATH=""
if [[ "$DIR_ARG" == */* ]]; then
  SUBPATH="${DIR_ARG#*/}"
fi

CLONE_DIR="$REPO"

# Handle pre-existing directory
if [[ -e "$CLONE_DIR" ]]; then
  if [[ $FORCE -eq 1 ]]; then
    echo "Removing existing '$CLONE_DIR' (because --force was provided)..."
    rm -rf -- "$CLONE_DIR"
  else
    echo "Error: '$CLONE_DIR' already exists. Use --force to overwrite."
    exit 2
  fi
fi

# Clone with minimal history and no checkout
echo "Cloning git@github.com:${GITHUB_USER}/${REPO}.git into '$CLONE_DIR'..."
git clone --depth 1 --no-checkout "git@github.com:${GITHUB_USER}/${REPO}.git" "$CLONE_DIR"

cd "$CLONE_DIR"

# If a subpath is requested, configure sparse-checkout
if [[ -n "$SUBPATH" ]]; then
  echo "Configuring sparse-checkout for path: '$SUBPATH'"
  git sparse-checkout init --cone
  git sparse-checkout set "$SUBPATH"
fi

# Materialize files
echo "Checking out files..."
git checkout

echo "Done."
if [[ -n "$SUBPATH" ]]; then
  echo "Fetched subdirectory: $SUBPATH"
else
  echo "Fetched entire repository."
fi
echo "Location: $GITHUB_ROOT/$CLONE_DIR"

