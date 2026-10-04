from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import app.utils as utils


class ToolDefinitionsTest(unittest.TestCase):
    def test_read_write_and_bash_tools_are_available(self):
        try:
            tools = utils.get_tools()
        except FileNotFoundError as error:
            self.fail(f"Tool definitions could not be loaded: {error}")

        tools_by_name = {tool["function"]["name"]: tool for tool in tools}

        self.assertEqual(set(tools_by_name), {"Read", "Write", "Bash"})
        self.assertEqual(
            tools_by_name["Read"]["function"]["parameters"]["required"],
            ["file_path"],
        )
        self.assertEqual(
            tools_by_name["Write"]["function"]["parameters"]["required"],
            ["file_path", "content"],
        )
        self.assertEqual(
            tools_by_name["Bash"]["function"]["parameters"]["required"],
            ["command"],
        )

    def test_bash_executes_a_command_and_returns_its_output(self):
        if not hasattr(utils, "run_bash"):
            self.fail("Bash tool handler is missing")

        self.assertEqual(utils.run_bash("echo hello").strip(), "hello")

    def test_skill_prompt_advertises_frontmatter_without_bodies(self):
        if not hasattr(utils, "get_skills_prompt"):
            self.fail("Skill discovery is missing")

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            apple_dir = skills_dir / "apple"
            grape_dir = skills_dir / "grape"
            apple_dir.mkdir()
            grape_dir.mkdir()
            (apple_dir / "SKILL.md").write_text(
                "---\n"
                "name: apple\n"
                "description: Deploys the apple service to production.\n"
                "---\n\n"
                "SECRET APPLE BODY\n",
                encoding="utf-8",
            )
            (grape_dir / "SKILL.md").write_text(
                "---\n"
                "name: grape\n"
                'description: "Runs tests: reports failures."\n'
                "---\n\n"
                "SECRET GRAPE BODY\n",
                encoding="utf-8",
            )

            prompt = utils.get_skills_prompt(skills_dir)

        self.assertEqual(
            prompt,
            "You have access to the following skills:\n\n"
            "- apple: Deploys the apple service to production.\n"
            "- grape: Runs tests: reports failures.",
        )
        self.assertNotIn("SECRET", prompt)

    def test_named_skill_invocation_loads_only_that_skills_body(self):
        if not hasattr(utils, "get_skill_body"):
            self.fail("Named skill invocation is missing")

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            kestrel_dir = skills_dir / "kestrel"
            quartz_dir = skills_dir / "quartz"
            kestrel_dir.mkdir()
            quartz_dir.mkdir()
            (kestrel_dir / "SKILL.md").write_text(
                "---\nname: kestrel\ndescription: Runs tests.\n---\n\n"
                "Respond with exactly one word: nectarine\n",
                encoding="utf-8",
            )
            (quartz_dir / "SKILL.md").write_text(
                "---\nname: quartz\ndescription: Rotates credentials.\n---\n\n"
                "Respond with exactly one word: jujube\n",
                encoding="utf-8",
            )

            body = utils.get_skill_body("kestrel", skills_dir)

        self.assertEqual(body, "Respond with exactly one word: nectarine")
        self.assertNotIn("jujube", body)

    def test_skill_arguments_replace_full_indexed_and_short_placeholders(self):
        if not hasattr(utils, "render_skill_invocation"):
            self.fail("Skill argument substitution is missing")

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            skill_dir = skills_dir / "apple"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: apple\ndescription: Deploys apples.\n---\n\n"
                "Full: $ARGUMENTS. Reverse: $ARGUMENTS[1] $0. "
                "Again: $1 $0. Missing: <$2>.\n",
                encoding="utf-8",
            )

            rendered = utils.render_skill_invocation(
                "/apple staging eu-west", skills_dir
            )

        self.assertEqual(
            rendered,
            "Full: staging eu-west. Reverse: eu-west staging. "
            "Again: eu-west staging. Missing: <>.",
        )

    def test_skill_placeholders_become_empty_without_arguments(self):
        if not hasattr(utils, "render_skill_invocation"):
            self.fail("Skill argument substitution is missing")

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            skill_dir = skills_dir / "apple"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: apple\ndescription: Deploys apples.\n---\n\n"
                "<$ARGUMENTS>|<$ARGUMENTS[0]>|<$0>\n",
                encoding="utf-8",
            )

            rendered = utils.render_skill_invocation("/apple", skills_dir)

        self.assertEqual(rendered, "<>|<>|<>")

    def test_stacked_skills_share_arguments_and_exclude_uninvoked_skill(self):
        if not hasattr(utils, "render_skill_invocations"):
            self.fail("Stacked skill invocation is missing")

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            for name, body in (
                ("apple", "blueberry-$ARGUMENTS"),
                ("grape", "cherry-$ARGUMENTS"),
                ("pear", "dragonfruit-$ARGUMENTS"),
            ):
                skill_dir = skills_dir / name
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: Test skill.\n---\n\n{body}\n",
                    encoding="utf-8",
                )

            rendered = utils.render_skill_invocations(
                "/apple /grape 4127", skills_dir
            )

        self.assertEqual(rendered, ["blueberry-4127", "cherry-4127"])
        self.assertNotIn("dragonfruit", "\n".join(rendered))

    def test_stacking_stops_at_unknown_skill_and_keeps_remaining_arguments(self):
        if not hasattr(utils, "render_skill_invocations"):
            self.fail("Stacked skill invocation is missing")

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            apple_dir = skills_dir / "apple"
            apple_dir.mkdir()
            (apple_dir / "SKILL.md").write_text(
                "---\nname: apple\ndescription: Test skill.\n---\n\n"
                "Arguments: $ARGUMENTS\n",
                encoding="utf-8",
            )

            rendered = utils.render_skill_invocations(
                "/apple /pear 4127", skills_dir
            )

        self.assertEqual(rendered, ["Arguments: /pear 4127"])


if __name__ == "__main__":
    unittest.main()
