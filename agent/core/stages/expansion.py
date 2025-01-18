from typing import TypedDict
import re


PROMPT = """
Given user application description, expand it filling the missing details
into precise application specification including types and operations on them.
Keep number of types and operations to minimum required to cover the user description.

Example input:

<description>
Bot that records my diet and calculates calories.
</description>

Output:
<reasoning>
    The user application description is about a bot that records diet and calculates calories.
    The bot is a software application that records dishes and ingredients.
    The bot can list dishes and calculate calories for requested time period.
</reasoning>

<specification>
    <types>
        <type>dish</type>
        <type>ingredient</type>
    </types>
    <operations>
        <operation>record dish</operation>
        <operation>list dishes</operation>
    </operations>
</specification>

User application description:
{{application_description}}
""".strip()


class ExpansionInput(TypedDict):
    application_description: str


class ExpansionOutput(TypedDict):
    reasoning: str
    application_specification: str


def parse_output(output: str) -> ExpansionOutput:
    pattern = re.compile(
        r"<reasoning>(.*?)</reasoning>.*?<specification>(.*?)</specification>",
        re.DOTALL,
    )
    match = pattern.search(output)
    if match is None:
        raise ValueError("Failed to parse output")
    reasoning = match.group(1).strip()
    application_specification = match.group(2).strip()
    return ExpansionOutput(reasoning=reasoning, application_specification=application_specification)