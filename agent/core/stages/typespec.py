from typing import TypedDict
import re

PROMPT = """
Given user application description and structured types and opetations,
generate TypeSpec models and interfaces for the application.

Application mostly operates on free-form user messages.
TypeSpec is augmented with special decorator that indicates that this function
is processed by language model parametrized with number of previous messages
passed to the LLM.

extern dec llm_func(target: unknown, history: valueof integer);

Example input:
<description>
Bot that records my diet and calculates calories.
</description>

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

Output:
<typespec>

model Dish {
    name: String
    ingredients: Ingredient[]
}

model Ingredient {
    name: String
    calories: Int
}

interface DietBot {
    @llm_func(1)
    recordDish(message: str): Dish;
    listDishes(from: Date, to: Date): Dish[];
}
</typespec>

User application description:
{{application_description}}

Application specification:
{{application_specification}}
""".strip()


class TypespecInput(TypedDict):
    application_description: str
    application_specification: str


class TypespecOutput(TypedDict):
    typespec_definitions: str


def parse_output(output: str) -> TypespecOutput:
    pattern = re.compile(
        r"<typespec>(.*?)</typespec>",
        re.DOTALL,
    )
    match = pattern.search(output)
    if match is None:
        raise ValueError("Failed to parse output")
    typespec_definitions = match.group(1).strip()
    return TypespecOutput(typespec_definitions=typespec_definitions)