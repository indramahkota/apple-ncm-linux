#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail

if [[ "${1:-}" == "--help" && $# -eq 1 ]]; then
  echo "Usage: sudo ./uninstall.sh (removes the override for the running kernel; reboot afterwards)"
  exit 0
fi
[[ $# -eq 0 ]] || { echo "Error: unexpected arguments; use --help." >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo "Error: Linux is required." >&2; exit 1; }
[[ "$(id -u)" -eq 0 ]] || { echo "Error: run with sudo." >&2; exit 1; }
KVERSION="$(uname -r)"
TARGET="/lib/modules/${KVERSION}/updates/cdc_ncm.ko"
command -v depmod >/dev/null || { echo "Error: depmod is required." >&2; exit 1; }
[[ -f "$TARGET" && ! -L "$TARGET" ]] || { echo "Error: no regular module override at $TARGET." >&2; exit 1; }
rm -- "$TARGET"
depmod -a "$KVERSION"
echo "Removed the override for $KVERSION. The running module has not been changed."
echo "Reboot to select the distribution's driver; verify modinfo -n cdc_ncm afterwards."
echo "Network configuration and overrides for other kernels are not removed."
