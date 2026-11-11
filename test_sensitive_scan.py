"""sensitive_scan.py: secrets and Korean personal data in proposal material. Fixtures are built at runtime
so this file itself never contains a token-shaped or identifier-shaped literal."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import ooxml_fixtures as fixtures

sys.path.insert(0, str(Path(__file__).parent / "skills/create-best-proposal/scripts"))
import sensitive_scan as scan  # noqa: E402


def valid_rrn(prefix: str = "900101", gender: str = "1", body: str = "23456") -> str:
    """Build a 13-digit number whose checksum is valid: prefix(6) + gender(1) + body(5) + check(1)."""
    head = prefix + gender + body
    weights = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    check = (11 - sum(int(d) * w for d, w in zip(head, weights)) % 11) % 10
    return head + str(check)


def mail(user: str, host: str) -> str:
    """Assembled at runtime so this file holds no address-shaped literal (see test_repo_hygiene)."""
    return user + "@" + host


def kinds(findings):
    return {f.kind for f in findings}


class SecretPatternTests(unittest.TestCase):
    def test_known_token_families_are_found_and_masked(self):
        text = "\n".join([
            "key " + "AK" + "IA" + "ABCDEFGHIJKLMNOP",
            "pat " + "ghp" + "_" + "a" * 36,
            "slack " + "xox" + "b-" + "1234567890-abcdef",
            "-----BEGIN " + "RSA PRIVATE KEY-----",
            'password = "' + "hunter2hunter2" + '"',
            "db " + "postgres" + "://admin:" + mail("s3cretpw", "db.internal:5432/app"),
        ])
        found = scan.scan_text(text, "x.md")
        self.assertEqual(kinds(found), {"aws-access-key", "github-token", "slack-token", "private-key",
                                        "hardcoded-credential", "connection-string-password"})
        for finding in found:
            self.assertNotIn("ABCDEFGHIJKLMNOP", finding.sample)
            self.assertNotIn("hunter2hunter2", finding.sample)
            self.assertLessEqual(len(finding.sample.replace("*", "")), 2)

    def test_placeholder_credentials_are_not_findings(self):
        text = 'api_key = "your-api-' + 'key-here"\npassword = "changeme"\ntoken = "short"'
        self.assertEqual(scan.scan_text(text, "x.md"), [])

    def test_connection_string_placeholders_are_documentation(self):
        for placeholder in ("password", "<password>", "{password}", "xxxx", "****", "changeme"):
            text = "scheme://user:" + placeholder + "@host/db"
            self.assertEqual(scan.scan_text(text, "x.md"), [], placeholder)
        real = "scheme://user:" + "Tr0ub4dor" + "@host/db"
        self.assertEqual(kinds(scan.scan_text(real, "x.md")), {"connection-string-password"})

    def test_credential_needs_a_matching_quote_pair(self):
        """A string closed by a different quote (code concatenation) is not one literal value."""
        self.assertEqual(scan.scan_text('api_key = "your-api-' + "' + 'key-here\"", "x.py"), [])
        value = "long-enough" + "-value"  # assembled so no credential-shaped literal sits in this file
        for quote in ("'", '"'):
            text = "password = " + quote + value + quote
            self.assertEqual(kinds(scan.scan_text(text, "x.py")), {"hardcoded-credential"}, quote)

    def test_line_numbers_are_reported(self):
        text = "a\nb\n" + "ghp" + "_" + "b" * 36
        self.assertEqual(scan.scan_text(text, "x.md")[0].where, "line 3")


class KoreanPersonalDataTests(unittest.TestCase):
    def test_rrn_with_valid_checksum_is_flagged(self):
        number = valid_rrn()
        for text in (f"{number[:6]}-{number[6:]}", number, f"{number[:6]} {number[6:]}"):
            found = scan.scan_text("홍길동 " + text, "resume.md")
            self.assertEqual(kinds(found), {"resident-registration-number"}, text)
            self.assertIn("checksum valid", found[0].note)

    def test_rrn_with_invalid_checksum_but_real_date_still_flagged_with_note(self):
        number = valid_rrn()
        wrong = number[:12] + str((int(number[12]) + 1) % 10)
        found = scan.scan_text(wrong[:6] + "-" + wrong[6:], "x.md")
        self.assertEqual(kinds(found), {"resident-registration-number"})
        self.assertIn("checksum not valid", found[0].note)

    def test_impossible_birth_date_is_not_flagged(self):
        self.assertEqual(scan.scan_text("991340-1234567", "x.md"), [])

    def test_foreigner_range_is_noted(self):
        number = valid_rrn(gender="5")
        found = scan.scan_text(number, "x.md")
        self.assertIn("foreigner", found[0].note)

    def test_longer_digit_runs_do_not_match(self):
        self.assertEqual(scan.scan_text("주문번호 " + valid_rrn() + "9", "x.md"), [])

    def test_mobile_phone_and_email_are_medium_and_example_domains_are_ignored(self):
        found = scan.scan_text("연락처 010-1234-5678, " + mail("hong", "corp.co.kr") + ", " + mail("doc", "example.com"), "x.md")
        self.assertEqual(kinds(found), {"mobile-phone", "email"})
        self.assertEqual(sum(f.kind == "email" for f in found), 1)

    def test_card_number_needs_luhn(self):
        self.assertEqual(kinds(scan.scan_text("4012 8888 " + "8888 1881", "x.md")), {"payment-card-number"})
        self.assertEqual(scan.scan_text("4012 8888 " + "8888 1882", "x.md"), [])

    def test_internal_ip_ranges_only(self):
        found = scan.scan_text("서버 10.20.30.40, 172.16.0.5, 192.168.1.9, 8.8.8.8, 172.32.0.1, 999.1.1.1", "x.md")
        self.assertEqual([f.sample[:2] for f in found], ["10", "17", "19"])
        self.assertEqual(kinds(found), {"internal-ip"})

    def test_version_numbers_are_not_ip_addresses(self):
        self.assertEqual(scan.scan_text("버전 10.2.3.4.5 및 v10.2.3", "x.md"), [])


class FileHandlingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_pptx_text_split_across_runs_is_still_found(self):
        number = valid_rrn()
        path = fixtures.pptx(self.dir / "deck.pptx", {"ppt/slides/slide1.xml": number[:6] + "-" + number[6:]})
        found, unscanned, count = scan.scan_paths([path])
        self.assertEqual((count, unscanned), (1, []))
        self.assertEqual(kinds(found), {"resident-registration-number"})
        self.assertEqual(found[0].where, "ppt/slides/slide1.xml")

    def test_docx_header_and_xlsx_shared_strings_are_read(self):
        docx = fixtures.docx(self.dir / "a.docx", "<w:p><w:r><w:t>본문</w:t></w:r></w:p>",
                             {"word/header1.xml": "010-2222-3333"})
        xlsx = fixtures.xlsx(self.dir / "b.xlsx", {"xl/sharedStrings.xml": "<sst><si><t>10.1.1.1</t></si></sst>"})
        found, _, _ = scan.scan_paths([docx, xlsx])
        self.assertEqual(kinds(found), {"mobile-phone", "internal-ip"})

    def test_core_properties_metadata_is_scanned(self):
        path = fixtures.pptx(self.dir / "m.pptx", raw={
            "docProps/core.xml": '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>' + mail('kim', 'corp.co.kr') + '</dc:creator></cp:coreProperties>'})
        found, _, _ = scan.scan_paths([path])
        self.assertEqual(kinds(found), {"email"})

    def test_embedded_media_is_reported_as_unscanned_not_clean(self):
        path = fixtures.pptx(self.dir / "img.pptx")
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("ppt/media/image1.png", b"\x89PNG")
        found, unscanned, _ = scan.scan_paths([path])
        self.assertEqual(found, [])
        self.assertTrue(any("embedded" in u.reason for u in unscanned))

    def test_corrupt_office_file_is_unscanned_and_exit_2(self):
        bad = self.dir / "bad.pptx"
        bad.write_bytes(b"not a zip")
        out = io.StringIO()
        with redirect_stdout(out):
            code = scan.main([str(bad)])
        self.assertEqual(code, 2)
        self.assertIn("UNSCANNED", out.getvalue())
        self.assertIn("INCOMPLETE", out.getvalue())

    def test_dtd_entity_xml_is_refused_not_expanded(self):
        path = self.dir / "evil.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><d>&a;</d>')
        found, unscanned, _ = scan.scan_paths([path])
        self.assertEqual(found, [])
        self.assertTrue(unscanned)

    def test_dtd_after_long_padding_and_utf16_xml_are_refused(self):
        bodies = {"late.docx": ("<?xml version=\"1.0\"?><!-- " + "x" * 5000 + " --><!DOCTYPE d [<!ENTITY a \"b\">]><d/>").encode(),
                  "wide.docx": '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "b">]><d/>'.encode("utf-16")}
        for name, data in bodies.items():
            path = self.dir / name
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("word/document.xml", data)
            found, unscanned, _ = scan.scan_paths([path])
            self.assertEqual((found, bool(unscanned)), ([], True), name)

    def test_directory_walk_reports_pdf_and_hwpx_as_unscanned(self):
        (self.dir / "rfp.pdf").write_bytes(b"%PDF-1.4")
        (self.dir / "resume.hwpx").write_bytes(b"PK")
        found, unscanned, count = scan.scan_paths([self.dir])
        self.assertEqual((found, count), ([], 0))
        self.assertEqual(sorted(Path(u.path).name for u in unscanned), ["resume.hwpx", "rfp.pdf"])

    def test_incomplete_scan_exits_2_even_with_findings(self):
        (self.dir / "dirty.md").write_text("담당 010-1234-5678", encoding="utf-8")
        (self.dir / "rfp.pdf").write_bytes(b"%PDF-1.4")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main([str(self.dir)]), 2)

    def test_bare_13_digits_without_checksum_is_medium_but_formatted_or_valid_is_high(self):
        number = valid_rrn()
        wrong = number[:12] + str((int(number[12]) + 1) % 10)
        self.assertEqual(scan.scan_text(wrong, "x.md")[0].severity, "medium")
        self.assertEqual(scan.scan_text(wrong[:6] + "-" + wrong[6:], "x.md")[0].severity, "high")
        self.assertEqual(scan.scan_text(number, "x.md")[0].severity, "high")

    def test_oversized_zip_total_is_refused(self):
        path = self.dir / "big.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", "<d/>" + " " * 1024)
        original = scan.MAX_UNZIPPED_BYTES
        scan.MAX_UNZIPPED_BYTES = 100
        self.addCleanup(setattr, scan, "MAX_UNZIPPED_BYTES", original)
        _, unscanned, _ = scan.scan_paths([path])
        self.assertTrue(any("safety limit" in u.reason for u in unscanned))

    def test_directory_walk_skips_git_and_symlinks_and_missing_path_is_reported(self):
        (self.dir / ".git").mkdir()
        (self.dir / ".git" / "x.md").write_text("010-1234-5678", encoding="utf-8")
        (self.dir / "ok.md").write_text("깨끗한 문서", encoding="utf-8")
        found, unscanned, count = scan.scan_paths([self.dir, self.dir / "missing"])
        self.assertEqual((found, count), ([], 1))
        self.assertTrue(any("does not exist" in u.reason for u in unscanned))

    def test_binary_and_unsupported_files_are_not_clean(self):
        blob = self.dir / "data.txt"
        blob.write_bytes(b"\0\1\2binary")
        found, unscanned, _ = scan.scan_paths([blob])
        self.assertEqual(found, [])
        self.assertTrue(unscanned)

    def test_allow_kind_suppresses_only_that_kind(self):
        text = "010-1234-5678 " + mail("hong", "corp.co.kr") + " 10.0.0.1"
        found = scan.scan_text(text, "x.md", allow=frozenset({"mobile-phone", "email"}))
        self.assertEqual(kinds(found), {"internal-ip"})


class CliTests(unittest.TestCase):
    def test_exit_codes_and_json_never_contain_full_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean = Path(tmp) / "clean.md"
            clean.write_text("제안 개요", encoding="utf-8")
            dirty = Path(tmp) / "dirty.md"
            dirty.write_text("담당 010-1234-5678", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(scan.main([str(clean)]), 0)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(scan.main([str(dirty), "--json"]), 1)
            report = json.loads(out.getvalue())
            self.assertEqual(report["findings"][0]["kind"], "mobile-phone")
            self.assertNotIn("1234-5678", out.getvalue())


if __name__ == "__main__":
    unittest.main()
