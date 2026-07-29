from fastapi import APIRouter
from pydantic import BaseModel

from app.workflows.planner_graph import graph

router = APIRouter(
    prefix="/planner",
    tags=["Planner"]
)


class PlannerRequest(BaseModel):
    question: str


@router.post("")
def planner(request: PlannerRequest):

    result = graph.invoke({

        "question": request.question,

        "answer": "",

        "statistics": {},

        "tile_url": "",

        "active_layer": ""

    })

    return {

        "answer": result["answer"],

        "statistics": result["statistics"],

        "tile_url": result["tile_url"],

        "active_layer": result["active_layer"]

    }