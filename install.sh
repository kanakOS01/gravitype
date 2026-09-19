#!/bin/sh
# Gravitype installer.
#
#   curl -LsSf https://raw.githubusercontent.com/kanakOS01/gravitype/main/install.sh | sh
#
# Installs the `gravitype` command into an isolated environment using uv
# (installing uv first if it is missing), falling back to pipx or pip.

set -eu

PKG="gravitype"
UV_INSTALLER="https://astral.sh/uv/install.sh"

info() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

install_uv() {
    info "uv not found, installing it first"
    if have curl; then
        curl -LsSf "$UV_INSTALLER" | sh
    elif have wget; then
        wget -qO- "$UV_INSTALLER" | sh
    else
        die "need curl or wget to install uv"
    fi

    # uv lands in one of these; pick it up for the rest of this script
    for d in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        [ -x "$d/uv" ] && PATH="$d:$PATH" && export PATH
    done

    have uv || die "uv installed but not on PATH; open a new shell and re-run"
}

main() {
    if have uv; then
        info "installing $PKG with uv"
        uv tool install --force "$PKG"
    elif have pipx; then
        info "installing $PKG with pipx"
        pipx install --force "$PKG"
    elif have curl || have wget; then
        install_uv
        info "installing $PKG with uv"
        uv tool install --force "$PKG"
    else
        die "no uv, pipx, curl or wget found"
    fi

    if have "$PKG"; then
        info "done - run: $PKG"
    else
        warn "$PKG installed but not on PATH yet"
        have uv && warn "run: uv tool update-shell"
        warn "then open a new shell and run: $PKG"
    fi
}

main "$@"
