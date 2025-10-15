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
