import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import app.main as main_module


def response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs["messages"]))
        return self.responses.pop(0)


class SubagentTest(unittest.TestCase):
    def test_forked_skill_runs_with_only_its_body_and_returns_answer(self):
        if not hasattr(main_module, "run_agent"):
            self.fail("Reusable agent loop is missing")

        skill_call = SimpleNamespace(
            id="skill-call",
            function=SimpleNamespace(
                name="Skill",
                arguments=json.dumps({"name": "apple"}),
            ),
        )
        completions = FakeCompletions(
            [
                response(tool_calls=[skill_call]),
                response(content="blueberry", tool_calls=None),
                response(
                    content="The on-call engineer is blueberry.",
                    tool_calls=None,
                ),
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )

        with TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir)
            apple_dir = skills_dir / "apple"
            grape_dir = skills_dir / "grape"
            apple_dir.mkdir()
            grape_dir.mkdir()
            (apple_dir / "SKILL.md").write_text(
                "---\n"
                "name: apple\n"
                "description: Use for on-call rotation questions.\n"
                "context: fork\n"
                "---\n\n"
                "Respond with exactly one word: blueberry\n",
                encoding="utf-8",
            )
            (grape_dir / "SKILL.md").write_text(
                "---\nname: grape\ndescription: Decoy skill.\n---\n\n"
                "Respond with exactly one word: jujube\n",
                encoding="utf-8",
            )

            result = main_module.run_agent(
                client,
                "test-model",
                [],
                [
                    {
                        "role": "user",
                        "content": "Who is on the on-call rotation right now?",
                    }
                ],
                skills_dir,
            )

        self.assertEqual(result, "The on-call engineer is blueberry.")
        self.assertEqual(
            completions.requests[1],
            [
                {
                    "role": "user",
                    "content": "Respond with exactly one word: blueberry",
                }
            ],
        )
        self.assertNotIn(
            "Who is on the on-call rotation",
            str(completions.requests[1]),
        )
        self.assertIn("blueberry", str(completions.requests[2]))
        self.assertNotIn("jujube", str(completions.requests))


if __name__ == "__main__":
    unittest.main()
