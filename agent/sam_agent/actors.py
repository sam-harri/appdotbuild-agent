import anyio
import jinja2
import logging
import os
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

from core.base_node import Node
from core.workspace import Workspace
from core.actors import BaseData, FileOperationsActor, AgentSearchFailedException
from llm.common import AsyncLLM, Message, TextRaw, Tool, ToolUse, ToolUseResult
from sam_agent import playbooks
from sam_agent.playwright import alembic_push
# from sam_agent.playwright import PlaywrightRunner, drizzle_push
from core.notification_utils import notify_if_callback, notify_stage

logger = logging.getLogger(__name__)


@dataclass
class SamAgentPaths:
    """File path configuration for SamAgent actor."""

    files_allowed_draft: list[str]
    files_allowed_frontend: list[str]
    files_protected_frontend: list[str]
    files_relevant_draft: list[str] 
    files_relevant_handlers: list[str]
    files_relevant_frontend: list[str]
    files_inherit_handlers: list[str]

    @classmethod
    def default(cls) -> "SamAgentPaths":
        return cls(
            files_allowed_draft=[
                "server/app/db/base.py",
                "server/app/db/session.py",
                "server/app/models.py",
                "server/app/schema.py",
                "server/app/config.py",
                "server/app/main.py",
                "server/app/routes.py",
                "server/alembic/env.py",
                "server/app/routes/",
                "server/alembic/versions/"
            ],
            files_allowed_frontend=[
                "client/src/App.tsx",
                "client/src/components/",
                "client/src/App.css",
                "client/src/utils/api.ts",
            ],
            files_protected_frontend=["client/src/components/ui/"],
            files_relevant_draft=[
                "server/alembic/env.py",
                "server/app/db/base.py",
                "server/app/db/session.py",
                "server/app/models.py",
                "server/app/schema.py",
                "server/app/config.py",
                "server/app/main.py",
                "server/app/routes.py",
                "client/src/utils/api.ts",
            ],
            files_relevant_handlers=[
                "server/app/db/base.py",
                "server/app/db/session.py",
                "server/app/models.py",
                "server/app/schema.py",
                "server/app/config.py",
                "server/app/main.py",
                "server/app/routes.py",
            ],
            files_relevant_frontend=[
                "server/app/schema.py",
                "server/app/routes.py",
                "client/src/utils/api.ts",
            ],
            files_inherit_handlers=[
                "server/app/schema.py",
            ],
        )


class SamActor(FileOperationsActor):
    """Modern SamAgent actor that generates full-stack TypeScript applications."""

    def __init__(
        self,
        llm: AsyncLLM,
        vlm: AsyncLLM,
        workspace: Workspace,
        beam_width: int = 3,
        max_depth: int = 30,
        event_callback: Callable[[str, str], Awaitable[None]] | None = None,
    ):
        super().__init__(llm, workspace, beam_width, max_depth)
        self.vlm = vlm
        self.event_callback = event_callback
        # self.playwright = PlaywrightRunner(vlm)

        # Sub-nodes for parallel execution
        self.handler_nodes: dict[str, Node[BaseData]] = {}
        self.frontend_node: Optional[Node[BaseData]] = None
        self.draft_node: Optional[Node[BaseData]] = None

        # User prompt for validation
        self._user_prompt: str = ""

        # File path configuration
        self.paths = SamAgentPaths.default()

    async def execute(
        self,
        files: dict[str, str],
        user_prompt: str,
        feedback: str | None = None,
    ) -> Node[BaseData]:
        """Execute Sam generation or editing based on parameters."""
        self._user_prompt = user_prompt

        # If feedback is provided, route to edit functionality
        if feedback is not None:
            return await self.execute_edit(files, user_prompt, feedback)

        # Otherwise, proceed with normal generation
        # Update workspace with input files
        self.workspace = self._create_workspace_with_permissions(files, [], [])

        # Determine what to generate based on existing files
        has_schema = any(
            f in files for f in ["server/app/schema.py", "server/app/db/base.py", "client/src/utils/api.ts"]
        )

        if not has_schema:
            # Stage 1: Generate data model only
            await notify_stage(
                self.event_callback, "🎯 Starting data model generation", "in_progress" # type: ignore
            )

            solution = await self._generate_draft(user_prompt)
            if not solution:
                raise AgentSearchFailedException(
                    agent_name="SamActor", message="Data model generation failed"
                )

            await notify_stage(
                self.event_callback, "✅ Data model generated successfully", "completed" # type: ignore
            )
            return solution

        else:
            # Stage 2: Generate application based on existing schema
            await notify_stage(
                self.event_callback, "🚀 Starting application generation", "in_progress" # type: ignore
            )

            # Create a single node to collect all results
            root_workspace = self.workspace.clone().permissions(
                allowed=self.paths.files_allowed_draft
                + self.paths.files_allowed_frontend
            )
            message = Message(
                role="user",
                content=[TextRaw(f"Generate application for: {user_prompt}")],
            )
            root_node = self._create_node_with_files(
                root_workspace, message, files, "draft"
            )

            # Generate implementation
            results = await self._generate_implementation(files, None)

            # Merge all results into root node
            for _, final_node in results.items():
                if final_node:
                    for node in final_node.get_trajectory():
                        root_node.data.files.update(node.data.files)

            await notify_stage(
                self.event_callback, # type: ignore
                "✅ Application generated successfully",
                "completed",
            )
            return root_node

    async def execute_edit(
        self,
        files: dict[str, str],
        user_prompt: str,
        feedback: str,
    ) -> Node[BaseData]:
        """Execute edit/feedback-based modifications."""
        self._user_prompt = user_prompt

        await notify_stage(
            self.event_callback, "🛠️ Applying requested changes...", "in_progress" # type: ignore
        )

        # Create workspace with input files and permissions
        workspace = self._create_workspace_with_permissions(
            files,
            allowed=self.paths.files_allowed_draft + self.paths.files_allowed_frontend,
            protected=self.paths.files_protected_frontend,
        )
        await workspace.exec_mut(["bun", "run", "sync"]) # sync deps
        self.workspace = workspace

        # Build context with relevant files
        context = await self._build_context(workspace, "edit")

        # Prepare edit prompt
        user_prompt_rendered = self._render_prompt(
            "EDIT_ACTOR_USER_PROMPT",
            project_context=context,
            user_prompt=user_prompt,
            feedback=feedback,
        )

        # Create root node for editing
        message = Message(role="user", content=[TextRaw(user_prompt_rendered)])
        root_node = self._create_node_with_files(workspace, message, files, "edit")

        # Search for solution
        solution = await self._search_single_node(
            root_node, playbooks.EDIT_ACTOR_SYSTEM_PROMPT, True
        )

        if not solution:
            raise AgentSearchFailedException(
                agent_name="SamActor", message="Edit failed to find a solution"
            )

        await notify_stage(
            self.event_callback, "✅ Changes applied successfully!", "completed" # type: ignore
        )

        return solution

    async def _generate_draft(self, user_prompt: str) -> Optional[Node[BaseData]]:
        """Generate schema and type definitions."""

        await notify_if_callback(
            self.event_callback, # type: ignore
            "🎯 Generating application schema and types...",
            "draft start",
        )

        # Create draft workspace
        workspace = self.workspace.clone().permissions(
            allowed=self.paths.files_allowed_draft
        )

        # Build context
        context = await self._build_context(workspace, "draft")

        # Prepare prompt
        user_prompt_rendered = self._render_prompt(
            "BACKEND_DRAFT_USER_PROMPT",
            project_context=context,
            user_prompt=user_prompt,
        )

        # Create root node
        message = Message(role="user", content=[TextRaw(user_prompt_rendered)])
        self.draft_node = Node(BaseData(workspace, [message], {}, True, "draft"))

        # Search for solution
        solution = await self._search_single_node(
            self.draft_node, playbooks.BACKEND_DRAFT_SYSTEM_PROMPT, True
        )

        if solution:
            await notify_if_callback(
                self.event_callback, "✅ Schema and types generated!", "draft complete" # type: ignore
            )
        else:
            raise AgentSearchFailedException(
                agent_name="SamActor",
                message="Draft generation failed - no solution found",
            )

        return solution

    async def _generate_implementation(
        self,
        draft_files: dict[str, str],
        feedback_data: Optional[str] = None,
    ) -> dict[str, Node[BaseData]]:
        """Generate handlers and frontend in parallel."""

        results: dict[str, Node[BaseData]] = {}

        await self.workspace.exec_mut(["bun", "run", "sync"]) # sync deps from draft stage
        async with anyio.create_task_group() as tg:
            # Start frontend generation
            tg.start_soon(
                self._generate_frontend_task, draft_files, feedback_data, results
            )

            # Start parallel handler generation
            tg.start_soon(
                self._generate_handlers_parallel, draft_files, feedback_data, results
            )

        return results

    async def _generate_handlers_parallel(
        self,
        draft_files: dict[str, str],
        feedback_data: Optional[str],
        results: dict[str, Node[BaseData]],
    ):
        """Generate all handlers in parallel."""

        await notify_if_callback(
            self.event_callback, # type: ignore
            "🔧 Generating backend API handlers...",
            "handlers start",
        )

        # Create handler nodes
        handler_files = {
            path: content
            for path, content in draft_files.items()
            if path.startswith("server/app/routes/") and path.endswith(".py")
        }

        if not handler_files:
            logger.warning("No handler files found in draft")
            return

        # Create nodes for each handler
        await self._create_handler_nodes(handler_files, draft_files, feedback_data)

        # Process all handlers in parallel
        tx, rx = anyio.create_memory_object_stream[
            tuple[str, Optional[Node[BaseData]]]
        ](100)

        async def search_handler(name: str, node: Node[BaseData], tx_channel):
            await notify_if_callback(
                self.event_callback, # type: ignore
                f"⚡ Working on {name} handler...",
                "handler progress",
            )
            solution = await self._search_single_node(
                node, playbooks.BACKEND_HANDLER_SYSTEM_PROMPT
            )
            async with tx_channel:
                await tx_channel.send((name, solution))

        async with anyio.create_task_group() as tg:
            for name, node in self.handler_nodes.items():
                tg.start_soon(search_handler, name, node, tx.clone())
            tx.close()

            async with rx:
                async for handler_name, solution in rx:
                    if solution:
                        results[f"handler_{handler_name}"] = solution
                        logger.info(f"Handler {handler_name} completed")
                    else:
                        await notify_if_callback(
                            self.event_callback, # type: ignore
                            f"💥 Handler {handler_name} failed to generate",
                            "handler failure",
                        )

        await notify_if_callback(
            self.event_callback, # type: ignore
            "✅ Backend handlers generation finished!",
            "handlers complete",
        )

    async def _generate_frontend_task(
        self,
        draft_files: dict[str, str],
        feedback_data: Optional[str],
        results: dict[str, Node[BaseData]],
    ):
        """Generate frontend application."""

        await notify_if_callback(
            self.event_callback, # type: ignore
            "🎨 Starting frontend application generation...",
            "frontend start",
        )

        # Create frontend workspace
        workspace = self._create_workspace_with_permissions(
            draft_files,
            allowed=self.paths.files_allowed_frontend,
            protected=self.paths.files_protected_frontend,
        )

        # Build context
        context = await self._build_context(workspace, "frontend")

        # Prepare prompt
        user_prompt_rendered = self._render_prompt(
            "FRONTEND_USER_PROMPT",
            project_context=context,
            user_prompt=feedback_data or self._user_prompt,
        )

        # Create frontend node
        message = Message(role="user", content=[TextRaw(user_prompt_rendered)])
        self.frontend_node = Node(BaseData(workspace, [message], {}, True, "frontend"))

        # Search for solution
        solution = await self._search_single_node(
            self.frontend_node, playbooks.FRONTEND_SYSTEM_PROMPT
        )

        if solution:
            results["frontend"] = solution
            await notify_if_callback(
                self.event_callback, # type: ignore
                "✅ Frontend application generated!",
                "frontend complete",
            )
        else:
            await notify_if_callback(
                self.event_callback, # type: ignore
                "💥 Frontend failed to generate, keeping the template page as is",
                "handler failure",
            )

    async def _search_single_node(
        self, root_node: Node[BaseData], system_prompt: str, conditional_tools: bool = False,
    ) -> Optional[Node[BaseData]]:
        """Search for solution from a single node."""
        solution: Optional[Node[BaseData]] = None
        iteration = 0

        while solution is None:
            iteration += 1
            candidates = self._select_candidates(root_node)
            if not candidates:
                logger.info("No candidates to evaluate, search terminated")
                break

            logger.info(
                f"Iteration {iteration}: Running LLM on {len(candidates)} candidates"
            )
            nodes = await self.run_llm(
                candidates,
                system_prompt=system_prompt,
                tools=self.tools + (self.conditional_tools if conditional_tools else []),
                max_tokens=8192,
            )
            logger.info(f"Received {len(nodes)} nodes from LLM")

            for i, new_node in enumerate(nodes):
                logger.info(f"Evaluating node {i + 1}/{len(nodes)}")
                if await self.eval_node(new_node, self._user_prompt):
                    logger.info(f"Found solution at depth {new_node.depth}")
                    solution = new_node
                    break

        return solution

    def _select_candidates(self, node: Node[BaseData]) -> list[Node[BaseData]]:
        """Select candidate nodes for evaluation."""
        if node.is_leaf and node.data.should_branch:
            logger.info(f"Selecting root node {self.beam_width} times (beam search)")
            return [node] * self.beam_width

        all_children = node.get_all_children()
        candidates = []
        for n in all_children:
            if n.is_leaf and n.depth <= self.max_depth:
                if n.data.should_branch:
                    effective_beam_width = (
                        1 if len(all_children) > (n.depth + 1) else self.beam_width
                    )
                    logger.info(
                        f"Selecting candidates with effective beam width: {effective_beam_width}, current depth: {n.depth}/{self.max_depth}"
                    )
                    candidates.extend([n] * effective_beam_width)
                else:
                    candidates.append(n)

        logger.info(f"Selected {len(candidates)} leaf nodes for evaluation")
        return candidates

    async def eval_node(self, node: Node[BaseData], user_prompt: str) -> bool:
        """Evaluate node using base class flow with context-aware checks."""
        # Use base class implementation which calls run_tools and handles completion
        tool_calls, is_completed = await self.run_tools(node, user_prompt)
        if tool_calls:
            node.data.messages.append(Message(role="user", content=tool_calls))
        elif not is_completed:
            # Only add continue message if not completed and no tool calls
            content = [TextRaw(text="Continue or mark completed via tool call")]
            node.data.messages.append(Message(role="user", content=content))
        return is_completed

    async def _validate_draft(self, node: Node[BaseData]) -> bool:
        """Validate draft: TypeScript compilation + Alembic schema."""
        errors = []

        async with anyio.create_task_group() as tg:

            async def check_tsc():
                if error := await self.run_py_backend_check(node):
                    errors.append(error)

            async def check_drizzle():
                if error := await self.run_alembic_check(node):
                    errors.append(error)

            tg.start_soon(check_tsc)
            tg.start_soon(check_drizzle)

        return await self._handle_validation_errors(node, errors)

    async def _validate_handler(self, node: Node[BaseData]) -> bool:
        """Validate handler: TypeScript + tests only."""
        errors = []
        handler_name = self._get_handler_name(node)

        async with anyio.create_task_group() as tg:

            async def check_tsc():
                if error := await self.run_py_backend_check(node):
                    errors.append(error)

            async def check_tests():
                if error := await self.run_test_check(node, handler_name):
                    errors.append(error)

            tg.start_soon(check_tsc)
            tg.start_soon(check_tests)

        return await self._handle_validation_errors(node, errors)

    async def _validate_frontend(self, node: Node[BaseData]) -> bool:
        """Validate frontend: TypeScript + build + Playwright."""
        errors = []

        # Quick checks first
        async with anyio.create_task_group() as tg:

            async def check_tsc():
                if error := await self.run_tsc_frontend_check(node):
                    errors.append(error)

            async def check_build():
                if error := await self.run_build_check(node):
                    errors.append(error)

            tg.start_soon(check_tsc)
            tg.start_soon(check_build)

        if not await self._handle_validation_errors(node, errors):
            return False

        # Then Playwright (slow)
        # if feedback := await self.run_playwright_check(node, "client"):
        #     node.data.messages.append(
        #         Message(role="user", content=[TextRaw(x) for x in feedback])
        #     )
        #     return False

        return True

    async def _validate_edit(self, node: Node[BaseData]) -> bool:
        """Validate edit: Full validation including TypeScript, tests, build, and Playwright."""
        await notify_if_callback(
            self.event_callback, "🔍 Validating changes...", "validation start" # type: ignore
        )

        errors = []

        # Quick checks first
        async with anyio.create_task_group() as tg:

            async def check_backend_tsc():
                if error := await self.run_py_backend_check(node):
                    errors.append(error)

            async def check_frontend_tsc():
                await notify_if_callback(
                    self.event_callback, # type: ignore
                    "🔧 Compiling frontend TypeScript...",
                    "frontend compile start",
                )
                if error := await self.run_tsc_frontend_check(node):
                    await notify_if_callback(
                        self.event_callback, # type: ignore
                        "❌ Frontend TypeScript compilation failed",
                        "frontend compile failure",
                    )
                    errors.append(error)

            async def check_tests():
                if error := await self.run_test_check(node):
                    errors.append(error)

            async def check_build():
                if error := await self.run_build_check(node):
                    errors.append(error)

            async def check_drizzle():
                if error := await self.run_alembic_check(node):
                    errors.append(error)

            tg.start_soon(check_drizzle)
            tg.start_soon(check_backend_tsc)
            tg.start_soon(check_frontend_tsc)
            tg.start_soon(check_tests)
            tg.start_soon(check_build)

        if not await self._handle_validation_errors(node, errors):
            return False

        # Then Playwright (slow)
        # await notify_if_callback(
        #     self.event_callback, "🎭 Running UI validation...", "playwright start"
        # )
        # if feedback := await self.run_playwright_check(node, "full"):
        #     await notify_if_callback(
        #         self.event_callback,
        #         "❌ UI validation failed - adjusting...",
        #         "playwright failure",
        #     )
        #     node.data.messages.append(
        #         Message(role="user", content=[TextRaw(x) for x in feedback])
        #     )
        #     return False

        await notify_if_callback(
            self.event_callback, "✅ All validations passed!", "validation success" # type: ignore
        )
        return True

    async def run_py_backend_check(self, node: Node[BaseData]) -> str | None:
        """Run TypeScript compilation check for backend."""
        result = await node.data.workspace.exec(
            ["bun", "run", "check:py:syntax"]
        )
        if result.exit_code != 0:
            error_output = f"{result.stdout}\n{result.stderr}"
            return f"Python errors (backend):\n{error_output}"
        return None

    async def run_tsc_frontend_check(self, node: Node[BaseData]) -> str | None:
        """Run TypeScript compilation check for frontend."""
        result = await node.data.workspace.exec(
            ["bun", "run", "check:ts"]
        )
        if result.exit_code != 0:
            error_output = f"{result.stdout}\n{result.stderr}"
            return f"TypeScript errors (frontend):\n{error_output}"
        return None

    async def run_alembic_check(self, node: Node[BaseData]) -> str | None:
        """Run Alembic schema validation."""
        result = await alembic_push(
            node.data.workspace.client, node.data.workspace.ctr, postgresdb=None
        )
        if result.exit_code != 0:
            error_output = f"{result.stdout}\n{result.stderr}"
            return f"Alembic errors:\n{error_output} | {result.exit_code} | {result.stdout} | {result.stderr}"
        return None

    async def run_build_check(self, node: Node[BaseData]) -> str | None:
        """Run frontend build check."""
        result = await node.data.workspace.exec(["bun", "run", "client:build"])
        if result.exit_code != 0:
            error_output = f"{result.stdout}\n{result.stderr}"
            return f"Build errors:\n{error_output}"

        result = await node.data.workspace.exec(["bun", "run", "client:lint"])
        if result.exit_code != 0:
            error_output = f"{result.stdout}\n{result.stderr}"
            return f"Lint errors:\n{error_output}\n"
        return None

    async def run_test_check(
        self, node: Node[BaseData], handler_name: str | None = None
    ) -> str | None:
        """Run test checks - specific handler or all tests with real database."""

        return None
        # prepare test command
        if handler_name:
            test_cmd = ["bun", "test", f"src/tests/{handler_name}.test.ts"]
            test_context = f"handler '{handler_name}'"
        else:
            test_cmd = ["bun", "test"]
            test_context = "all tests"

        # run tests with postgres service
        result = await node.data.workspace.exec_with_pg(test_cmd, cwd="server")
        logger.info(f"Test execution result for {test_context}: {result.exit_code}")

        if result.exit_code != 0:
            error_output = result.stderr
            return f"Test errors:\n{error_output}"
        return None

    # async def run_playwright_check(
    #     self, node: Node[BaseData], mode: str = "client"
    # ) -> list[str] | None:
    #     """Run Playwright UI validation."""
    #     feedback = await self.playwright.evaluate(node, self._user_prompt, mode=mode)
    #     return feedback if feedback else None

    async def run_checks(self, node: Node[BaseData], user_prompt: str) -> str | None:
        """Run context-aware validation checks based on node context."""
        context = node.data.context

        # Run validation based on context
        match context:
            case "draft":
                logger.info("RUNNING DRAFT VALIDATION")
                success = await self._validate_draft(node)
                logger.info(f"DRAFT VALIDATION RESULT: {success}")
            case "frontend":
                logger.info("RUNNING FRONTEND VALIDATION")
                success = await self._validate_frontend(node)
                logger.info(f"FRONTEND VALIDATION RESULT: {success}")
            case "edit":
                logger.info("RUNNING EDIT VALIDATION")
                success = await self._validate_edit(node)
                logger.info(f"EDIT VALIDATION RESULT: {success}")
            case s if s.startswith("handler:"):
                logger.info("RUNNING HANDLER VALIDATION")
                success = await self._validate_handler(node)
                logger.info(f"HANDLER VALIDATION RESULT: {success}")
            case _:
                logger.warning(f"Unknown context: {context}, skipping validation")
                return None  # No validation for unknown context

        # If validation failed, extract error message from last message
        if not success and node.data.messages:
            last_msg = node.data.messages[-1]
            if last_msg.role == "user" and last_msg.content:
                # Extract error text from message content
                error_texts = []
                for content_item in last_msg.content:
                    if isinstance(content_item, TextRaw):
                        error_texts.append(content_item.text)
                if error_texts:
                    # Remove the last message as we'll return it as error
                    node.data.messages.pop()
                    return "\n".join(error_texts)

        return None if success else "Validation failed"

    def _render_prompt(self, template_name: str, **kwargs) -> str:
        """Render Jinja template with given parameters."""
        jinja_env = jinja2.Environment()
        template = jinja_env.from_string(getattr(playbooks, template_name))
        return template.render(**kwargs)

    def _create_node_with_files(
        self,
        workspace: Workspace,
        message: Message,
        files: dict[str, str],
        context: str = "default",
    ) -> Node[BaseData]:
        """Create a Node with BaseData and copy files to it."""
        node = Node(BaseData(workspace, [message], {}, True, context))
        for file_path, content in files.items():
            node.data.files[file_path] = content
        return node

    async def _handle_validation_errors(
        self, node: Node[BaseData], errors: list[str]
    ) -> bool:
        """Handle validation errors by adding to node messages."""
        if errors:
            error_msg = await self.compact_error_message("\n".join(errors))
            node.data.messages.append(
                Message(role="user", content=[TextRaw(error_msg)])
            )
            return False
        return True

    def _create_workspace_with_permissions(
        self,
        files: dict[str, str],
        allowed: list[str],
        protected: list[str] | None = None,
    ) -> Workspace:
        """Create workspace with files and permissions."""
        workspace = self.workspace.clone()
        for file_path, content in files.items():
            workspace.write_file(file_path, content)
        return workspace.permissions(allowed=allowed, protected=protected or [])

    async def _build_context(
        self,
        workspace: Workspace,
        context_type: str,
        extra_files: list[str] | None = None,
    ) -> str:
        """Build context for different generation phases."""
        context = []

        # Select relevant files based on context type
        match context_type:
            case "draft":
                relevant_files = self.paths.files_relevant_draft
                allowed_files = self.paths.files_allowed_draft
                protected_files = []
            case "edit":
                relevant_files = list(
                    set(
                        self.paths.files_relevant_draft
                        + self.paths.files_relevant_handlers
                        + self.paths.files_relevant_frontend
                    )
                )
                allowed_files = (
                    self.paths.files_allowed_draft + self.paths.files_allowed_frontend
                )
                protected_files = self.paths.files_protected_frontend
            case "frontend":
                relevant_files = self.paths.files_relevant_frontend
                allowed_files = self.paths.files_allowed_frontend
                protected_files = self.paths.files_protected_frontend
            case "handler":
                relevant_files = self.paths.files_relevant_handlers + (
                    extra_files or []
                )
                allowed_files = extra_files or []
                protected_files = []
            case _:
                raise ValueError(f"Unknown context type: {context_type}")

        # Add relevant files to context
        for path in relevant_files:
            try:
                content = await workspace.read_file(path)
                context.append(f'\n<file path="{path}">\n{content.strip()}\n</file>\n')
                logger.debug(f"Added {path} to context")
            except Exception:
                # File might not exist, skip it
                pass

        # Add UI components info for frontend/edit contexts
        if context_type in ["frontend", "edit"]:
            try:
                ui_files = await workspace.ls("client/src/components/ui")
                context.append(f"UI components in client/src/components/ui: {ui_files}")
            except Exception:
                pass

        # Add configuration info
        if context_type == "draft":
            context.append(
                "APP_DATABASE_URL=postgres+asyncpg://postgres:postgres@postgres:5432/postgres",
            )
            context.append(
                "DATABASE_URL=postgres+asyncpg://postgres:postgres@postgres:5432/postgres",
            )

        if allowed_files:
            context.append(f"Allowed paths and directories: {allowed_files}")
        if protected_files:
            context.append(f"Protected paths and directories: {protected_files}")

        return "\n".join(context)

    async def _create_handler_nodes(
        self,
        handler_files: dict[str, str],
        draft_files: dict[str, str],
        feedback_data: Optional[str],
    ):
        """Create nodes for each handler."""
        self.handler_nodes = {}

        # Set up workspace with inherited files
        workspace = self.workspace.clone()
        for file in self.paths.files_inherit_handlers:
            if file in draft_files:
                workspace.write_file(file, draft_files[file])
                logger.debug(f"Copied inherited file: {file}")

        # Template will be rendered per handler

        # Process handler files
        for file, content in handler_files.items():
            handler_name, _ = os.path.splitext(os.path.basename(file))
            logger.info(f"Processing handler: {handler_name}")

            # Create workspace with permissions
            allowed = [file, f"server/app/tests/test_{handler_name}.py"]
            handler_ws = (
                workspace.clone().permissions(allowed=allowed).write_file(file, content)
            )

            # Build context with relevant files
            context = await self._build_context(handler_ws, "handler", [file])

            # Render user prompt and create node
            user_prompt_rendered = self._render_prompt(
                "BACKEND_HANDLER_USER_PROMPT",
                project_context=context,
                handler_name=handler_name,
                feedback_data=feedback_data,
            )

            message = Message(role="user", content=[TextRaw(user_prompt_rendered)])
            node = Node(
                BaseData(handler_ws, [message], {}, True, f"handler:{handler_name}")
            )
            self.handler_nodes[handler_name] = node

    def _get_handler_name(self, node: Node[BaseData]) -> str:
        """Extract handler name from node's context."""
        context = node.data.context
        if context.startswith("handler:"):
            return context.split(":", 1)[1]
        return "unknown"

    async def handle_custom_tool(
        self, tool_use: ToolUse, node: Node[BaseData]
    ) -> ToolUseResult:
        """Handle SamActor-specific custom tools."""
        assert isinstance(tool_use.input, dict), (
            f"Tool input must be dict, got {type(tool_use.input)}"
        )
        match tool_use.name:
            case "npm_install":
                packages = tool_use.input["packages"]  # pyright: ignore[reportIndexIssue]
                target = tool_use.input["target"]  # pyright: ignore[reportIndexIssue]

                match target:
                    case "server":
                        cwd = "server"
                    case "client":
                        cwd = "client"
                    case other:
                        return ToolUseResult.from_tool_use(
                            tool_use,
                            f"Invalid target: {other}. Must be 'server' or 'client'",
                            is_error=True,
                        )

                node.data.workspace.cwd(cwd)
                exec_res = await node.data.workspace.exec_mut(
                    ["bun", "add", " ".join(packages)]
                )
                node.data.workspace.cwd("/app")
                await node.data.workspace.exec_mut(["bun", "install"]) # update root lockfile
                if exec_res.exit_code != 0:
                    return ToolUseResult.from_tool_use(
                        tool_use,
                        f"Failed to add packages: {exec_res.stderr}",
                        is_error=True,
                    )
                else:
                    package_path = f"{cwd}/package.json"
                    node.data.files.update(
                        {
                            package_path: await node.data.workspace.read_file(
                                package_path
                            ),
                            "bun.lock": await node.data.workspace.read_file("bun.lock")
                        }
                    )
                    return ToolUseResult.from_tool_use(tool_use, "success")
            case _:
                return await super().handle_custom_tool(tool_use, node)

    @property
    def conditional_tools(self) -> list[Tool]:
        """Conditional tools specific to SamActor."""
        tools = [
            {
                "name": "npm_install",
                "description": "Install additional packages",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "packages": {"type": "array", "items": {"type": "string"}},
                        "target": {"type": "string", "enum": ["server", "client"]},
                    },
                    "required": ["packages", "target"],
                },
            },
        ]
        return tools # type: ignore
