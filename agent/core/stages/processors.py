from typing import TypedDict
import re


PROMPT_PRE = """
Given TypeSpec application definition examine arguments of {{function_name}} function.
Generate pairs of example user inputs and outputs matching the function signature.

TypeSpec definition:
<typespec>
{{typespec_definitions}}
</typespec>

Return output in the format:
<instructions>
// General instruction for LLM when handling user input for {{function_name}} function.
// Includes rules for imputing arguments that might be missing in the user input.
</instructions>

<examples>
    <example>
        <input>// Example user input</input>
        <output>// Expected structured JSON output</output>
    </example>
</examples>
""".strip()


class PreprocessorInput(TypedDict):
    typespec_definitions: str
    function_name: str


class PreprocessorOutput(TypedDict):
    instructions: str
    examples: list[tuple[str, str]]


def parse_output(output: str) -> PreprocessorOutput:
    pattern = re.compile(
        r"<instructions>(.*?)</instructions>.*?<examples>(.*?)</examples>",
        re.DOTALL,
    )
    match = pattern.search(output)
    if match is None:
        raise ValueError("Failed to parse output")
    instructions = match.group(1).strip()
    examples = re.findall(r"<example>\s*<input>(.*?)</input>\s*<output>(.*?)</output>\s*</example>", match.group(2), re.DOTALL)
    return PreprocessorOutput(instructions=instructions, examples=examples)