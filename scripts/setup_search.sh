#!/bin/bash
# setup_search.sh - Optional search tool setup for GSD
#
# This script checks for and optionally installs search tools.
# GSD works without these tools (falls back to grep), but they improve performance.

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " GSD ► Search Tools Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# check_ripgrep checks whether ripgrep is installed and reports its availability and version.
check_ripgrep() {
    if command -v rg &> /dev/null; then
        echo "✅ ripgrep (rg) is installed: $(rg --version | head -n1)"
        return 0
    else
        echo "❌ ripgrep (rg) is not installed"
        return 1
    fi
}

# check_fd checks whether fd or its fdfind executable is available and reports its version.
check_fd() {
    if command -v fd &> /dev/null; then
        echo "✅ fd is installed: $(fd --version)"
        return 0
    elif command -v fdfind &> /dev/null; then
        echo "✅ fd is installed (as fdfind): $(fdfind --version)"
        return 0
    else
        echo "❌ fd is not installed"
        return 1
    fi
}

# suggest_install prints platform-specific installation instructions for ripgrep and fd.
suggest_install() {
    echo ""
    echo "───────────────────────────────────────────────────────"
    echo "📦 Installation Options"
    echo "───────────────────────────────────────────────────────"
    echo ""
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS detected. Install with Homebrew:"
        echo "  brew install ripgrep fd"
    elif [[ -f /etc/debian_version ]]; then
        echo "Debian/Ubuntu detected. Install with apt:"
        echo "  sudo apt install ripgrep fd-find"
        echo "  # Note: fd is installed as 'fdfind' on Debian"
    elif [[ -f /etc/fedora-release ]]; then
        echo "Fedora detected. Install with dnf:"
        echo "  sudo dnf install ripgrep fd-find"
    elif [[ -f /etc/arch-release ]]; then
        echo "Arch Linux detected. Install with pacman:"
        echo "  sudo pacman -S ripgrep fd"
    else
        echo "Install from source or package manager:"
        echo "  ripgrep: https://github.com/BurntSushi/ripgrep"
        echo "  fd: https://github.com/sharkdp/fd"
    fi
    
    echo ""
    echo "───────────────────────────────────────────────────────"
}

# Main
echo "Checking search tools..."
echo ""

RG_OK=0
FD_OK=0

check_ripgrep && RG_OK=1
check_fd && FD_OK=1

echo ""

if [[ $RG_OK -eq 1 && $FD_OK -eq 1 ]]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " ✅ All search tools are ready!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "You can use ./scripts/search_repo.sh for optimized searching."
    exit 0
else
    echo "⚠️  Some tools are missing (optional)"
    echo ""
    echo "GSD will work fine with built-in grep, but ripgrep and fd"
    echo "provide faster searching in large codebases."
    
    suggest_install
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " GSD ► Using grep as fallback (works fine!)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
fi
