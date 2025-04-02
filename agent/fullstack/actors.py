import dataclasses
import logic
import statemachine
from models.common import Message
from workspace import Workspace


@dataclasses.dataclass
class NodeData:
    workspace: Workspace
    messages: list[Message]
    files: dict[str, str] = dataclasses.field(default_factory=dict)

    def head(self) -> Message:
        if (num_messages := len(self.messages)) != 1:
            raise ValueError(f"Expected 1 got {num_messages} messages: {self.messages}")
        if self.messages[0].role != "assistant":
            raise ValueError(f"Expected assistant role in message: {self.messages}")
        return self.messages[0]


class BaseSearchActor(statemachine.Actor):
    workspace: Workspace
    root: logic.Node[NodeData] | None

    async def dump(self) -> object:
        if self.root is None:
            return []
        stack, result = [self.root], []
        while stack:
            node = stack.pop()
            result.append({
                "id": node._id,
                "parent": node.parent._id if node.parent else None,
                "data": {
                    "messages": [msg.to_dict() for msg in node.data.messages],
                    "files": node.data.files,
                },
            })
            stack.extend(node.children)
        return result

    async def load(self, data: object):
        if not isinstance(data, list):
            raise ValueError(f"Expected list got {type(data)}")
        if not data:
            return
        id_to_node: dict[str, logic.Node[NodeData]] = {}
        for item in data:
            parent = id_to_node[item["parent"]] if item["parent"] else None
            messages = [Message.from_dict(msg) for msg in item["data"]["messages"]]
            ws = parent.data.workspace.clone() if parent else self.workspace.clone()
            for file, content in item["data"]["files"].items():
                ws.write_file(file, content)
            data = NodeData(ws, messages, item["data"]["files"])
            node = logic.Node(data, parent, item["id"])
            if parent:
                parent.children.append(node)
            else:
                self.root = node
            id_to_node[item["id"]] = node
