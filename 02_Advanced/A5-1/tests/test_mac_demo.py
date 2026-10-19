"""관리자 권한 없는 Mac 시연 런처의 무결성·실패 차단 회귀 검사."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mac_demo", ROOT / "tools/mac_demo.py")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)
OK = subprocess.CompletedProcess([], 0, "학습 OK", "")
FAIL = subprocess.CompletedProcess([], 1, "", "Symbol not found: ___kmpc_dispatch_deinit libomp")


class MacDemoTests(unittest.TestCase):
    def test_bundled_macho_and_export(self):
        data = demo.BUNDLED_LIB.read_bytes()
        metadata = json.loads((demo.BUNDLED_LIB.parent / "provenance.json").read_text())
        self.assertEqual(hashlib.sha256(data).hexdigest(), demo.BUNDLED_SHA256)
        self.assertEqual(metadata["library_sha256"], demo.BUNDLED_SHA256)
        self.assertEqual(struct.unpack_from("<II", data), (0xFEEDFACF, 0x01000007))
        ncmds = struct.unpack_from("<I", data, 16)[0]
        pos, exported = 32, False
        for _ in range(ncmds):
            cmd, size = struct.unpack_from("<II", data, pos)
            if cmd == 2:  # LC_SYMTAB: a defined external symbol, not just a string
                symoff, nsyms, stroff, strsize = struct.unpack_from("<4I", data, pos + 8)
                for i in range(nsyms):
                    strx, kind, _, _, _ = struct.unpack_from("<IBBHQ", data, symoff + i * 16)
                    name = data[stroff + strx:stroff + strsize].split(b"\0", 1)[0]
                    if name == b"___kmpc_dispatch_deinit" and kind & 1 and kind & 0x0E:
                        exported = True
            pos += size
        self.assertTrue(exported)

    def test_verify_intel_runtime(self):
        with patch.object(demo.platform, "machine", return_value="x86_64"), patch.object(demo.platform, "mac_ver", return_value=("11.7.10", (), "")):
            self.assertEqual(demo.verified_bundled_library(), demo.BUNDLED_LIB)

    def test_wrong_architecture_does_not_use_bundle(self):
        with patch.object(demo.platform, "machine", return_value="arm64"):
            self.assertIsNone(demo.verified_bundled_library())

    def test_missing_and_corrupt_bundle_stop(self):
        library = Mock(spec=Path)
        with patch.object(demo.platform, "machine", return_value="x86_64"), patch.object(demo, "BUNDLED_LIB", library):
            library.is_file.return_value = False
            with self.assertRaisesRegex(RuntimeError, "런타임이 없습니다"):
                demo.verified_bundled_library()
            library.is_file.return_value = True
            library.read_bytes.return_value = b"broken"
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                demo.verified_bundled_library()

    def test_old_macos_stops(self):
        with patch.object(demo.platform, "machine", return_value="x86_64"), patch.object(demo.platform, "mac_ver", return_value=("10.15.7", (), "")):
            with self.assertRaisesRegex(RuntimeError, "macOS 11"):
                demo.verified_bundled_library()

    def test_bundle_preferred_and_environment_not_modified(self):
        with patch.object(demo, "verified_bundled_library", return_value=demo.BUNDLED_LIB), patch.object(demo, "probe", return_value=OK) as probe, patch.dict(demo.os.environ, {"DYLD_LIBRARY_PATH": "/previous"}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            env = demo.find_working_environment()
            self.assertTrue(env["DYLD_LIBRARY_PATH"].startswith(str(demo.BUNDLED_LIB.parent)))
            self.assertTrue(env["DYLD_LIBRARY_PATH"].endswith("/previous"))
            self.assertEqual(demo.os.environ["DYLD_LIBRARY_PATH"], "/previous")
            self.assertEqual(probe.call_count, 1)

    def test_native_failure_stops_instead_of_using_old_library(self):
        with patch.object(demo, "verified_bundled_library", return_value=demo.BUNDLED_LIB), patch.object(demo, "probe", return_value=FAIL), patch.object(demo, "library_candidates") as old, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(demo.find_working_environment())
            old.assert_not_called()

    def test_check_only_does_not_run_analysis(self):
        with patch.object(demo.sys, "platform", "darwin"), patch.object(demo.sys, "argv", ["mac_demo.py", "--check-only"]), patch.object(demo, "find_working_environment", return_value={}), patch.object(demo.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(demo.main(), 0)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
