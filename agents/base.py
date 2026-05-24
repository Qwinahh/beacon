"""
Base agent class.

Each agent is a Claude instance with a specific role, a set of callable
tools, and a reasoning loop. The agent decides WHICH tools to call and in
what order — we don't tell it. It runs until it returns a final text
response (stop_reason == "end_turn"), then we parse that as structured JSON.

Usage:
    class MyAgent(ToolAgent):
        SYSTEM = "You are a ..."
        TOOLS  = {"my_tool": (my_tool_fn, my_tool_schema)}

    result = MyAgent().run("Do this task")
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

import anthropic

from bot.config import CLAUDE_MODEL

log = logging.getLogger(__name__)

# Max iterations of the tool-use loop per agent run. Safety net only.
MAX_TOOL_ROUNDS = 8


class ToolAgent:
    """
    A Claude agent that can call Python functions as tools.

    Subclasses define:
        SYSTEM  — system prompt (str)
        TOOLS   — dict mapping tool_name → (callable, anthropic_tool_schema)
        MODEL   — optional model override
    """

    SYSTEM: str = ""
    TOOLS:  dict[str, tuple[Callable, dict]] = {}
    MODEL:  str = CLAUDE_MODEL

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is required for agent use.")
        self._client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _tool_schemas(self) -> list[dict]:
        return [schema for _, (_, schema) in self.TOOLS.items()]

    def _call_tool(self, name: str, inputs: dict) -> Any:
        if name not in self.TOOLS:
            return f"ERROR: unknown tool '{name}'"
        fn, _ = self.TOOLS[name]
        try:
            result = fn(**inputs)
            return result
        except Exception as exc:
            log.error("Tool '%s' raised: %s", name, exc)
            return f"ERROR: {exc}"

    # ------------------------------------------------------------------
    # Reasoning loop
    # ------------------------------------------------------------------

    def run(self, task: str, extra_context: str = "") -> dict:
        """
        Run the agent on a task.

        Returns a dict parsed from the agent's final JSON response.
        Falls back to {"text": raw_response} if the response isn't valid JSON.
        """
        user_content = task
        if extra_context:
            user_content = f"{task}\n\nContext:\n{extra_context}"

        messages: list[dict] = [{"role": "user", "content": user_content}]
        schemas  = self._tool_schemas()

        log.info("[%s] Starting run: %s", self.__class__.__name__, task[:60])

        for round_num in range(MAX_TOOL_ROUNDS):
            kwargs: dict = {
                "model":      self.MODEL,
                "system":     self.SYSTEM,
                "messages":   messages,
                "max_tokens": 1024,
            }
            if schemas:
                kwargs["tools"] = schemas

            response = self._client.messages.create(**kwargs)

            if response.stop_reason == "end_turn":
                # Extract the final text block.
                text = next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    "",
                ).strip()
                log.info("[%s] Final response (%d chars).", self.__class__.__name__, len(text))
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}

            if response.stop_reason == "tool_use":
                # Append assistant's message (may include text + tool_use blocks).
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool call and collect results.
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    log.debug("[%s] Tool call: %s(%s)", self.__class__.__name__, block.name, block.input)
                    result = self._call_tool(block.name, block.input)
                    # Serialise the result so Claude can read it.
                    if not isinstance(result, str):
                        try:
                            result = json.dumps(result, default=str)
                        except Exception:
                            result = str(result)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result,
                    })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason.
            log.warning("[%s] Unexpected stop_reason: %s", self.__class__.__name__, response.stop_reason)
            break

        log.error("[%s] Exceeded MAX_TOOL_ROUNDS without a final response.", self.__class__.__name__)
        return {"error": "max_rounds_exceeded"}
