import pytest
from statemachine import State, StateMachine

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'

# Simple context to record events


class SimpleContext:
    def __init__(self):
        self.log: list[str] = []

    def dump(self) -> dict:
        return {"log": self.log.copy()}

    @classmethod
    def load(cls, data: dict) -> "SimpleContext":
        ctx = cls()
        ctx.log = data["log"]
        return ctx


class SimpleActor:
    def __init__(self):
        self.log: list[str] = []

    async def execute(self, *args, **kwargs) -> str:
        self.log.append("actor_executed")
        return "done"

    def dump(self) -> dict:
        return {"log": self.log.copy()}

    def load(self, data: dict):
        self.log = data["log"]


async def enter_A(ctx: SimpleContext):
    ctx.log.append("enter_A")


async def enter_B(ctx: SimpleContext):
    ctx.log.append("enter_B")


async def actor_on_done(ctx: SimpleContext, result: any):
    ctx.log.append("actor_on_done")


async def actor_on_error(ctx: SimpleContext, error: Exception):
    ctx.log.append("actor_on_error")

# Helper function to build a state machine with simple states and transitions.


def create_state(actor: SimpleActor) -> State[SimpleContext]:
    root = {
        "on": {"go": "A"},
        "states": {
            "A": {
                "entry": [enter_A],
                "invoke": {
                    "src": actor,
                    "input_fn": lambda ctx: [],
                    "on_done": {"target": "B", "actions": [actor_on_done]},
                    "on_error": {"target": "B", "actions": [actor_on_error]},
                },
                "states": {
                    "B": {
                        "entry": [enter_B],
                        "on": {"reset": "A"}
                    }
                },
            }
        }
    }
    return root


async def test_checkpoint_recovery():
    machine = StateMachine(create_state(SimpleActor()), SimpleContext())
    # Trigger transition: event "go" transitions from root to A and then, via invoke, to B.
    await machine.send("go")
    checkpoint = machine.dump()

    # Load a new machine from the checkpoint.
    loaded_machine = StateMachine[SimpleContext].load(create_state(SimpleActor()), checkpoint, SimpleContext)

    # Assert that the recovered state's stack path is equal to the original.
    assert machine.stack_path == loaded_machine.stack_path

    # Assert that the context log is recovered.
    assert machine.context.log == loaded_machine.context.log

    # Retrieve actor instances from the state machine structure.
    original_actor = machine.root["states"]["A"]["invoke"]["src"]
    loaded_actor = loaded_machine.root["states"]["A"]["invoke"]["src"]
    assert original_actor.dump() == loaded_actor.dump()


async def test_recovered_behavior():
    machine = StateMachine(create_state(SimpleActor()), SimpleContext())
    await machine.send("go")
    checkpoint = machine.dump()

    # Trigger on original
    await machine.send("reset")

    loaded_machine = StateMachine[SimpleContext].load(create_state(SimpleActor()), checkpoint, SimpleContext)
    await loaded_machine.send("reset")

    # Both machines should show identical context logs after the reset.
    assert machine.context.log == loaded_machine.context.log

    # Both machines should have same actor logs after the reset.
    original_actor = machine.root["states"]["A"]["invoke"]["src"]
    loaded_actor = loaded_machine.root["states"]["A"]["invoke"]["src"]
    assert original_actor.dump() == loaded_actor.dump()
