import json
import os
from pathlib import Path
import re
import subprocess

import yaml


def get_tools() -> list:
    script_path = os.path.dirname(os.path.abspath(__file__))
    tools_path = os.path.join(script_path, "tools.json")

    with open(tools_path) as tools_file:
        return json.load(tools_file)


def read_file(file_path: str) -> str:
    with open(file_path) as file:
        return file.read()


def write_file(file_path: str, content: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, "w") as file:
        file.write(content)

    return f"Successfully wrote to {file_path}"


def run_bash(command: str) -> str:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def get_skills_prompt(skills_dir: Path = Path(".claude/skills")) -> str:
    if not skills_dir.is_dir():
        return ""

    advertised_skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_file.is_file():
            continue

        lines = skill_file.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            continue

        try:
            frontmatter_end = next(
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            )
        except StopIteration:
            continue

        metadata = yaml.safe_load("\n".join(lines[1:frontmatter_end])) or {}
        name = metadata.get("name")
        description = metadata.get("description")
        if isinstance(name, str) and isinstance(description, str):
            advertised_skills.append(f"- {name}: {description}")

    if not advertised_skills:
        return ""

    return (
        "You have access to the following skills:\n\n"
        + "\n".join(advertised_skills)
        + "\n\nIf a skill matches the user's request, call the Skill tool with its name\n"
        "and follow the instructions it returns."
    )


def get_skill_body(
    skill_name: str, skills_dir: Path = Path(".claude/skills")
) -> str:
    if not re.fullmatch(r"[a-z0-9-]+", skill_name):
        return ""

    skill_file = skills_dir / skill_name / "SKILL.md"
    if not skill_file.is_file():
        return ""

    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""

    try:
        frontmatter_end = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        return ""

    return "\n".join(lines[frontmatter_end + 1 :]).strip()


def render_skill_invocation(
    prompt: str, skills_dir: Path = Path(".claude/skills")
) -> str:
    rendered_skills = render_skill_invocations(prompt, skills_dir)
    return rendered_skills[0] if rendered_skills else ""


def _substitute_skill_arguments(body: str, arguments: list[str]) -> str:
    full_arguments = " ".join(arguments)

    def replace_placeholder(match: re.Match[str]) -> str:
        if match.group(0) == "$ARGUMENTS":
            return full_arguments

        index_text = match.group(1) or match.group(2)
        index = int(index_text)
        return arguments[index] if index < len(arguments) else ""

    return re.sub(
        r"\$ARGUMENTS\[(\d+)\]|\$(\d+)|\$ARGUMENTS",
        replace_placeholder,
        body,
    )


def render_skill_invocations(
    prompt: str, skills_dir: Path = Path(".claude/skills")
) -> list[str]:
    return [body for _, body in _expand_skill_invocations(prompt, skills_dir)]


def _expand_skill_invocations(
    prompt: str, skills_dir: Path
) -> list[tuple[str, str]]:
    tokens = prompt.strip().split()
    skills = []
    argument_start = 0

    for index, token in enumerate(tokens):
        if not token.startswith("/"):
            argument_start = index
            break

        body = get_skill_body(token[1:], skills_dir)
        if not body:
            argument_start = index
            break

        skills.append((token[1:], body))
        argument_start = index + 1

    arguments = tokens[argument_start:]
    return [
        (skill_name, _substitute_skill_arguments(body, arguments))
        for skill_name, body in skills
    ]


def render_skill_messages(
    prompt: str, skills_dir: Path = Path(".claude/skills")
) -> list[str]:
    return [
        f"Skill: {skill_name} "
        f"(located at {(skills_dir / skill_name).as_posix()})\n"
        "Paths in the instructions below are relative to that folder.\n\n"
        f"{body}"
        for skill_name, body in _expand_skill_invocations(prompt, skills_dir)
    ]


def load_skill(
    name: str,
    args: str = "",
    skills_dir: Path = Path(".claude/skills"),
) -> str:
    prompt = f"/{name}"
    if args:
        prompt += f" {args}"

    messages = render_skill_messages(prompt, skills_dir)
    if not messages:
        return f"Skill not found: {name}"
    return messages[0]
