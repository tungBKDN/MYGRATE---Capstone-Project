from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.agents.base_agent import BaseAgent, ToolDefinition
from src.models.state import GlobalState

VALID_NODES = {"reader", "architect", "translator", "end"}


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent orchestrating the codebase migration pipeline.
    Inherits from BaseAgent to support ReAct loop and tool-based routing decision.
    """

    def __init__(self, model_name: str | None = None):
        super().__init__(model_name)
        self._routing_decision: dict[str, Any] | None = None
        self._messages_from_state: list = []

    def get_prompt_file(self) -> str | None:
        return "supervisor.md"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="route_to",
                description=(
                    "Make the final routing decision to transfer control to another sub-agent "
                    "or terminate the workflow."
                ),
                func=self._tool_route_to,
                parameters={
                    "type": "object",
                    "properties": {
                        "next_node": {
                            "type": "string",
                            "enum": ["reader", "architect", "translator", "end"],
                            "description": "The next node to route control to.",
                        },
                        "current_instruction": {
                            "type": "string",
                            "description": "Instruction payload for the next node.",
                        },
                        "summary_update": {
                            "type": "string",
                            "description": "Short summary of completed tasks to append to state history.",
                        },
                        "response_to_user": {
                            "type": "string",
                            "description": "A response message to show the user (especially if next_node is 'end').",
                        },
                    },
                    "required": ["next_node"],
                },
            )
        ]

    def _tool_route_to(
        self,
        next_node: str,
        current_instruction: str = "",
        summary_update: str = "",
        response_to_user: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Save the routing decision for the pipeline."""
        self._routing_decision = {
            "next_node": next_node.lower(),
            "current_instruction": current_instruction,
            "summary_update": summary_update,
            "response_to_user": response_to_user,
        }
        return {"status": "success", "message": f"Routing decision set to '{next_node}'."}

    def _run_react_loop(
        self,
        instruction: str,
        payload: dict[str, Any],
        tools: list[ToolDefinition],
        tool_map: dict[str, ToolDefinition],
    ) -> str:
        """Override the ReAct loop to preserve user chat messages in LLM context."""
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

        prompt_file = self.get_prompt_file()
        system_prompt = self._load_prompt_file(prompt_file) if prompt_file else self.get_system_prompt()

        # 1. Initialize messages with the system prompt
        messages: list = [SystemMessage(content=system_prompt)]

        # 2. Append historical chat history from state (messages)
        if hasattr(self, "_messages_from_state") and self._messages_from_state:
            messages.extend(self._messages_from_state[-10:])

        # 3. Add context payload as the user instruction
        user_content = (
            f"Global State Context:\n{instruction}\n\n"
            "Available Tools:\n" + self._format_tool_descriptions(tools) + "\n\n"
            "Analyze the current state and chat history. You MUST call the 'route_to' tool "
            "to set the next node. Once you have called 'route_to' successfully, wrap up "
            "your answer by returning a JSON confirmation matching the required output format."
        )
        messages.append(HumanMessage(content=user_content))

        # Bind tools
        llm_with_tools = self.llm.bind_tools([t.to_openai_tool() for t in tools])

        for iteration in range(self.MAX_ITERATIONS):
            print(f"-> [SUPERVISOR] ReAct iteration {iteration + 1}/{self.MAX_ITERATIONS}")
            try:
                response = llm_with_tools.invoke(messages)
            except Exception as e:
                print(f"-> [SUPERVISOR] LLM error: {e}")
                break

            tool_calls = getattr(response, "tool_calls", None) or []
            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = getattr(tool_call, "name", None) or (
                        tool_call.get("name", "") if isinstance(tool_call, dict) else ""
                    )
                    tool_args = getattr(tool_call, "args", None) or (
                        tool_call.get("args", {}) if isinstance(tool_call, dict) else {}
                    )
                    if isinstance(tool_args, str):
                           try:
                               tool_args = json.loads(tool_args)
                           except json.JSONDecodeError:
                               tool_args = {}

                    print(f"-> [SUPERVISOR] Calling tool: {tool_name}({json.dumps(tool_args, default=str)[:200]})")
                    observation = self._execute_tool(tool_name, tool_args, tool_map, payload)

                    tool_call_id = getattr(tool_call, "id", None) or (
                        tool_call.get("id", "") if isinstance(tool_call, dict) else ""
                    )
                    messages.append(response)
                    messages.append(ToolMessage(
                        content=json.dumps(observation, ensure_ascii=False, default=str)[:4000],
                        tool_call_id=tool_call_id or tool_name,
                    ))

                # Check if routing decision is set; if so, we can terminate early
                if self._routing_decision is not None:
                    return json.dumps(self._routing_decision, ensure_ascii=False, indent=2)
            else:
                # No tool calls — final answer
                content = getattr(response, "content", "") or ""
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        if "final_answer" in parsed:
                            final = parsed["final_answer"]
                            if isinstance(final, dict):
                                return json.dumps(final, ensure_ascii=False, indent=2, default=str)
                        return json.dumps(parsed, ensure_ascii=False, indent=2, default=str)
                except json.JSONDecodeError:
                    pass
                return json.dumps({"response_to_user": content, "next_node": "end"}, ensure_ascii=False, indent=2)

        if self._routing_decision is not None:
            return json.dumps(self._routing_decision, ensure_ascii=False, indent=2)

        return json.dumps({"next_node": "end", "response_to_user": "Supervisor reached max iterations without routing."}, ensure_ascii=False)

    def process(self, state: GlobalState) -> dict:
        """
        Process the current state and return the routing dictionary update.
        """
        self._routing_decision = None
        self._messages_from_state = state.get("messages", [])

        # Build state context summary
        dependencies = state.get("dependencies", [])
        deps_preview = ""
        if dependencies:
            deps_preview = ", ".join(
                f"{d.get('artifactId', '?')}:{d.get('version', '?')}"
                for d in dependencies[:10]
            )

        state_context = {
            "project_path": state.get("project_path", "unknown"),
            "project_type": state.get("project_type", "unknown"),
            "target_java_version": state.get("target_java_version", "17"),
            "dependencies_count": len(dependencies),
            "dependencies_preview": deps_preview or "not yet scanned",
            "last_subagent_result": str(state.get("last_subagent_result", ""))[:500],
            "completed_tasks": state.get("completed_tasks_summary", []),
            "has_solutions": (
                state.get("candidate_solutions") is not None 
                or state.get("upgrade_report") is not None
                or "solutions" in str(state.get("last_subagent_result", ""))
            ),
            "has_reader_review": (
                state.get("reader_review") is not None
                or "markdown_report" in str(state.get("last_subagent_result", ""))
            ),
            "has_translation": state.get("jdeprscan_report") is not None or "change_candidates" in str(state.get("last_subagent_result", "")),
        }

        # Run agent
        result_str = self.run(json.dumps(state_context, ensure_ascii=False, indent=2))

        try:
            data = json.loads(result_str)
        except Exception:
            data = {}

        next_node = data.get("next_node", "end").lower()
        instruction = data.get("current_instruction", "")
        summary = data.get("summary_update", "")
        response_text = data.get("response_to_user", "")

        # Validate routing node
        if next_node not in VALID_NODES:
            print(f"-> [SUPERVISOR] Invalid node '{next_node}'. Falling back to end.")
            next_node = "end"

        update = {"next_node": next_node, "current_instruction": instruction}
        if summary:
            update["completed_tasks_summary"] = [summary]
        if response_text:
            update["messages"] = [AIMessage(content=response_text)]

        print(f"-> [SUPERVISOR] Routing to: {next_node}")
        return update

    def _run_deterministic(
        self,
        instruction: str,
        payload: dict[str, Any],
        tools: list[ToolDefinition],
    ) -> str:
        """Deterministic fallback when LLM is unavailable."""
        print(f"-> [SUPERVISOR] No LLM available, executing deterministic routing...")
        
        project_type = payload.get("project_type", "unknown")
        deps_count = payload.get("dependencies_count", 0)
        has_solutions = payload.get("has_solutions", False)
        has_reader_review = payload.get("has_reader_review", False)
        has_translation = payload.get("has_translation", False)

        # Simple sequential fallback
        if project_type == "unknown" or deps_count == 0:
            next_node = "reader"
            current_instruction = "Index codebase and extract dependencies."
            response_to_user = "Scanning project dependencies..."
        elif not has_solutions:
            next_node = "architect"
            current_instruction = "Solve version compatibility constraints."
            response_to_user = "Analyzing library version solutions..."
        elif not has_reader_review:
            next_node = "reader"
            current_instruction = "Select the best candidate solutions and output final review."
            response_to_user = "Performing final compatibility candidate review..."
        elif not has_translation:
            next_node = "translator"
            current_instruction = "Translate migration scope."
            response_to_user = "Proceeding with migration and code changes..."
        else:
            next_node = "end"
            current_instruction = ""
            response_to_user = "Migration and translation plan has been generated successfully. Let me know if you need anything else!"

        return json.dumps({
            "next_node": next_node,
            "current_instruction": current_instruction,
            "response_to_user": response_to_user
        }, ensure_ascii=False)


def get_supervisor_node(state: GlobalState):
    supervisor = SupervisorAgent()
    return supervisor.process(state)