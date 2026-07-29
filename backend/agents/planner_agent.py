from langchain_core.messages import SystemMessage, HumanMessage

from app.llm.groq_client import llm
from app.prompts.planner_prompt import SYSTEM_PROMPT

from app.tools.gee_tools import (
    heat_tool,
    vegetation_tool,
)


class PlannerAgent:

    def run(self, state):

        question = state["question"].lower()

        # ---------------------------------------
        # Default values
        # ---------------------------------------

        tool_result = None

        # ---------------------------------------
        # Decide which tool to execute
        # ---------------------------------------

        if any(word in question for word in [
            "heat",
            "temperature",
            "hot",
            "lst"
        ]):

            tool_result = heat_tool()

        elif any(word in question for word in [
            "vegetation",
            "green",
            "ndvi",
            "trees"
        ]):

            tool_result = vegetation_tool()

        else:

            tool_result = heat_tool()

        # ---------------------------------------
        # Extract data
        # ---------------------------------------

        statistics = tool_result["statistics"]

        tile_url = tool_result["tile_url"]

        active_layer = tool_result["active_layer"]

        # ---------------------------------------
        # Ask Groq to explain
        # ---------------------------------------

        messages = [

            SystemMessage(
                content=SYSTEM_PROMPT
            ),

            HumanMessage(
                content=f"""
User Question:

{question}

Analysis Results:

{statistics}

Explain these results in simple language.
Suggest possible mitigation strategies.
"""
            )

        ]

        response = llm.invoke(messages)

        # ---------------------------------------
        # Update graph state
        # ---------------------------------------

        state["answer"] = response.content

        state["statistics"] = statistics

        state["tile_url"] = tile_url

        state["active_layer"] = active_layer

        return state