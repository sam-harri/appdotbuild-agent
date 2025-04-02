import pytest
import dagger
from logic import Node
from actors import BaseSearchActor, NodeData
from models.common import Message, TextRaw
from workspace import Workspace

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


class SimpleActor(BaseSearchActor):
    def __init__(self, workspace: Workspace, root: Node[NodeData] | None = None):
        self.workspace = workspace
        self.root = root
    
    def execute(self, *args, **kwargs):
        pass


async def test_actor_recovery():
    async with dagger.connection():
        workspace = await Workspace.create()
        root = Node[NodeData](NodeData(
            workspace=workspace.clone(),
            messages=[Message(role="user", content=[TextRaw("test")])],
        ))
        workspace_child = workspace.clone()
        workspace_child.write_file("test.txt", "test")
        child = Node[NodeData](NodeData(
            workspace=workspace_child,
            messages=[Message(role="assistant", content=[TextRaw("test child")])],
            files={"test.txt": "test"},
        ), parent=root)
        root.children.append(child)
        actor = SimpleActor(workspace, root)
        dumped = await actor.dump()

        loaded = SimpleActor(await Workspace.create())
        await loaded.load(dumped)

        assert loaded.root.data.files == root.data.files
        assert loaded.root.data.messages == root.data.messages

        loaded_child = loaded.root.children[0]
        assert loaded_child.data.files == child.data.files
        assert loaded_child.data.messages == child.data.messages
        assert await loaded_child.data.workspace.read_file("test.txt") == "test"
