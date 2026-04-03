from typing import Any, Dict, List, Optional, TypedDict


class ELSResult(TypedDict, total=False):
    layer: str
    layer_number: str
    layer_name: str
    explanation: str
    next_steps: List[str]
    mapped_context: dict

class LearningResult(TypedDict, total=False):
    kubernetes: str
    ai: str
    platform: str
    product: str


class AgentTraceStep(TypedDict, total=False):
    step: int
    action: str
    why: str
    outcome: str


class CoachResponse(TypedDict, total=False):
    summary: str
    answer: str
    els: ELSResult
    learning: LearningResult
    agent_trace: List[AgentTraceStep]
    warnings: List[str]
    error: str
    raw_text: str
