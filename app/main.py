import argparse
import os
import sys
import json
from pathlib import Path
from typing import Any, cast
from openai import OpenAI
from .utils import (
    get_skill_context,
    get_skills_prompt,
    get_tools,
    load_skill,
    read_file,
    render_skill_invocation,
    render_skill_messages,
    run_bash,
    write_file,
)

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def run_agent(
    client: Any,
    model: str,
    tools: list,
    messages: list[Any],
    skills_dir: Path = Path(".claude/skills"),
) -> str:
    while True:
        chat = client.chat.completions.create(
            model=model, messages=messages, max_tokens=1000, tools=tools
        )

        if not chat.choices:
            raise RuntimeError("no choices in response")

        message = chat.choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
        )

        if not message.tool_calls:
            return message.content or ""

        for tool_call in message.tool_calls:
            tool_name = getattr(tool_call.function, "name", None) or getattr(
                tool_call, "name", None
            )
            tool_args = getattr(tool_call.function, "arguments", None) or getattr(
                tool_call, "arguments", None
            )
            if tool_args is None:
                tool_kwargs = {}
            else:
                if isinstance(tool_args, (bytes, bytearray)):
                    tool_args = tool_args.decode()
                tool_kwargs = json.loads(tool_args)

            if tool_name == "Read":
                result = read_file(**tool_kwargs)
            elif tool_name == "Write":
                result = write_file(**tool_kwargs)
            elif tool_name == "Bash":
                result = run_bash(**tool_kwargs)
            elif tool_name == "Skill":
                skill_name = tool_kwargs.get("name", "")
                skill_args = tool_kwargs.get("args", "")
                if get_skill_context(skill_name, skills_dir) == "fork":
                    prompt = f"/{skill_name}"
                    if skill_args:
                        prompt += f" {skill_args}"
                    skill_body = render_skill_invocation(prompt, skills_dir)
                    subagent_answer = run_agent(
                        client,
                        model,
                        tools,
                        [{"role": "user", "content": skill_body}],
                        skills_dir,
                    )
                    result = (
                        f"Skill {skill_name} ran in a separate context and returned: "
                        f"{subagent_answer}"
                    )
                else:
                    result = load_skill(
                        skill_name,
                        skill_args,
                        skills_dir,
                    )
            else:
                raise RuntimeError(f"Unknown tool: {tool_name}")

            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result}
            )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    tools = get_tools()
    messages: list[Any] = []
    skills_prompt = get_skills_prompt()
    if skills_prompt:
        messages.append({"role": "system", "content": skills_prompt})
    skill_messages = render_skill_messages(args.p)
    if skill_messages:
        messages.extend(
            {"role": "user", "content": skill_message}
            for skill_message in skill_messages
        )
    else:
        messages.append({"role": "user", "content": args.p})

    model = "anthropic/claude-haiku-4.5"

    print(run_agent(client, model, tools, messages))


if __name__ == "__main__":
    main()
