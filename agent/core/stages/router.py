from typing import TypedDict
import re


PROMPT = """
Given TypeSpec application definition for all functions decorated with @llm_func
generate prompt for the LLM to classify which function should handle user request.
For each function generate description of user intent.

Example input:

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
    @llm_func("pre", 1)
    recordDish(dish: Dish): void;
    @llm_func("wrap", 1)
    listDishes(from: Date, to: Date): Dish[];
}
</typespec>

Example output:
<functions>
<function name="recordDish">
Log user's dish. Examples:
- "I ate a burger."
- "I had a salad for lunch."
- "Chili con carne"
</function>
<function name="listDishes">
List user's dishes. Examples:
- "What did I eat yesterday?"
- "Show me my meals for last week."
</function>
</functions>
""".strip()


class RouterInput(TypedDict):
    application_description: str


class Function(TypedDict):
    name: str
    description: str


class RouterOutput(TypedDict):
    functions: list[Function]


def parse_output(output: str) -> RouterOutput:
    pattern = re.compile(
        r"<functions>(.*?)</functions>",
        re.DOTALL,
    )
    match = pattern.search(output)
    if match is None:
        raise ValueError("Failed to parse output")
    functions = match.group(1).strip()
    functions_pattern = re.compile(r'<function name="(.*?)">(.*?)</function>', re.DOTALL)
    functions = functions_pattern.findall(functions)
    return RouterOutput(functions=[Function(name=name, description=description) for name, description in functions])