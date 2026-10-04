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


if __name__ == "__main__":
    unittest.main()
