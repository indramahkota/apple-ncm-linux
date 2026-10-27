#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail

if [[ "${1:-}" == "--help" && $# -eq 1 ]]; then
  echo "Usage: sudo ./install.sh (build first with make; reboot after installation)"
  exit 0
fi
[[ $# -eq 0 ]] || { echo "Error: unexpected arguments; use --help." >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo "Error: Linux is required." >&2; exit 1; }
[[ "$(id -u)" -eq 0 ]] || { echo "Error: run with sudo after building as your normal user." >&2; exit 1; }

KVERSION="$(uname -r)"
MODULE_DIR="/lib/modules/${KVERSION}/updates"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE="${SCRIPT_DIR}/cdc_ncm.ko"
TARGET="${MODULE_DIR}/cdc_ncm.ko"
for tool in modinfo depmod install; do
  command -v "$tool" >/dev/null || { echo "Error: missing command: $tool" >&2; exit 1; }
done
[[ -f "$MODULE" && ! -L "$MODULE" ]] || { echo "Error: build cdc_ncm.ko first with make." >&2; exit 1; }
[[ ! -e "$TARGET" && ! -L "$TARGET" ]] || { echo "Error: $TARGET already exists; inspect it before uninstalling or replacing it." >&2; exit 1; }
[[ "$(modinfo -F name "$MODULE")" == cdc_ncm ]] || { echo "Error: unexpected module name." >&2; exit 1; }
VERMAGIC="$(modinfo -F vermagic "$MODULE")"
[[ "${VERMAGIC%% *}" == "$KVERSION" ]] || { echo "Error: module was built for a different kernel." >&2; exit 1; }

if [[ -d /sys/firmware/efi ]]; then
  command -v mokutil >/dev/null || { echo "Error: install mokutil to check Secure Boot before installing." >&2; exit 1; }
  SB_STATE="$(LC_ALL=C mokutil --sb-state)"
  case "$SB_STATE" in
    *"SecureBoot disabled"*) ;;
    *"SecureBoot enabled"*)
      [[ -n "$(modinfo -F signer "$MODULE")" ]] || {
        echo "Error: Secure Boot is enabled. Sign the module with an enrolled MOK first; see README.md." >&2
        exit 1
      }
      echo "A module signature is present; key trust must also be established before reboot."
      ;;
    *) echo "Error: unable to determine Secure Boot state; installation stopped." >&2; exit 1 ;;
  esac
fi

mkdir -p "$MODULE_DIR"
install -m 644 "$MODULE" "$TARGET"
if ! depmod -a "$KVERSION"; then
  rm -f "$TARGET"
  depmod -a "$KVERSION" || true
  echo "Error: depmod failed; the newly installed file was removed." >&2
  exit 1
fi
echo "Installed for kernel $KVERSION. No running module or USB device was changed."
echo "Reboot from a local console when convenient, then verify modinfo -n cdc_ncm."
echo "Install again after a kernel update only if the new stock driver still needs this patch."
