#!/usr/bin/env python3
"""Scan proposal material for secrets and personal data before it is shared, bundled, or committed.

Proposal work carries customer systems, staff resumes, and quotations. Typical leaks are a Korean
resident registration number in a resume slide, an internal IP in an architecture diagram, or an API key
pasted into an appendix. This scanner reports them with masked samples; it never prints a full value
and never modifies a file.

Reads plain text (.md .txt .json .csv .yml .yaml .xml .html .py .sh) and, with the standard library
only, the text of Office files (.pptx .docx .xlsx) and Hancom HWPX (.hwpx; the older binary .hwp is not read). Anything it cannot read is reported as UNSCANNED,
never silently treated as clean.

Exit codes: 0 clean, 1 findings, 2 usage error or incomplete scan (unreadable/unsupported/oversized).
An incomplete scan exits 2 even when findings exist; the findings are still printed.

Findings are leads for a human reviewer, not a legal or privacy determination. A clean result means
only that these patterns were not found in the files that were read.

Usage:
  python sensitive_scan.py FILE_OR_DIR [FILE_OR_DIR ...] [--allow-kind email --allow-kind phone] [--json]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

TEXT_SUFFIXES = {".md", ".txt", ".json", ".csv", ".tsv", ".yml", ".yaml", ".xml", ".html", ".htm",
                 ".py", ".sh", ".js", ".ts", ".ini", ".cfg", ".toml", ".env"}
OFFICE_SUFFIXES = {".pptx", ".docx", ".xlsx", ".hwpx"}
# Document formats that carry text but are not read here. A directory walk reports them as UNSCANNED
# instead of skipping them, so a folder holding an RFP .pdf or a binary .hwp resume is never called CLEAN.
# (.hwpx is read; the older binary .hwp is not.)
UNREADABLE_DOC_SUFFIXES = {".pdf", ".hwp", ".doc", ".ppt", ".xls", ".pptm", ".docm", ".xlsm",
                           ".odt", ".odp", ".ods", ".rtf", ".zip"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache"}
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_UNZIPPED_BYTES = 128 * 1024 * 1024  # zip-bomb guard across all parts of one Office file
MAX_ZIP_PARTS = 5000

# severity: high = likely credential or identifier; medium = personal/contact data; low = review lead.
# Family list: AWS, private key, GitHub/GitLab/Slack/Google/npm/OpenAI-style tokens are public formats.
SECRET_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("aws-access-key", "high", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private-key", "high", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----")),
    ("github-token", "high", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("gitlab-token", "high", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("slack-token", "high", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai-style-key", "high", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{16,}")),
    ("google-api-key", "high", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("npm-token", "high", re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b")),
    ("hardcoded-credential", "high", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*(?P<q>[\"'])"
        r"(?!(?:placeholder|example|dummy|changeme|change-me|replace-me|your[-_ ]api[-_ ]key[-_ ]here)\b)"
        r"(?:(?!(?P=q))\S){8,}(?P=q)")),
    ("connection-string-password", "high", re.compile(
        r"\b[a-z][a-z0-9+.-]{2,15}://[^\s:/@]+:"
        r"(?!(?:password|passwd|pass|pwd|secret|changeme|x{3,}|\*+|<[^>\s]*>|\{[^}\s]*\})@)"  # documentation placeholders
        r"[^\s/@]{3,}@[^\s/]+", re.I)),
)

SECRET_PATTERNS_BY_KIND = {name: pattern for name, _, pattern in SECRET_PATTERNS}
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<![\d-])01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?![\d-])")
RRN_RE = re.compile(r"(?<!\d)(\d{2})(\d{2})(\d{2})[- ]?([1-8])(\d{6})(?!\d)")
CARD_RE = re.compile(r"(?<![\d-])(?:\d{4}[- ]?){3}\d{4}(?![\d-])")
IPV4_RE = re.compile(r"(?<![\d.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])")

# Documentation/example mailboxes are not leaks.
EXAMPLE_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "localhost"}
DOCUMENT_PROPERTY_TAGS = {"title", "subject", "creator", "lastModifiedBy", "keywords", "description",
                          "Company", "Manager", "Template"}
KINDS = tuple(name for name, _, _ in SECRET_PATTERNS) + (
    "resident-registration-number", "payment-card-number", "email", "mobile-phone", "internal-ip")


@dataclass(frozen=True)
class Finding:
    path: str
    where: str       # "line 12" or "ppt/slides/slide3.xml"
    kind: str
    severity: str
    sample: str      # masked
    note: str = ""


@dataclass(frozen=True)
class Unscanned:
    path: str
    reason: str


def mask(value: str) -> str:
    """Show at most the first two characters; everything else is hidden."""
    compact = value.strip()
    if len(compact) <= 4:
        return "*" * len(compact)
    return compact[:2] + "*" * min(len(compact) - 2, 12)


def rrn_checksum_ok(digits: str) -> bool:
    """Official 13-digit checksum. Numbers issued since Oct 2020 are random and need not satisfy it."""
    if len(digits) != 13 or not digits.isdigit():
        return False
    weights = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    total = sum(int(d) * w for d, w in zip(digits[:12], weights))
    return (11 - total % 11) % 10 == int(digits[12])


def rrn_date_ok(yy: str, mm: str, dd: str, gender: str) -> bool:
    century = {"1": 1900, "2": 1900, "5": 1900, "6": 1900, "3": 2000, "4": 2000, "7": 2000, "8": 2000}[gender]
    try:
        date(century + int(yy), int(mm), int(dd))
    except ValueError:
        return False
    return True


def luhn_ok(digits: str) -> bool:
    total, flip = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if flip:
            n *= 2
            n -= 9 if n > 9 else 0
        total += n
        flip = not flip
    return total % 10 == 0


def is_internal_ip(octets: tuple[int, ...]) -> bool:
    a, b = octets[0], octets[1]
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)


def scan_text(text: str, path: str, where_of=None, allow: frozenset[str] = frozenset()) -> list[Finding]:
    """Scan one text body. `where_of(offset)` maps a character offset to a location label."""
    findings: list[Finding] = []

    def where(offset: int) -> str:
        return where_of(offset) if where_of else f"line {text.count(chr(10), 0, offset) + 1}"

    def add(kind: str, severity: str, match: re.Match[str], note: str = "") -> None:
        if kind not in allow:
            findings.append(Finding(path, where(match.start()), kind, severity, mask(match.group(0)), note))

    for kind, severity, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            add(kind, severity, m)
    for m in RRN_RE.finditer(text):
        yy, mm, dd, gender, tail = m.groups()
        if not rrn_date_ok(yy, mm, dd, gender):
            continue
        digits = yy + mm + dd + gender + tail
        checksum = rrn_checksum_ok(digits)
        note = "checksum valid" if checksum else "format and birth date valid; checksum not valid (post-2020 numbers are random)"
        # A bare 13-digit run with no valid checksum is as likely an order or ledger number: keep it, lower it.
        strong = checksum or re.search(r"[- ]", m.group(0)) is not None
        add("resident-registration-number", "high" if strong else "medium", m,
            note + ("; foreigner registration range" if gender in "5678" else ""))
    for m in CARD_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if luhn_ok(digits) and len(set(digits)) > 3:
            add("payment-card-number", "high", m, "Luhn checksum valid")
    # user:password@host inside a connection string is already reported; it is not also an email address.
    credential_spans = [m.span() for m in SECRET_PATTERNS_BY_KIND["connection-string-password"].finditer(text)]
    for m in EMAIL_RE.finditer(text):
        if any(start <= m.start() < end for start, end in credential_spans):
            continue
        if m.group(0).rsplit("@", 1)[1].lower() not in EXAMPLE_EMAIL_DOMAINS and not m.group(0).lower().endswith("@users.noreply.github.com"):
            add("email", "medium", m)
    for m in PHONE_RE.finditer(text):
        add("mobile-phone", "medium", m)
    for m in IPV4_RE.finditer(text):
        octets = tuple(int(g) for g in m.groups())
        if all(o <= 255 for o in octets) and is_internal_ip(octets):
            add("internal-ip", "low", m, "private-range address; confirm it is not the customer's real network")
    return findings


def _safe_root(data: bytes) -> ElementTree.Element:
    """Parse XML after refusing inputs that could expand entities or hide from the byte search."""
    # defusedxml is not in the standard library; reject DTDs outright to avoid entity-expansion attacks.
    # The byte search below is ASCII-only, so UTF-16/32 (NUL bytes) is refused instead of slipping past it.
    if b"\0" in data:
        raise ValueError("UTF-16/32 XML is not read")
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("XML with DTD/entity declarations is not read")
    return ElementTree.fromstring(data)


def _hwpx_text(data: bytes) -> str:
    """Text of an HWPX section or master page: one line per paragraph, including table cells and text boxes.

    A paragraph is `p` with `run` children holding `t` text. Nested paragraphs (table cells, footnotes, drawn text) are
    separate `p` elements, so each paragraph reads only its own direct runs and nothing is counted twice.
    """
    lines: list[str] = []
    for paragraph in _safe_root(data).iter():
        if paragraph.tag.rsplit("}", 1)[-1] != "p":
            continue
        pieces = ["".join(t.itertext()) for run in paragraph if run.tag.rsplit("}", 1)[-1] == "run"
                  for t in run if t.tag.rsplit("}", 1)[-1] == "t"]
        if any(pieces):
            lines.append("".join(pieces))
    return "\n".join(lines)


def _hwpx_metadata(data: bytes) -> str:
    """Title, language and author-style `meta` values from Contents/content.hpf (travel with the file)."""
    return "\n".join(e.text.strip() for e in _safe_root(data).iter()
                     if e.tag.rsplit("}", 1)[-1] in {"title", "meta"} and e.text and e.text.strip())


def read_hwpx(path: Path) -> list[tuple[str, str]]:
    """Return [(part name, text)] for an HWPX package (a ZIP of XML), with the same size limits as Office files."""
    parts: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_PARTS:
            raise ValueError(f"too many parts ({len(infos)})")
        if sum(i.file_size for i in infos) > MAX_UNZIPPED_BYTES:
            raise ValueError("unzipped size exceeds the safety limit")
        names = [i.filename for i in infos if not i.is_dir()]
        if "mimetype" not in names or not archive.read("mimetype").startswith(b"application/hwp+zip"):
            raise ValueError("not an HWPX package (mimetype)")
        sections = sorted(n for n in names if re.fullmatch(r"Contents/(?:section|masterpage)\d+\.xml", n))
        if not any("section" in n for n in sections):
            raise ValueError("HWPX package has no section part")
        for name in sections:
            parts.append((name, _hwpx_text(archive.read(name))))
        if "Contents/content.hpf" in names:
            parts.append(("Contents/content.hpf", _hwpx_metadata(archive.read("Contents/content.hpf"))))
        if "Preview/PrvText.txt" in names:  # a plain-text copy of the first page; can differ from the body
            raw = archive.read("Preview/PrvText.txt")
            parts.append(("Preview/PrvText.txt", raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8", "replace")))
        embedded = [n for n in names if n.startswith("BinData/")]
    if embedded:
        parts.append(("<embedded>", "\0" + "\n".join(embedded)))
    return parts


def _xml_text(data: bytes) -> str:
    """Concatenate all text nodes, one line per paragraph-ish element, without resolving entities."""
    root = _safe_root(data)

    def local(element: ElementTree.Element) -> str:
        return element.tag.rsplit("}", 1)[-1]

    lines: list[str] = []
    for element in root.iter():
        tag = local(element)
        if tag in {"p", "si"}:
            # Office splits one visible string across many runs; join them so a number cannot hide
            # between two runs. Each paragraph / shared string becomes one line.
            lines.append("".join(t.text for t in element.iter()
                                 if local(t) in {"t", "instrText"} and t.text))
        elif tag in DOCUMENT_PROPERTY_TAGS and element.text:
            lines.append(element.text)  # author / company / title metadata travels with the file
        elif tag == "v" and element.text:
            lines.append(element.text)  # spreadsheet cell values and chart caches
    return "\n".join(lines)


EMBEDDED_OFFICE = (".xlsx", ".docx", ".pptx")
OFFICE_PARTS = re.compile(r"(ppt/(slides|notesSlides|comments|charts)/|word/(document|header\d*|footer\d*|comments|footnotes|endnotes)\.xml|word/charts/|xl/(sharedStrings|worksheets/|comments|charts/)|docProps/(core|app|custom)\.xml)")


def _office_parts(archive: zipfile.ZipFile, prefix: str = "", depth: int = 0, budget: list[int] | None = None) -> tuple[list[tuple[str, str]], list[str]]:
    """Readable XML parts of one package, plus names that could not be read.

    An Office package embedded in another (a chart's value workbook, an attached spreadsheet) is read one level deep;
    its parts are named `outer/part.xlsx!inner/part.xml`. Images, OLE objects and anything nested deeper stay unread
    and are reported, never assumed clean. `budget` carries the unzipped size across every package read.
    """
    budget = budget if budget is not None else [0]
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_PARTS:
        raise ValueError(f"too many parts ({len(infos)})")
    budget[0] += sum(i.file_size for i in infos)
    if budget[0] > MAX_UNZIPPED_BYTES:
        raise ValueError("unzipped size exceeds the safety limit")
    parts: list[tuple[str, str]] = []
    unread: list[str] = []
    for info in infos:
        if info.is_dir():
            continue
        name, low = info.filename, info.filename.lower()
        if low.endswith((".xml", ".rels")):
            if OFFICE_PARTS.match(name):   # slides, documents, shared strings, sheets, notes, comments, headers/footers, charts
                parts.append((prefix + name, _xml_text(archive.read(info))))
        elif re.search(r"/(media|embeddings)/", name):
            if "/embeddings/" in name and low.endswith(EMBEDDED_OFFICE) and depth < 1 and info.file_size <= MAX_FILE_BYTES:
                try:
                    with zipfile.ZipFile(io.BytesIO(archive.read(info))) as nested:
                        inner, inner_unread = _office_parts(nested, f"{prefix}{name}!", depth + 1, budget)
                    parts += inner
                    unread += inner_unread
                except zipfile.BadZipFile:
                    unread.append(f"{prefix}{name} (not a ZIP package)")
                except (ElementTree.ParseError, RuntimeError):
                    unread.append(f"{prefix}{name} (unreadable)")
            else:
                unread.append(prefix + name)
    return parts, unread


def read_office(path: Path) -> list[tuple[str, str]]:
    """Return [(part name, text)] for readable XML parts, enforcing size and part-count limits."""
    if path.suffix.lower() == ".hwpx":
        return read_hwpx(path)
    with zipfile.ZipFile(path) as archive:
        parts, unread = _office_parts(archive)
    if unread:
        parts.append(("<embedded>", "\0" + "\n".join(unread)))
    return parts


def iter_files(targets: list[Path]) -> tuple[list[Path], list[Unscanned]]:
    files: list[Path] = []
    problems: list[Unscanned] = []
    for target in targets:
        if target.is_symlink():
            problems.append(Unscanned(str(target), "symbolic link not followed"))
        elif target.is_file():
            files.append(target)
        elif target.is_dir():
            stack = [target]
            while stack:
                current = stack.pop()
                try:
                    entries = sorted(current.iterdir())
                except OSError as exc:
                    problems.append(Unscanned(str(current), f"cannot list directory ({type(exc).__name__})"))
                    continue
                for entry in entries:
                    if entry.is_symlink():
                        continue  # never follow links: they can leave the tree or loop forever
                    if entry.is_dir():
                        if entry.name not in SKIP_DIRS:
                            stack.append(entry)
                    elif entry.suffix.lower() in TEXT_SUFFIXES | OFFICE_SUFFIXES:
                        files.append(entry)
                    elif entry.suffix.lower() in UNREADABLE_DOC_SUFFIXES:
                        problems.append(Unscanned(str(entry), f"document type {entry.suffix.lower()} is not read; convert it to text or review it by hand"))
        else:
            problems.append(Unscanned(str(target), "path does not exist"))
    return files, problems


def scan_file(path: Path, allow: frozenset[str]) -> tuple[list[Finding], list[Unscanned]]:
    label = str(path)
    suffix = path.suffix.lower()
    try:
        size = path.stat().st_size
    except OSError as exc:
        return [], [Unscanned(label, f"cannot inspect ({type(exc).__name__})")]
    if size > MAX_FILE_BYTES:
        return [], [Unscanned(label, f"larger than {MAX_FILE_BYTES // (1024 * 1024)} MiB")]
    try:
        if suffix in OFFICE_SUFFIXES:
            findings: list[Finding] = []
            unscanned: list[Unscanned] = []
            for part, text in read_office(path):
                if part == "<embedded>":
                    unscanned.append(Unscanned(label, "embedded media/OLE objects are not inspected: " + text[1:].replace("\n", ", ")[:200]))
                    continue
                findings += scan_text(text, label, lambda _o, part=part: part, allow)
            return findings, unscanned
        if suffix in TEXT_SUFFIXES or not suffix:
            raw = path.read_bytes()
            if b"\0" in raw[:4096]:
                return [], [Unscanned(label, "binary content")]
            return scan_text(raw.decode("utf-8", errors="replace"), label, None, allow), []
        return [], [Unscanned(label, f"unsupported file type {suffix}")]
    except zipfile.BadZipFile:
        # Seen with files saved under an enterprise DRM agent: the file looks like .xlsx but is not a ZIP.
        return [], [Unscanned(label, "not a ZIP package: encrypted or DRM-protected, or corrupt; decrypt it through an authorized route and rescan")]
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError, ValueError, RuntimeError) as exc:
        return [], [Unscanned(label, f"cannot read ({type(exc).__name__}: {str(exc)[:80]})")]


def scan_paths(targets: list[Path], allow: frozenset[str] = frozenset()) -> tuple[list[Finding], list[Unscanned], int]:
    files, problems = iter_files(targets)
    findings: list[Finding] = []
    for file in files:
        f, u = scan_file(file, allow)
        findings += f
        problems += u
    return findings, problems, len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--allow-kind", action="append", default=[], choices=KINDS, metavar="KIND",
                        help="ignore a finding kind that is legitimate here (e.g. the bidder's own email); repeatable")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    findings, problems, count = scan_paths(args.paths, frozenset(args.allow_kind))
    if args.json:
        print(json.dumps({"files": count, "findings": [f.__dict__ for f in findings],
                          "unscanned": [u.__dict__ for u in problems]}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            note = f" - {f.note}" if f.note else ""
            print(f"[{f.severity.upper()}] {f.path} ({f.where}): {f.kind} {f.sample}{note}")
        for u in problems:
            print(f"[UNSCANNED] {u.path}: {u.reason}")
        status = "FINDINGS" if findings else ("INCOMPLETE" if problems else "CLEAN")
        print(f"SENSITIVE-SCAN: {status} ({count} file(s), {len(findings)} finding(s), {len(problems)} unscanned)")
    if problems:  # incomplete wins over findings so a gate cannot mistake a partial scan for a complete one
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
