#!/bin/sh
set -e

# ---------------------------
# 0) Dotfiles (.bashrc/.bash_profile)
# ---------------------------
cat > "$HOME/.bashrc" <<'EOF'
export githubroot="$HOME/Github"
export PATH="$githubroot/bin/:$HOME/bin/:$PATH"
EOF

cat > "$HOME/.bash_profile" <<'EOF'
# Load ~/.bashrc for interactive login shells
case $- in *i*) [ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc" ;; esac
EOF

# Make the vars available to THIS run too
. "$HOME/.bashrc"
# Refresh Bash's command lookup cache (no-op in plain sh, harmless)
hash -r 2>/dev/null || true

# ---------------------------
# 1) Clone bin (HTTPS) then switch remote to SSH
# ---------------------------
mkdir -p "$githubroot"
if [ ! -d "$githubroot/bin/.git" ]; then
  echo "Cloning https://github.com/longhaiSK/bin.git -> $githubroot/bin ..."
  git clone https://github.com/longhaiSK/bin.git "$githubroot/bin"
else
  echo "Repo already exists at $githubroot/bin"
fi

echo "Setting remote to SSH (git@github.com:longhaiSK/bin.git) ..."
git -C "$githubroot/bin" remote set-url origin git@github.com:longhaiSK/bin.git || true

# Ensure new PATH is active for current shell session
hash -r 2>/dev/null || true

# ---------------------------
# 2) Git identity
# ---------------------------
GIT_NAME="Longhai Li"
GIT_EMAIL="longhai.li@usask.ca"
git config --global user.name  "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
git config --global init.defaultBranch main
git config --global pull.rebase false

# ---------------------------
# 3) SSH key: create if missing, add to agent, show public key
# ---------------------------
mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
KEY="$HOME/.ssh/id_ed25519"
PUB="$KEY.pub"

if [ -f "$KEY" ]; then
  echo "SSH key already exists: $KEY"
else
  echo "Generating ed25519 key at $KEY ..."
  ssh-keygen -t ed25519 -C "$GIT_EMAIL" -N "" -f "$KEY"
fi

# Start agent if needed; add key (best effort)
eval "$(ssh-agent -s)" >/dev/null 2>&1 || true
ssh-add "$KEY" >/dev/null 2>&1 || true

echo
echo "===== PUBLIC KEY — copy the next line into GitHub (Settings → SSH and GPG keys) ====="
cat "$PUB"
echo "===== END PUBLIC KEY ====="
echo

# ---------------------------
# 4) Finalize: ensure current shell sees bin commands NOW,
#    and (optionally) re-exec a clean login Bash once.
# ---------------------------
# Source again (idempotent) and refresh hash so new PATH is live
. "$HOME/.bashrc"
hash -r 2>/dev/null || true

# Optional: replace current shell with a login Bash so everything behaves
# like a fresh terminal. Skip if RELOADED_ONCE is set to avoid loops.
if command -v bash >/dev/null 2>&1; then
  if [ -z "${RELOADED_ONCE:-}" ]; then
    export RELOADED_ONCE=1
    echo "Reopening as a login shell (bash -l) so PATH/githubroot are fully applied ..."
    exec bash -l
  fi
fi

echo "Done. If commands in bin aren't found, try: hash -r"
