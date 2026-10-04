import unittest

from app.utils import get_tools


class ToolDefinitionsTest(unittest.TestCase):
    def test_read_write_and_bash_tools_are_available(self):
        try:
            tools = get_tools()
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


if __name__ == "__main__":
    unittest.main()
