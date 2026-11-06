#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail

if [[ "${1:-}" == "--help" && $# -eq 1 ]]; then
  echo "Usage: sudo ./uninstall.sh (removes the DKMS module for all kernels, updates the initramfs and reloads cdc_ncm)"
  exit 0
fi
[[ $# -eq 0 ]] || { echo "Error: unexpected arguments; use --help." >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo "Error: Linux is required." >&2; exit 1; }
[[ "$(id -u)" -eq 0 ]] || { echo "Error: run with sudo." >&2; exit 1; }

# The initramfs carries a copy of cdc_ncm that loads before the root filesystem,
# so it must be rebuilt for the boot to use the module now in /lib/modules.
rebuild_initramfs() {
  if command -v update-initramfs >/dev/null; then
    update-initramfs -u -k "$1"
  elif command -v dracut >/dev/null; then
    if [[ "$1" == all ]]; then dracut -f --regenerate-all; else dracut -f --kver "$1"; fi
  else
    echo "Warning: no update-initramfs or dracut; rebuild the initramfs manually." >&2
  fi
}

# Swap the running cdc_ncm for the one modprobe now resolves. Modules that depend
# on it (such as cdc_mbim) are unloaded first and loaded again afterwards.
reload_cdc_ncm() {
  local holders=()
  [[ -d /sys/module/cdc_ncm/holders ]] && mapfile -t holders < <(ls /sys/module/cdc_ncm/holders)
  if modprobe -r "${holders[@]}" cdc_ncm && modprobe cdc_ncm && { (( ${#holders[@]} == 0 )) || modprobe -a "${holders[@]}"; }; then
    echo "Reloaded cdc_ncm: $(modinfo -n cdc_ncm)"
  else
    echo "Warning: cdc_ncm could not be reloaded while in use; reboot to load it." >&2
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="${SCRIPT_DIR}/dkms.conf"
for tool in dkms modprobe modinfo; do
  command -v "$tool" >/dev/null || { echo "Error: missing command: $tool" >&2; exit 1; }
done
PKG_NAME="$(sed -n 's/^PACKAGE_NAME="\(.*\)"$/\1/p' "$CONF")"
PKG_VERSION="$(sed -n 's/^PACKAGE_VERSION="\(.*\)"$/\1/p' "$CONF")"
[[ -n "$PKG_NAME" && -n "$PKG_VERSION" ]] || { echo "Error: unable to read dkms.conf." >&2; exit 1; }
[[ -n "$(dkms status "${PKG_NAME}/${PKG_VERSION}")" ]] || {
  echo "Error: ${PKG_NAME}/${PKG_VERSION} is not registered with DKMS." >&2
  exit 1
}
dkms remove "${PKG_NAME}/${PKG_VERSION}" --all
rm -rf -- "/usr/src/${PKG_NAME}-${PKG_VERSION}"
echo "Removed ${PKG_NAME}/${PKG_VERSION} from DKMS."
rebuild_initramfs all
reload_cdc_ncm
echo "Network configuration is not removed."
