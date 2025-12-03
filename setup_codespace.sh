#!/usr/bin/env bash

set -eu

# ---------- Colors ----------
C_BLUE=$'\033[0;34m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[0;33m'
C_RED=$'\033[0;31m'
C_NONE=$'\033[0m'
# ---------------------------

echo -e "${C_BLUE}--- Codespace Setup ---${C_NONE}"

# Check if git user.email is configured
if ! git config user.email > /dev/null 2>&1 || [ -z "$(git config user.email)" ]; then
    echo -e "${C_YELLOW}Git user not configured. Setting up...${C_NONE}"
    
    # Try to get email from GitHub via CLI if available
    if command -v gh &> /dev/null; then
        GH_EMAIL=$(gh api user --jq '.email' 2>/dev/null || echo "")
        if [ -n "$GH_EMAIL" ]; then
            git config --global user.email "$GH_EMAIL"
            GIT_NAME=$(gh api user --jq '.name' 2>/dev/null || echo "Codespace User")
            git config --global user.name "$GIT_NAME"
            echo -e "${C_GREEN}✓ Git configured with GitHub account info${C_NONE}"
        else
            git config --global user.email "$(whoami)@codespace.local"
            git config --global user.name "Codespace User"
            echo -e "${C_GREEN}✓ Git configured with default Codespace settings${C_NONE}"
        fi
    else
        git config --global user.email "$(whoami)@codespace.local"
        git config --global user.name "Codespace User"
        echo -e "${C_GREEN}✓ Git configured with default Codespace settings${C_NONE}"
    fi
else
    echo -e "${C_GREEN}✓ Git user already configured: $(git config user.name) <$(git config user.email)>${C_NONE}"
fi

# Verify SSH connection to GitHub
echo -e "${C_BLUE}Verifying GitHub SSH connection...${C_NONE}"
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo -e "${C_GREEN}✓ SSH connection to GitHub successful${C_NONE}"
elif ssh -T git@github.com 2>&1 | grep -q "Permission denied"; then
    echo -e "${C_YELLOW}⚠ SSH key not available, HTTPS will be used${C_NONE}"
else
    echo -e "${C_YELLOW}⚠ Could not verify SSH connection${C_NONE}"
fi

echo -e "\n${C_GREEN}--- Codespace setup completed ---${C_NONE}"
