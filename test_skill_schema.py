"""Multi-host skill schema: flagship entry vs explicit-only siblings."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import install_skill

REPO = Path(__file__).resolve().parent
SKILLS = REPO / "skills"


class SkillSchemaTests(unittest.TestCase):
    def test_all_skills_pass_schema(self):
        names = install_skill.available_skills()
        self.assertGreaterEqual(len(names), 3)
        for name in names:
            with self.subTest(skill=name):
                problems = install_skill.skill_schema_problems(SKILLS / name)
                self.assertEqual(problems, [], problems)

    def test_dir_name_matches_frontmatter(self):
        for name in install_skill.available_skills():
            fm = install_skill.parse_frontmatter(
                (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(fm.get("name"), name)
            self.assertTrue(fm.get("description"))

    def test_openai_yaml_parses_interface(self):
        for name in install_skill.available_skills():
            meta = install_skill.load_openai_yaml(SKILLS / name)
            self.assertIsNotNone(meta, name)
            self.assertIn("interface", meta)
            iface = meta["interface"]
            self.assertTrue(iface.get("display_name") or iface.get("short_description"))

    def test_siblings_are_explicit_only(self):
        for name in sorted(install_skill.SIBLINGS):
            with self.subTest(skill=name):
                fm = install_skill.parse_frontmatter(
                    (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
                self.assertTrue(fm.get("disable-model-invocation"), name)
                meta = install_skill.load_openai_yaml(SKILLS / name)
                self.assertFalse(install_skill.allow_implicit_invocation(meta), name)

    def test_flagship_allows_implicit_and_model_invocation(self):
        name = install_skill.FLAGSHIP
        fm = install_skill.parse_frontmatter(
            (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
        self.assertFalse(bool(fm.get("disable-model-invocation")))
        meta = install_skill.load_openai_yaml(SKILLS / name)
        self.assertTrue(install_skill.allow_implicit_invocation(meta))
        # Prefer omitting policy entirely on the flagship.
        self.assertNotIn("policy", meta or {})

    def test_flagship_packaged_deps_exist(self):
        for dep in install_skill.DEPS[install_skill.FLAGSHIP]:
            self.assertTrue((SKILLS / dep / "SKILL.md").is_file(), dep)

    def test_plugin_manifest_points_at_skills(self):
        manifest = REPO / ".codex-plugin" / "plugin.json"
        self.assertTrue(manifest.is_file())
        text = manifest.read_text(encoding="utf-8")
        self.assertIn('"skills"', text)
        self.assertIn("./skills/", text)

    def test_docs_name_flagship_entry_and_explicit_siblings(self):
        for doc in ("AGENTS.md", "README.md"):
            body = (REPO / doc).read_text(encoding="utf-8")
            self.assertIn("create-best-proposal", body)
            self.assertRegex(body, r"진입점|flagship|Entry", doc)
            self.assertRegex(body, r"명시|explicit", doc)

    def test_sibling_default_prompt_is_not_main_entry(self):
        for name in sorted(install_skill.SIBLINGS):
            meta = install_skill.load_openai_yaml(SKILLS / name)
            prompt = (meta or {}).get("interface", {}).get("default_prompt", "")
            self.assertIn("create-best-proposal", prompt, name)
            self.assertRegex(prompt.lower(), r"only|unavailable|prefer|명시|레이어")


class VerifySchemaIntegrationTests(unittest.TestCase):
    def test_verify_accepts_intact_source_copies(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in install_skill.available_skills():
                shutil.copytree(
                    SKILLS / name, root / name,
                    ignore=install_skill.COPY_IGNORE)
            for name in install_skill.available_skills():
                with self.subTest(skill=name):
                    self.assertEqual(install_skill.verify(root / name), [])

    def test_coinstall_helper_flags_missing_siblings(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            target = install_skill.install(Path(tmp), "create-best-proposal")
            problems = install_skill.coinstall_problems(target)
            self.assertTrue(any("create-proposal-document" in p for p in problems))
            self.assertTrue(any("create-winning-proposal" in p for p in problems))


class ReferenceWiringTests(unittest.TestCase):
    """새 reference를 만들고 연결하지 않거나, 경로를 바꾸고 문서를 두는 회귀를 막는다.

    규약: 마크다운 링크는 문서 파일 기준 상대 경로, 백틱 경로는 스킬 루트 기준 상대 경로다
    (sibling-map.md «경로 기준»). 백틱은 두 기준 중 하나로 해석되면 통과시킨다.
    """

    LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
    TICK = re.compile(r"`((?:\.\./[\w-]+/)?(?:references|scripts|fixtures|assets)/[\w./-]+"
                      r"\.(?:md|py|json|yaml))`")

    @staticmethod
    def _skill_docs() -> list[Path]:
        return sorted(SKILLS.glob("*/**/*.md"))

    def test_relative_links_and_paths_resolve(self):
        broken: list[str] = []
        for doc in self._skill_docs():
            root = SKILLS / doc.relative_to(SKILLS).parts[0]
            text = doc.read_text(encoding="utf-8")
            for target in self.LINK.findall(text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (doc.parent / target).exists():
                    broken.append(f"{doc.relative_to(REPO)} → {target}")
            for target in self.TICK.findall(text):
                if not ((root / target).exists() or (doc.parent / target).exists()):
                    broken.append(f"{doc.relative_to(REPO)} → `{target}`")
        self.assertEqual(broken, [], "깨진 상대 경로")

    def test_every_reference_is_linked_from_another_document(self):
        corpus = {doc: doc.read_text(encoding="utf-8") for doc in self._skill_docs()}
        for top in ("README.md", "AGENTS.md"):
            corpus[REPO / top] = (REPO / top).read_text(encoding="utf-8")
        orphans: list[str] = []
        for ref in sorted(SKILLS.glob("*/references/**/*.md")):
            refs_dir = SKILLS / ref.relative_to(SKILLS).parts[0] / "references"
            rel = ref.relative_to(refs_dir).as_posix()
            if not any(rel in text for doc, text in corpus.items() if doc != ref):
                orphans.append(str(ref.relative_to(REPO)))
        self.assertEqual(orphans, [], "어느 문서에서도 가리키지 않는 reference")

    def test_flagship_links_its_own_new_references(self):
        """플래그십 references는 SKILL.md 또는 master-playbook에서 직접 도달해야 한다."""
        flagship = SKILLS / install_skill.FLAGSHIP
        entry = (flagship / "SKILL.md").read_text(encoding="utf-8") + \
            (flagship / "references" / "master-playbook.md").read_text(encoding="utf-8")
        for ref in sorted((flagship / "references").glob("*.md")):
            if ref.name == "master-playbook.md":
                continue
            with self.subTest(reference=ref.name):
                self.assertIn(ref.name, entry)


class MultiHostDistributionTests(unittest.TestCase):
    def test_host_manifests_share_identity(self):
        import json
        manifests = [json.loads((REPO / path).read_text(encoding="utf-8")) for path in
                     ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json")]
        for key in ("name", "version", "description", "author"):
            self.assertTrue(all(m[key] == manifests[0][key] for m in manifests))
        self.assertEqual(manifests[0]["$schema"],
                         "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(manifests[1]["skills"], "./skills/")

    def test_marketplaces_point_at_the_complete_plugin(self):
        import json
        claude = json.loads((REPO / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        codex = json.loads((REPO / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(claude["name"], codex["name"])
        self.assertTrue(claude["owner"]["name"])
        self.assertTrue(claude["metadata"]["description"])
        for entry, source in ((claude["plugins"][0], claude["plugins"][0]["source"]),
                              (codex["plugins"][0], codex["plugins"][0]["source"]["path"])):
            self.assertEqual(entry["name"], "proposal-skills")
            self.assertTrue(source.startswith("./"))
            self.assertEqual((REPO / source).resolve(), REPO.resolve())
        self.assertEqual(codex["plugins"][0]["policy"]["installation"], "AVAILABLE")

    def test_archive_has_all_layers_and_excludes_cache_and_repo_metadata(self):
        import tempfile
        import zipfile
        import package_plugin
        with tempfile.TemporaryDirectory() as tmp:
            archive = package_plugin.build_archive(Path(tmp) / "plugin.zip")
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
                self.assertIsNone(z.testzip())
                self.assertTrue(set(package_plugin.PACKAGE_FILES).issubset(names))
                for name in install_skill.available_skills():
                    entry = f"skills/{name}/SKILL.md"
                    self.assertIn(entry, names)
                    self.assertEqual(z.read(entry), (REPO / entry).read_bytes())
                self.assertIn("skills/create-best-proposal/scripts/unified_gate.py", names)
                self.assertIn("skills/create-proposal-document/scripts/deck_check.py", names)
                self.assertIn("skills/create-winning-proposal/scripts/proposal_gate.py", names)
                self.assertFalse(any(package_plugin.CACHE_PARTS.intersection(Path(n).parts)
                                     or n.endswith((".pyc", ".pyo")) for n in names))
                self.assertTrue(all(n.startswith("skills/") or n in package_plugin.PACKAGE_FILES for n in names))

    def test_archive_does_not_overwrite_an_existing_file(self):
        import tempfile
        import package_plugin
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "keep.zip"
            dest.write_bytes(b"synthetic existing file")
            with self.assertRaises(FileExistsError):
                package_plugin.build_archive(dest)
            self.assertEqual(dest.read_bytes(), b"synthetic existing file")

    def test_incomplete_package_does_not_create_an_archive(self):
        import tempfile
        import package_plugin
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "missing.zip"
            with self.assertRaises(FileNotFoundError):
                package_plugin.build_archive(dest, root=Path(tmp))
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
