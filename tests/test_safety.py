"""Exercise destructive boundaries using fake commands; never touch the host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

STUB = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(json.dumps([name] + args) + "\n")
if name == "uname":
    print("Linux" if args == ["-s"] else "6.8.0-ncm-safety-test")
elif name == "id":
    print(os.environ.get("TEST_UID", "0"))
elif name == "mokutil":
    print("SecureBoot disabled")
elif name == "dkms" and args[0] == "status":
    if os.environ.get("TEST_DKMS_REGISTERED"):
        print("apple-ncm/1.0.0, 6.8.0-ncm-safety-test, x86_64: installed")
elif name == "dkms" and args[0] == "install" and os.environ.get("TEST_DKMS_FAIL"):
    sys.exit(1)
elif name == "modprobe" and args[0] == "-r" and os.environ.get("TEST_MODULE_BUSY"):
    sys.exit(1)
elif name == "modinfo":
    print("/lib/modules/6.8.0-ncm-safety-test/updates/dkms/cdc_ncm.ko.zst")
'''


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.log = self.work / "calls.jsonl"
        for name in ("uname", "id", "mokutil", "dkms", "install", "rm", "update-initramfs", "modprobe", "modinfo"):
            path = self.bin / name
            path.write_text(STUB)
            path.chmod(0o755)
        for script in ROOT.glob("*.sh"):
            shutil.copy2(script, self.work)
        shutil.copy2(ROOT / "dkms.conf", self.work)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        CALL_LOG=str(self.log))

    def run_script(self, script, *args, **extra):
        return subprocess.run(["/bin/bash", str(self.work / script), *args],
                              env=dict(self.env, **extra), text=True, capture_output=True)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def mutations(self):
        return [call[:2] for call in self.calls()
                if call[0] in {"install", "rm", "update-initramfs", "modprobe"} or call[:2] in (["dkms", "install"], ["dkms", "remove"])]

    def holder_reload(self):
        # Holders come from the host's /sys; only the stubbed modprobe sees them.
        holders = Path("/sys/module/cdc_ncm/holders")
        return [["modprobe", "-a"]] if holders.is_dir() and any(holders.iterdir()) else []

    def test_help_never_mutates(self):
        for script in ("install.sh", "uninstall.sh"):
            self.assertEqual(self.run_script(script, "--help").returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_non_root_install_rejected(self):
        self.assertNotEqual(self.run_script("install.sh", TEST_UID="1000").returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_install_registers_with_dkms(self):
        result = self.run_script("install.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations(), [["rm", "-rf"], ["install", "-d"], ["install", "-m"], ["dkms", "install"],
                                            ["update-initramfs", "-u"], ["modprobe", "-r"], ["modprobe", "cdc_ncm"]]
                         + self.holder_reload())
        self.assertIn("Reloaded cdc_ncm", result.stdout)

    def test_busy_module_asks_for_reboot(self):
        result = self.run_script("install.sh", TEST_MODULE_BUSY="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations()[-2:], [["update-initramfs", "-u"], ["modprobe", "-r"]])
        self.assertIn("reboot", result.stderr)

    def test_install_replaces_existing_registration(self):
        result = self.run_script("install.sh", TEST_DKMS_REGISTERED="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations()[0], ["dkms", "remove"])

    def test_dkms_failure_removes_registration(self):
        result = self.run_script("install.sh", TEST_DKMS_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations()[-2:], [["dkms", "remove"], ["rm", "-rf"]])

    def test_uninstall_requires_registration(self):
        self.assertNotEqual(self.run_script("uninstall.sh").returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_uninstall_removes_dkms_package(self):
        result = self.run_script("uninstall.sh", TEST_DKMS_REGISTERED="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations(), [["dkms", "remove"], ["rm", "-rf"], ["update-initramfs", "-u"],
                                            ["modprobe", "-r"], ["modprobe", "cdc_ncm"]] + self.holder_reload())

if __name__ == "__main__":
    unittest.main()
