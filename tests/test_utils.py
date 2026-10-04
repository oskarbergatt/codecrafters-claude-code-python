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


if __name__ == "__main__":
    unittest.main()
