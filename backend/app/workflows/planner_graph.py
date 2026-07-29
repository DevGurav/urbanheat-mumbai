from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.agents.planner_agent import PlannerAgent


# ============================================
# Graph State
# ============================================

class GraphState(TypedDict):

    question: str

    answer: str

    statistics: dict

    tile_url: str

    active_layer: str


planner = PlannerAgent()


# ============================================
# Planner Node
# ============================================

def planner_node(state: GraphState):

    return planner.run(state)


# ============================================
# Build Graph
# ============================================

builder = StateGraph(GraphState)

builder.add_node("planner", planner_node)

builder.set_entry_point("planner")

builder.add_edge("planner", END)

graph = builder.compile()