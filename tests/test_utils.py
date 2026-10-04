import unittest

from app.utils import get_tools


class ToolDefinitionsTest(unittest.TestCase):
    def test_read_and_write_tools_are_available(self):
        try:
            tools = get_tools()
        except FileNotFoundError as error:
            self.fail(f"Tool definitions could not be loaded: {error}")

        tools_by_name = {tool["function"]["name"]: tool for tool in tools}

        self.assertEqual(set(tools_by_name), {"Read", "Write"})
        self.assertEqual(
            tools_by_name["Read"]["function"]["parameters"]["required"],
            ["file_path"],
        )
        self.assertEqual(
            tools_by_name["Write"]["function"]["parameters"]["required"],
            ["file_path", "content"],
        )


if __name__ == "__main__":
    unittest.main()
