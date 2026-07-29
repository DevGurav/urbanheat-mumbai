from typing import TypedDict, Optional


class GraphState(TypedDict):
    question: str

    heat_data: Optional[dict]

    vegetation_data: Optional[dict]

    answer: Optional[str]