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

        self.assertGreaterEqual(len(entries), 5)
        for entry in entries:
            self.assertRegex(
                entry,
                r"^- \[.+]\(https://zenn\.dev/yhay81/(?:articles|books)/[^)]+\)"
                r" — \d{4}-\d{2}-\d{2}$",
            )

    def test_proof_of_work_is_curated_and_distinct_from_pinned_repositories(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("https://github.com/haya-inc/wasmhatch", readme)
        self.assertIn("https://github.com/haya-inc/clawsembly", readme)
        self.assertIn("https://github.com/haya-inc/hayasend", readme)
        self.assertIn("https://github.com/hayatepy/hayate", readme)
        self.assertIn("https://github.com/yhay81/socialname", readme)
        for tool in (
            "sqrail",
            "cmdtrail",
            "taskattest",
            "dmlpact",
            "procherd",
            "blobdive",
            "hopwhy",
            "avpact",
        ):
            self.assertIn(f"https://github.com/yhay81/{tool}", readme)
        self.assertIn("https://firsthand.work/", readme)
        self.assertIn("https://ai-partners.info/", readme)
        self.assertIn("https://demand.ai-partners.info/", readme)
        self.assertIn("https://github.com/yhay81/tool-shelf", readme)
        self.assertNotIn("profile:repositories", readme)
        self.assertNotIn("Live OSS telemetry", readme)
        self.assertNotIn("DeskOne", readme)
        self.assertNotIn("https://github.com/yhay81/firsthand", readme)

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

    def test_profile_refresh_is_weekly_and_uses_only_github_owned_actions(self) -> None:
        refresh_workflow = (ROOT / ".github" / "workflows" / "refresh-profile.yml").read_text(
            encoding="utf-8"
        )
        footprint_template = (ROOT / "assets" / "github-metrics.template.svg").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn('cron: "11 21 * * 4"', refresh_workflow)
        self.assertIn("timeout-minutes: 1", refresh_workflow)
        self.assertNotIn("[skip ci]", refresh_workflow)
        self.assertNotIn("blog-post-workflow", refresh_workflow)
        self.assertTrue(
            all(
                "uses: actions/" in line
                for line in refresh_workflow.splitlines()
                if "uses:" in line
            )
        )
        self.assertNotIn("$generated_at", footprint_template)
        self.assertIn("weekly refresh", footprint_template)
        self.assertIn("regenerated weekly", readme)

    def test_footprint_template_has_the_complete_contract(self) -> None:
        template = Template(
            (ROOT / "assets" / "github-metrics.template.svg").read_text(encoding="utf-8")
        )
        identifiers = set(template.get_identifiers())
        expected = {
            "followers",
            "forks",
            "leading_language",
            "language_counts",
            "language_legend",
            "language_segments",
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
        self.assertNotIn("blog-post-workflow", tracked_text)
        self.assertNotIn("haya.company", tracked_text)
        self.assertIn("https://haya-inc.co.jp/", tracked_text)
        self.assertFalse((ROOT / ".github" / "workflows" / "metrics.yml").exists())
        self.assertFalse((ROOT / "github-metrics-live.svg").exists())


if __name__ == "__main__":
    unittest.main()
