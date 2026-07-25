from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_all_profile_svgs_are_valid_xml(self) -> None:
        paths = [
            ROOT / "github-metrics.svg",
            ROOT / "assets" / "hero-dark.svg",
            ROOT / "assets" / "hero-light.svg",
        ]

        for path in paths:
            with self.subTest(path=path.name):
                root = ET.parse(path).getroot()
                self.assertTrue(root.tag.endswith("svg"))

    def test_readme_local_links_resolve(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        references = re.findall(r'(?:href|src)="(\./[^"]+)"', readme)

        for reference in references:
            with self.subTest(reference=reference):
                path = ROOT / reference.removeprefix("./").split("#", 1)[0]
                self.assertTrue(path.is_file(), f"Missing local README target: {reference}")

    def test_latest_writing_markers_wrap_a_markdown_list(self) -> None:
        lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
        start = lines.index("<!-- BLOG-POST-LIST:START -->")
        end = lines.index("<!-- BLOG-POST-LIST:END -->")
        entries = [line for line in lines[start + 1 : end] if line]

        self.assertEqual(len(entries), 3)
        self.assertTrue(all(entry.startswith("- [") for entry in entries))

    def test_external_actions_are_pinned_to_full_commit_shas(self) -> None:
        uses_pattern = re.compile(r"^\s*uses:\s+[^@\s]+@([0-9a-f]{40})(?:\s+#.*)?$")
        workflow_paths = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

        self.assertTrue(workflow_paths)
        for path in workflow_paths:
            text = path.read_text(encoding="utf-8")
            self.assertIn("permissions: {}", text)
            for line in text.splitlines():
                if "uses:" not in line:
                    continue
                with self.subTest(path=path.name, line=line.strip()):
                    self.assertRegex(line, uses_pattern)

    def test_python_tooling_targets_only_python_314(self) -> None:
        validate_workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        ruff_config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertEqual((ROOT / ".python-version").read_text(encoding="utf-8").strip(), "3.14")
        self.assertNotIn("3.13", validate_workflow)
        self.assertIn('target-version = "py314"', ruff_config)

    def test_footprint_template_has_the_complete_contract(self) -> None:
        template = Template(
            (ROOT / "assets" / "github-metrics.template.svg").read_text(encoding="utf-8")
        )
        identifiers = set(template.get_identifiers())
        expected = {
            "followers",
            "forks",
            "generated_at",
            "language_1_width",
            "language_2_width",
            "language_2_x",
            "language_3_width",
            "language_3_x",
            "language_4_width",
            "language_4_x",
            "language_counts",
            "public_repositories",
            "stars",
        }

        self.assertEqual(identifiers, expected)

    def test_obsolete_integrations_are_absent(self) -> None:
        tracked_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "README.md",
                ROOT / ".github" / "workflows" / "refresh-profile.yml",
                ROOT / "scripts" / "update_profile.py",
            )
        ).casefold()

        self.assertNotIn("wakatime", tracked_text)
        self.assertNotIn("lowlighter", tracked_text)
        self.assertFalse((ROOT / ".github" / "workflows" / "metrics.yml").exists())
        self.assertFalse((ROOT / "github-metrics-live.svg").exists())


if __name__ == "__main__":
    unittest.main()
