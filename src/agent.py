import os
import yaml
import json
from openai import OpenAI

from config import OPENAI_MODEL, MAX_CONTEXT_CHARS, OPENAI_TEMPERATURE
from schemas import CoachResponse

client = OpenAI()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# --------------------------
# Load ELS Model
# --------------------------
def load_els_model():
    path = os.path.join(BASE_DIR, "src/schemas", "els_schema.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f)


# --------------------------
# Structured context
# --------------------------
def build_context(question: str, context: str) -> dict:
    return {
        "question": question,
        "context": context[:MAX_CONTEXT_CHARS],
    }


# --------------------------
# Agent Trace
# --------------------------
def build_trace(question: str, context: str):
    return [
        {
            "step": 1,
            "action": "Interpret question",
            "why": "Determine which Kubernetes layer and resource type is relevant",
            "outcome": question,
        },
        {
            "step": 2,
            "action": "Attach cluster context",
            "why": "Provide real cluster evidence instead of hallucination",
            "outcome": f"context size={len(context)} chars",
        },
        {
            "step": 3,
            "action": "Apply ELS model",
            "why": "Map observations to the layered Kubernetes mental model",
            "outcome": "ELS model loaded",
        },
    ]


# --------------------------
# Normalize model output
# --------------------------
def normalize_response(raw: str) -> CoachResponse:
    try:
        parsed = json.loads(raw)
        return parsed
    except Exception:
        return {
            "raw_text": raw,
            "summary": "",
            "answer": raw,
            "els": {
                "layer": "Unknown",
                "explanation": "Model did not return valid JSON.",
                "next_steps": [],
            },
            "learning": {
                "kubernetes": "",
                "ai": "",
                "platform": "",
                "product": "",
            },
            "agent_trace": [],
            "warnings": ["Response was not valid JSON."],
        }


# --------------------------
# Main LLM function
# --------------------------
def ask_llm(question: str, context: str = "") -> CoachResponse:
    try:
        els_model = load_els_model()
        trace = build_trace(question, context)

        payload = {
            "question": question,
            "context": context[:MAX_CONTEXT_CHARS],
            "els_model": els_model,
            "agent_trace": trace,
        }

        system_prompt = """
You are cka-coach, a Kubernetes + AI systems tutor.

You MUST:
- Use the provided ELS model as ground truth
- Use the provided agent trace
- Use ONLY the provided context
- Avoid guessing when evidence is incomplete

You teach through 4 lenses:
1. Kubernetes
2. AI / Agents
3. Platform Engineering
4. Product Thinking

Return STRICT JSON only.
"""

        user_prompt = f"""
DATA:
{json.dumps(payload, indent=2)}

Return JSON with exactly this shape:
{{
  "summary": "short summary",
  "answer": "main explanation",
  "els": {{
    "layer": "primary ELS layer",
    "explanation": "ELS-based reasoning",
    "next_steps": ["step 1", "step 2"]
  }},
  "learning": {{
    "kubernetes": "what this teaches about Kubernetes",
    "ai": "what this teaches about AI agents or LLM systems",
    "platform": "what this teaches about platform engineering",
    "product": "what this teaches about product thinking"
  }},
  "agent_trace": [
    {{
      "step": 1,
      "action": "what the agent did",
      "why": "why it did that",
      "outcome": "what it found"
    }}
  ],
  "warnings": ["warning 1"]
}}
"""

        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.output_text
        parsed = normalize_response(raw)

        if not parsed.get("agent_trace"):
            parsed["agent_trace"] = trace

        return parsed

    except Exception as e:
        return {
            "summary": "",
            "answer": "",
            "els": {
                "layer": "Error",
                "explanation": "",
                "next_steps": [],
            },
            "learning": {
                "kubernetes": "",
                "ai": "",
                "platform": "",
                "product": "",
            },
            "agent_trace": [],
            "warnings": [],
            "error": str(e),
        }
