#!/bin/sh
set -e

# Write the two files
cat > "$HOME/.bashrc" <<'EOF'
export githubroot="/cloud/project/Github"
export PATH="$githubroot/bin/:$HOME/bin/:$PATH"
EOF

cat > "$HOME/.bash_profile" <<'EOF'
# Load ~/.bashrc for interactive login shells
case $- in *i*) [ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc" ;; esac
EOF

# Clone via HTTPS then switch to SSH
githubroot="/cloud/project/Github"
mkdir -p "$githubroot"
[ -d "$githubroot/bin/.git" ] || git clone https://github.com/longhaiSK/bin.git "$githubroot/bin"
git -C "$githubroot/bin" remote set-url origin git@github.com:longhaiSK/bin.git

# Apply immediately in this shell
. "$HOME/.bash_profile"

#!/bin/sh
set -e

# ---- Settings ----
GIT_NAME="Longhai Li"
GIT_EMAIL="longhai.li@usask.ca"
KEY="$HOME/.ssh/id_ed25519"
PUB="$KEY.pub"

# ---- Ensure ~/.ssh exists with correct perms ----
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# ---- Create key if absent ----
if [ -f "$KEY" ]; then
  echo "SSH key already exists: $KEY"
else
  echo "Generating ed25519 key at $KEY ..."
  ssh-keygen -t ed25519 -C "$GIT_EMAIL" -N "" -f "$KEY"
fi

# ---- Start agent (if needed) and add key ----
eval "$(ssh-agent -s)" >/dev/null 2>&1 || true
ssh-add "$KEY" >/dev/null 2>&1 || true

# ---- Set global Git identity (idempotent) ----
git config --global user.name  "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"

# (Optional, nice defaults)
git config --global init.defaultBranch main
git config --global pull.rebase false

# ---- Show public key to copy to GitHub ----
echo
echo "===== PUBLIC KEY — copy everything on the next line into GitHub (Settings → SSH and GPG keys) ====="
cat "$PUB"
echo "===== END PUBLIC KEY ====="
echo
echo "After adding the key on GitHub, you can test with:  ssh -T git@github.com"
echo "Current Git identity:"
git config --global --get user.name
git config --global --get user.email

