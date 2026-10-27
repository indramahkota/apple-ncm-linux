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
elif name == "modinfo":
    field = args[1]
    print({"name": "cdc_ncm", "vermagic": os.environ.get("TEST_VERMAGIC", "6.8.0-ncm-safety-test SMP"), "signer": ""}[field])
elif name == "mokutil":
    print("SecureBoot disabled")
elif name == "depmod" and os.environ.get("TEST_DEPMOD_FAIL"):
    sys.exit(1)
'''


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.log = self.work / "calls.jsonl"
        for name in ("uname", "id", "modinfo", "mokutil", "depmod", "mkdir", "install", "rm"):
            path = self.bin / name
            path.write_text(STUB)
            path.chmod(0o755)
        for script in ROOT.glob("*.sh"):
            shutil.copy2(script, self.work)
        (self.work / "cdc_ncm.ko").write_bytes(b"test fixture; never installed")
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        CALL_LOG=str(self.log))

    def run_script(self, script, *args, **extra):
        return subprocess.run(["/bin/bash", str(self.work / script), *args],
                              env=dict(self.env, **extra), text=True, capture_output=True)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def mutations(self):
        return [call for call in self.calls() if call[0] in {"mkdir", "install", "rm", "depmod"}]

    def test_help_never_mutates(self):
        for script in ("install.sh", "uninstall.sh"):
            self.assertEqual(self.run_script(script, "--help").returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_non_root_install_rejected(self):
        self.assertNotEqual(self.run_script("install.sh", TEST_UID="1000").returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_kernel_mismatch_rejected(self):
        self.assertNotEqual(self.run_script("install.sh", TEST_VERMAGIC="wrong SMP").returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_install_only_stages_module(self):
        result = self.run_script("install.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[0] for c in self.mutations()], ["mkdir", "install", "depmod"])
        self.assertIn("No running module", result.stdout)

    def test_depmod_failure_removes_new_override(self):
        result = self.run_script("install.sh", TEST_DEPMOD_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([c[0] for c in self.mutations()], ["mkdir", "install", "depmod", "rm", "depmod"])

if __name__ == "__main__":
    unittest.main()
