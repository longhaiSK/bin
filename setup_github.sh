echo
echo "Optional: you can add it with the GitHub CLI (if authenticated):"
#!/usr/bin/env bash
set -euo pipefail

# Add /workspaces/bin to PATH for current session
if ! echo "$PATH" | grep -q "/workspaces/bin"; then
	export PATH="/workspaces/bin:$PATH"
	echo "Added /workspaces/bin to PATH for this session."
else
	echo "/workspaces/bin already in PATH for this session."
fi

# Persist PATH addition in ~/.bashrc if not already present
if [ -w "$HOME" ]; then
	if ! grep -qx 'export PATH="/workspaces/bin:$PATH"' "$HOME/.bashrc" 2>/dev/null; then
		echo '' >> "$HOME/.bashrc"
		echo '# Add workspace bin to PATH' >> "$HOME/.bashrc"
		echo 'export PATH="/workspaces/bin:$PATH"' >> "$HOME/.bashrc"
		echo "Appended PATH export to ~/.bashrc"
	else
		echo "PATH export already present in ~/.bashrc"
	fi
fi

# Authenticate with GitHub CLI for all repos
echo "Starting GitHub CLI authentication..."
gh auth login --web

# Show authentication status
echo
gh auth status

echo
echo "You are now authenticated with GitHub CLI. You can push/pull to all your repos from this Codespace."
echo "Test with: git push --dry-run or gh repo list"
exit 0
