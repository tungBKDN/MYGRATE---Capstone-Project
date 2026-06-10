from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


class ToolDefinition:
    """Describes a tool that an agent can call during the ReAct loop.

    Attributes:
        name: Unique identifier for the tool (used by LLM to call it).
        description: Human-readable description explaining what the tool does
            and when to use it. This is sent to the LLM.
        func: The actual Python callable to execute when the tool is invoked.
        parameters: JSON Schema dict describing the tool's input parameters.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to OpenAI function-calling tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseAgent(ABC):
    """Base class for all Mygrate agents using the ReAct pattern.

    The ReAct (Reasoning + Acting) loop works as follows:
        1. LLM receives the instruction + conversation history + tool descriptions
        2. LLM decides: call a tool (Action) or return final answer
        3. If Action: execute the tool, append Observation to history, go to step 1
        4. If Final Answer: return the result

    Subclasses must:
        - Define get_tools() to return the list of available tools
        - Define get_system_prompt() to return the agent role description
        - Optionally override get_context() to inject extra context

    The agent gracefully degrades: if no LLM is available, it falls back
    to a deterministic pipeline using the tools in order.
    """

    MAX_ITERATIONS = 8

    def __init__(self, model_name: str | None = None):
        load_dotenv()
        if model_name is None:
            model_name = self._get_default_model()
        self.model_name = model_name
        self.llm = self._init_llm(model_name)

    def _get_default_model(self) -> str:
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def _init_llm(self, model_name: str) -> Any | None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or ChatGroq is None:
            return None
        try:
            return ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)
        except Exception:
            return None

    def _load_prompt_file(self, filename: str) -> str | None:
        """Load a markdown prompt file from src/prompts/ directory.

        Returns None if the file doesn't exist.
        """
        base_dir = Path(__file__).resolve().parent.parent.parent  # project root
        prompt_path = base_dir / "src" / "prompts" / filename
        try:
            return prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    # ── Abstract methods ──

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return the list of tools this agent can use."""
        ...

    def get_system_prompt(self) -> str:
        """Return the system prompt defining this agent's role and behavior.

        Override this OR get_prompt_file() to provide the agent's prompt.
        If get_prompt_file() returns a valid filename, the .md file takes priority.
        """
        return ""

    def get_context(self, instruction: str, payload: dict[str, Any]) -> str:
        """Return additional context to prepend to the conversation.

        Override this in subclasses to inject project-specific context
        (e.g., jdeprscan results, dependency lists, etc.).
        """
        return ""

    def get_prompt_file(self) -> str | None:
        """Return the markdown prompt filename for this agent.

        Override in subclasses to load a .md prompt from src/prompts/.
        Returns None if no prompt file is configured.
        """
        return None

    # ── Instruction parsing (shared across all agents) ──

    def _parse_instruction(self, instruction: str) -> dict[str, Any]:
        """Parse instruction string into a structured payload.

        Tries JSON first, then falls back to key:value extraction.
        """
        try:
            parsed = json.loads(instruction)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        payload: dict[str, Any] = {}
        for label in [
            "Project Path", "project_path",
            "Target Java Version", "target_java_version",
            "current_instruction",
        ]:
            value = self._extract_value(instruction, [label])
            if value:
                payload[label.lower().replace(" ", "_")] = value
        return payload

    def _extract_value(self, instruction: str, labels: list[str]) -> str:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*:\s*(.+)"
            match = re.search(pattern, instruction, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    # ── ReAct Loop ──

    def run(self, instruction: str) -> str:
        """Execute the agent's ReAct loop.

        If LLM is available, the agent will autonomously decide which tools
        to call and in what order. If LLM is unavailable, it falls back to
        a deterministic sequential execution of all tools.
        """
        payload = self._parse_instruction(instruction)
        tools = list(self.get_tools())

        # Add submit_final_answer tool when LLM is active to avoid Groq 400 errors on raw JSON responses
        if self.llm is not None and not any(t.name == "submit_final_answer" for t in tools):
            tools.append(ToolDefinition(
                name="submit_final_answer",
                description=(
                    "Call this tool to submit the final migration plan/results when you have gathered all necessary information. "
                    "You MUST call this tool to return your final answer instead of writing raw JSON text. "
                    "You can pass the final report fields (status, jdeprscan, change_plan, markdown_report, migration_notes) "
                    "either as individual arguments, or wrapped in a single 'final_answer' object."
                ),
                func=lambda **kwargs: kwargs,
                parameters={
                    "type": "object",
                    "properties": {
                        "final_answer": {
                            "type": "object",
                            "description": "The final structured JSON object containing the results.",
                        },
                        "status": {
                            "type": "string",
                            "description": "Status of the migration plan (e.g., 'ok')",
                        },
                        "jdeprscan": {
                            "type": "object",
                            "description": "The jdeprscan pipeline results",
                        },
                        "change_plan": {
                            "type": "object",
                            "description": "The translation report with change candidates",
                        },
                        "markdown_report": {
                            "type": "string",
                            "description": "Human-readable summary of the migration plan",
                        },
                        "migration_notes": {
                            "type": "string",
                            "description": "Prioritized list of actions, with forRemoval=true items first",
                        },
                    },
                }
            ))

        tool_map = {t.name: t for t in tools}

        if self.llm is None:
            # For deterministic fallback, we don't need to run submit_final_answer tool
            deterministic_tools = [t for t in tools if t.name != "submit_final_answer"]
            return self._run_deterministic(instruction, payload, deterministic_tools)

        return self._run_react_loop(instruction, payload, tools, tool_map)

    def _run_react_loop(
        self,
        instruction: str,
        payload: dict[str, Any],
        tools: list[ToolDefinition],
        tool_map: dict[str, ToolDefinition],
    ) -> str:
        """Run the full ReAct loop: Thought -> Action -> Observation -> ... -> Final Answer."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # Build system prompt: prefer .md file, fall back to get_system_prompt()
        prompt_file = self.get_prompt_file()
        if prompt_file:
            file_content = self._load_prompt_file(prompt_file)
            if file_content:
                system_prompt = file_content
            else:
                system_prompt = self.get_system_prompt()
        else:
            system_prompt = self.get_system_prompt()

        extra_context = self.get_context(instruction, payload)
        tool_descriptions = self._format_tool_descriptions(tools)

        # Initial messages
        messages: list = [SystemMessage(content=system_prompt)]

        if extra_context:
            messages.append(SystemMessage(content=f"Additional Context:\n{extra_context}"))

        # Check if instruction is a JSON string to avoid duplicate dumps
        is_json = False
        try:
            json.loads(instruction)
            is_json = True
        except Exception:
            pass

        if is_json:
            user_content = f"Instruction Payload:\n{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}"
        else:
            user_content = f"Instruction:\n{instruction}"
            if payload:
                user_content += f"\n\nParsed payload:\n{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}"
        user_content += f"\n\nAvailable Tools:\n{tool_descriptions}"
        user_content += (
            "\n\nYou must decide which tools to call and in what order. "
            "To call a tool, use the provided function definitions.\n"
            "When you have gathered all necessary information and are ready to return the final results, "
            "you MUST call the 'submit_final_answer' tool with the final structured JSON as arguments. "
            "Do NOT output raw JSON in your chat response, as it will cause a system error."
        )

        messages.append(HumanMessage(content=user_content))

        # Bind tools to LLM for native function calling
        llm_with_tools = self.llm.bind_tools([t.to_openai_tool() for t in tools])
        
        # Track tool results to merge into final answers
        react_tool_results: dict[str, Any] = {}

        for iteration in range(self.MAX_ITERATIONS):
            print(f"-> [{self._agent_name()}] ReAct iteration {iteration + 1}/{self.MAX_ITERATIONS}")

            try:
                response = llm_with_tools.invoke(messages)
            except Exception as e:
                error_str = str(e)
                print(f"-> [{self._agent_name()}] LLM error: {e}")

                # Try to recover from schema validation errors (e.g. boolean params sent as strings)
                recovered = self._try_recover_tool_calls(e, tool_map, payload, react_tool_results, messages)
                if recovered is not None:
                    continue
                break

            # Check if LLM wants to call tools
            tool_calls = getattr(response, "tool_calls", None) or []

            if tool_calls:
                # Process each tool call
                for tool_call in tool_calls:
                    # LangChain tool_call objects have .name and .args attributes
                    tool_name = getattr(tool_call, "name", None) or (
                        tool_call.get("name", "") if isinstance(tool_call, dict) else ""
                    )
                    tool_args = getattr(tool_call, "args", None) or (
                        tool_call.get("args", {}) if isinstance(tool_call, dict) else {}
                    )

                    # Handle string JSON arguments
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}

                    # Coerce argument types to match the tool schema
                    # (guards against LLMs that send "true"/"false" as strings)
                    tool_def = tool_map.get(tool_name)
                    if tool_def:
                        schema_props = tool_def.parameters.get("properties", {})
                        tool_args = self._coerce_tool_args(tool_args, schema_props)

                    print(f"-> [{self._agent_name()}] Calling tool: {tool_name}({json.dumps(tool_args, default=str)[:200]})")

                    # Execute the tool
                    observation = self._execute_tool(tool_name, tool_args, tool_map, payload)

                    if tool_name == "submit_final_answer":
                        print(f"-> [{self._agent_name()}] Final answer submitted via tool.")
                        final_ans = tool_args.get("final_answer", tool_args)
                        if isinstance(final_ans, dict):
                            merged_ans = dict(tool_args)
                            if "final_answer" in merged_ans:
                                inner = merged_ans.pop("final_answer")
                                if isinstance(inner, dict):
                                    merged_ans.update(inner)
                            
                            combined = dict(react_tool_results)
                            combined.update(merged_ans)
                            return self._post_process(combined, instruction, payload)
                        
                        combined = dict(react_tool_results)
                        combined["result"] = final_ans
                        return self._post_process(combined, instruction, payload)

                    # Record the tool observation
                    react_tool_results[tool_name] = observation

                    # Append tool result to conversation using proper LangChain message types
                    from langchain_core.messages import ToolMessage
                    tool_call_id = getattr(tool_call, "id", None) or (
                        tool_call.get("id", "") if isinstance(tool_call, dict) else ""
                    )
                    messages.append(response)
                    messages.append(ToolMessage(
                        content=json.dumps(observation, ensure_ascii=False, default=str),
                        tool_call_id=tool_call_id or tool_name,
                    ))

            else:
                # No tool calls — this is the final answer
                content = getattr(response, "content", "") or ""

                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        if "final_answer" in parsed:
                            final = parsed["final_answer"]
                            if isinstance(final, dict):
                                combined = dict(react_tool_results)
                                combined.update(final)
                                return self._post_process(combined, instruction, payload)
                            combined = dict(react_tool_results)
                            combined["result"] = final
                            return self._post_process(combined, instruction, payload)
                        combined = dict(react_tool_results)
                        combined.update(parsed)
                        return self._post_process(combined, instruction, payload)
                except json.JSONDecodeError:
                    pass

                # If not JSON, return as-is wrapped in a result
                combined = dict(react_tool_results)
                combined["result"] = content
                return self._post_process(combined, instruction, payload)

        # If we exhausted iterations, ask for a final summary
        print(f"-> [{self._agent_name()}] Max iterations reached, requesting final summary...")
        messages.append(HumanMessage(
            content="You have reached the maximum number of iterations. Please provide your final answer now as a JSON object."
        ))
        try:
            final_response = self.llm.invoke(messages)
            content = getattr(final_response, "content", "") or ""
            try:
                parsed = json.loads(content)
                combined = dict(react_tool_results)
                if isinstance(parsed, dict):
                    combined.update(parsed)
                else:
                    combined["result"] = parsed
                return self._post_process(combined, instruction, payload)
            except json.JSONDecodeError:
                combined = dict(react_tool_results)
                combined["result"] = content
                return self._post_process(combined, instruction, payload)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to get final answer: {e}"}, ensure_ascii=False, indent=2)

    def _run_deterministic(
        self,
        instruction: str,
        payload: dict[str, Any],
        tools: list[ToolDefinition],
    ) -> str:
        """Fallback: run all tools sequentially when no LLM is available.

        Each tool receives the full payload as context, so tools can access
        project_path, target java version, etc. even without LLM orchestration.
        """
        print(f"-> [{self._agent_name()}] No LLM available, running tools deterministically...")

        results: dict[str, Any] = {
            "status": "ok",
            "agent": self._agent_name(),
            "instruction": instruction[:500],
        }

        # Pass payload to each tool so they have full context
        for tool in tools:
            print(f"-> [{self._agent_name()}] Running tool: {tool.name}")
            try:
                result = self._execute_tool(tool.name, {}, {tool.name: tool}, payload)
                results[tool.name] = result
            except Exception as e:
                results[f"{tool.name}_error"] = str(e)

        # Let the agent post-process deterministic results
        return self._post_process(results, instruction, payload)

    def _post_process(self, results: dict[str, Any], instruction: str, payload: dict[str, Any]) -> str:
        """Post-process deterministic tool results before returning.

        Override in subclasses to merge/combine results from multiple tools
        into a coherent final output (e.g., attaching jdeprscan data to
        the change plan).
        """
        return json.dumps(results, ensure_ascii=False, indent=2, default=str)

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_map: dict[str, ToolDefinition],
        payload: dict[str, Any],
    ) -> Any:
        """Execute a tool by name with the given arguments.

        Merges payload context into tool arguments for convenience.
        """
        tool = tool_map.get(tool_name)
        if tool is None:
            return {"error": f"Unknown tool: {tool_name}"}

        # Merge payload context into args (payload values serve as defaults)
        merged_args = {**payload, **tool_args}

        try:
            result = tool.func(**merged_args)
            if not isinstance(result, dict):
                result = {"result": result}
            return result
        except Exception as e:
            print(f"-> [{self._agent_name()}] Tool '{tool_name}' error: {e}")
            return {"error": str(e), "tool": tool_name}

    def _format_tool_descriptions(self, tools: list[ToolDefinition]) -> str:
        """Format tool descriptions for the LLM prompt."""
        lines = []
        for t in tools:
            params = t.parameters.get("properties", {})
            param_str = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in params.items())
            lines.append(f"- {t.name}({param_str}): {t.description}")
        return "\n".join(lines)

    def _try_recover_tool_calls(
        self,
        error: Exception,
        tool_map: dict[str, ToolDefinition],
        payload: dict[str, Any],
        react_tool_results: dict[str, Any],
        messages: list,
    ) -> bool | None:
        """Try to recover from LLM tool-call schema validation errors.

        Groq sometimes returns string values ("true"/"false") for boolean
        parameters.  When that happens the API rejects the call with a 400
        error but includes the *attempted* generation in
        ``failed_generation``.  We parse that, coerce the argument types to
        match the declared schema, execute the tools, and inject the
        observations back into the conversation so the ReAct loop can
        continue.

        Returns ``True`` if recovery succeeded (caller should ``continue``),
        ``None`` if the error is not recoverable.
        """
        from langchain_core.messages import HumanMessage

        error_str = str(error)

        # Only handle tool-use validation errors
        if "tool call validation failed" not in error_str and "tool_use_failed" not in error_str:
            return None

        # Extract failed_generation from the error
        failed_gen = None
        try:
            # The error body often contains failed_generation as a Python repr string
            # Pattern: 'failed_generation': '...content...'
            import re as _re
            # Match single-quoted failed_generation (Groq format)
            match = _re.search(r"'failed_generation':\s*'(.*?)'(?:\s*})", error_str, _re.DOTALL)
            if not match:
                # Try to find everything after failed_generation until the closing brace
                match = _re.search(r"failed_generation.*?':\s*'(.*?)'", error_str, _re.DOTALL)
            if match:
                raw = match.group(1)
                # Unescape common escape sequences
                raw = raw.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
                failed_gen = raw
        except Exception:
            pass

        if not failed_gen:
            return None

        # Parse the tool calls from failed_generation
        tool_calls_raw = None
        try:
            # The failed_generation may contain text before/after the JSON array
            # Find the JSON array boundaries
            bracket_start = failed_gen.find("[")
            bracket_end = failed_gen.rfind("]")
            if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
                json_text = failed_gen[bracket_start:bracket_end + 1]
                parsed = json.loads(json_text)
                if isinstance(parsed, list):
                    tool_calls_raw = parsed
        except json.JSONDecodeError:
            pass

        if not tool_calls_raw:
            return None

        # Process each recovered tool call
        any_executed = False
        for tc in tool_calls_raw:
            tool_name = tc.get("name", "")
            tool_args = tc.get("parameters", tc.get("args", {}))

            if tool_name not in tool_map or tool_name == "submit_final_answer":
                # Skip submit_final_answer — let the LLM call it again properly
                continue

            # Coerce argument types to match the schema
            tool = tool_map[tool_name]
            schema_props = tool.parameters.get("properties", {})
            tool_args = self._coerce_tool_args(tool_args, schema_props)

            print(f"-> [{self._agent_name()}] Recovered tool call: {tool_name}({json.dumps(tool_args, default=str)[:200]})")

            # Execute the tool
            observation = self._execute_tool(tool_name, tool_args, tool_map, payload)

            react_tool_results[tool_name] = observation

            # Inject observation into the conversation as a HumanMessage
            # so the LLM sees the result and can continue reasoning
            obs_str = json.dumps(observation, ensure_ascii=False, default=str)
            messages.append(HumanMessage(
                content=(
                    f"[System: The tool '{tool_name}' was called with corrected argument types. "
                    f"Result follows.]\n"
                    f"Tool: {tool_name}\nObservation: {obs_str[:3000]}"
                )
            ))

            any_executed = True

        return True if any_executed else None

    def _coerce_tool_args(self, args: dict[str, Any], schema_props: dict[str, Any]) -> dict[str, Any]:
        """Coerce tool arguments to match the declared JSON schema types.

        Handles the common case where an LLM sends string values for boolean
        or integer parameters.
        """
        coerced = dict(args)
        for key, value in list(coerced.items()):
            prop_schema = schema_props.get(key, {})
            expected_type = prop_schema.get("type", "")

            if expected_type == "boolean" and isinstance(value, str):
                lower = value.lower().strip()
                if lower in ("true", "yes", "1"):
                    coerced[key] = True
                elif lower in ("false", "no", "0"):
                    coerced[key] = False
            elif expected_type == "integer" and isinstance(value, str):
                try:
                    coerced[key] = int(value)
                except ValueError:
                    pass
            elif expected_type == "number" and isinstance(value, str):
                try:
                    coerced[key] = float(value)
                except ValueError:
                    pass

        return coerced

    def _agent_name(self) -> str:
        """Return the agent's name for logging."""
        return self.__class__.__name__.replace("Agent", "").upper()