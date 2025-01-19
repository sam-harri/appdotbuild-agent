from typing import TypedDict
import re

PROMPT = """
Given user application description and structured types and operations,
generate TypeSpec models and interface for the application. Output just a single interface.
Every decorated @llm_func operates on free-form text messages and it's arguments should be
easily extractable from chat messages. Keep argument complexity within what can be extracted / inferred
from the chat messages directly.

Application operates ONLY on free-form text messages.
TypeSpec is extended with special decorator that indicates that this function
is processed by language model parametrized with number of previous messages passed to the LLM.

extern dec llm_func(target: unknown, history: valueof int32);

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
    recordDish(dish: Dish): void;
    @llm_func(1)
    listDishes(from: Date, to: Date): Dish[];
}
</typespec>

User application description:
{{application_description}}

Application specification:
{{application_specification}}

Return TypeSpec definition encompassed with <typespec> tag.
""".strip()


class TypespecInput(TypedDict):
    application_description: str
    application_specification: str


class TypespecOutput(TypedDict):
    typespec_definitions: str
    llm_functions: list[str]


def parse_output(output: str) -> TypespecOutput:
    pattern = re.compile(
        r"<typespec>(.*?)</typespec>",
        re.DOTALL,
    )
    match = pattern.search(output)
    if match is None:
        raise ValueError("Failed to parse output")
    typespec_definitions = match.group(1).strip()
    llm_functions = re.findall(
        r'@llm_func\(\d+\)\s*(\w+)\s*\(',
        typespec_definitions
    )
    return TypespecOutput(typespec_definitions=typespec_definitions, llm_functions=llm_functions)