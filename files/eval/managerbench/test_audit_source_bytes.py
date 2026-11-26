"""Synthetic tests of read-only local source-byte provenance verification."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_source_bytes import verify_sources, SourceBytesError


class SourceBytesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.file = self.root / "files" / "source.json"
        self.file.parent.mkdir()
        self.file.write_bytes(b'{"actual":true}\n')
        self.digest = hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.snapshot = {"sources_sha256": {"files/source.json": self.digest}}

    def verify(self):
        return verify_sources(self.snapshot, self.root)

    def test_exact_source_bytes_pass(self):
        self.assertEqual(self.verify(), 1)

    def test_uppercase_hex_digest_pass(self):
        self.snapshot["sources_sha256"]["files/source.json"] = self.digest.upper()
        self.assertEqual(self.verify(), 1)

    def test_mutated_content_same_name_blocked(self):
        self.file.write_bytes(b'{"actual":false}\n')
        with self.assertRaises(SourceBytesError): self.verify()

    def test_wrong_but_valid_64hex_blocked(self):
        self.snapshot["sources_sha256"]["files/source.json"] = "b" * 64
        with self.assertRaises(SourceBytesError): self.verify()

    def test_nonhash_and_null_blocked(self):
        for value in (None, "", "x" * 64, 0, False, {}):
            with self.subTest(value=value):
                self.snapshot["sources_sha256"]["files/source.json"] = value
                with self.assertRaises(SourceBytesError): self.verify()

    def test_missing_source_blocked(self):
        self.file.unlink()
        with self.assertRaises(SourceBytesError): self.verify()

    def test_path_traversal_blocked(self):
        self.snapshot["sources_sha256"] = {"../escape.json": self.digest}
        with self.assertRaises(SourceBytesError): self.verify()

    def test_absolute_path_blocked(self):
        self.snapshot["sources_sha256"] = {str(self.file): self.digest}
        with self.assertRaises(SourceBytesError): self.verify()

    def test_symlink_outside_repo_blocked(self):
        outside = Path(self.tmp.name) / "outside.json"
        outside.write_bytes(self.file.read_bytes())
        link = self.root / "files" / "linked.json"
        link.symlink_to(outside)
        self.snapshot["sources_sha256"] = {"files/linked.json": self.digest}
        with self.assertRaises(SourceBytesError): self.verify()

    def test_empty_or_nonobject_sources_blocked(self):
        for value in ({}, [], None):
            with self.subTest(value=value):
                self.snapshot["sources_sha256"] = value
                with self.assertRaises(SourceBytesError): self.verify()

    def test_source_path_empty_or_not_string_blocked(self):
        for value in ("", " ", 123):
            with self.subTest(value=value):
                self.snapshot["sources_sha256"] = {value: self.digest}
                with self.assertRaises(SourceBytesError): self.verify()

    def test_multiple_sources_all_verified(self):
        new = self.root / "files" / "b.json"
        new.write_bytes(b'{"b":2}')
        self.snapshot["sources_sha256"]["files/b.json"] = hashlib.sha256(new.read_bytes()).hexdigest()
        self.assertEqual(self.verify(), 2)

    def test_dot_segment_alias_of_same_source_blocked(self):
        self.snapshot["sources_sha256"]["./files/source.json"] = self.digest
        with self.assertRaisesRegex(SourceBytesError, "duplicate.*source"):
            self.verify()

    def test_in_root_symlink_alias_of_same_source_blocked(self):
        alias = self.root / "files" / "alias.json"
        alias.symlink_to(self.file)
        self.snapshot["sources_sha256"]["files/alias.json"] = self.digest
        with self.assertRaisesRegex(SourceBytesError, "duplicate.*source"):
            self.verify()

    def test_hardlink_alias_of_same_source_inode_blocked(self):
        # Two paths, one physical source; resolve(strict=True) alone misses this.
        alias = self.root / "files" / "hardlink.json"
        os.link(self.file, alias)
        self.assertEqual(self.file.stat().st_ino, alias.stat().st_ino)
        self.snapshot["sources_sha256"]["files/hardlink.json"] = self.digest
        with self.assertRaisesRegex(SourceBytesError, "duplicate.*source"):
            self.verify()

    def test_missing_inode_identity_blocks_instead_of_counting_success(self):
        with patch("audit_source_bytes.os.fstat") as fstat:
            fstat.return_value.st_ino = 0
            with self.assertRaisesRegex(SourceBytesError, "identity unavailable"):
                self.verify()

    def test_distinct_files_with_identical_bytes_still_count_separately(self):
        another = self.root / "files" / "copy.json"
        another.write_bytes(self.file.read_bytes())
        self.snapshot["sources_sha256"]["files/copy.json"] = self.digest
        self.assertEqual(self.verify(), 2)

    def test_missing_root_blocked(self):
        with self.assertRaises(SourceBytesError):
            verify_sources(self.snapshot, self.root / "missing")


if __name__ == "__main__":
    unittest.main()
