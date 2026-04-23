"""
llm_parser.py
自然语言 → COMSOL 仿真参数 JSON
使用 Google Gemini API (google-genai SDK) 解析用户输入的仿真描述。
"""

import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# System Prompt: 严格约束 LLM 输出 JSON 格式
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a COMSOL simulation parameter extractor. Given a user's natural language description
(in Chinese or English) of a physics simulation, extract structured parameters and return
ONLY a valid JSON object—no explanation, no markdown.

## For FLOW FIELD simulations (流场仿真), return:
{
  "physics": "flow",
  "geometry": {
    "type": "pipe",
    "length": <float, meters>,
    "radius": <float, meters>
  },
  "material": {
    "fluid": "water",
    "density": 1000,
    "viscosity": 0.001
  },
  "boundary": {
    "inlet_velocity": <float, m/s>,
    "outlet_condition": "pressure_zero"
  },
  "mesh": "normal",
  "solver": "stationary"
}

## For ACOUSTIC FIELD simulations (声场仿真), return:
{
  "physics": "acoustic",
  "geometry": {
    "type": "room",
    "length": <float, meters>,
    "width": <float, meters>
  },
  "source": {
    "type": "monopole",
    "x": <float>,
    "y": <float>,
    "frequency": <float, Hz>,
    "power": 1e-3
  },
  "boundary": {
    "walls": "sound_hard"
  },
  "mesh": "normal",
  "solver": "frequency_domain"
}

## Rules:
- Use SI units throughout.
- Default water: density=1000, viscosity=0.001
- Default air: density=1.225, viscosity=1.81e-5
- Acoustic simulations use air by default.
- If mesh not specified: "normal".
- For pipe: radius = diameter / 2.
- Sound/speaker/acoustic/声学/声场/声压 → "acoustic"
- Flow/fluid/velocity/流场/流速/管道 → "flow"
- Source position defaults to 1/4 of room if not specified.
- Return ONLY the JSON object.
"""


def parse_simulation_description(user_input: str, model_name: str = "gemini-1.5-flash") -> dict:
    """
    Parse natural language simulation description into structured parameter dict.

    Args:
        user_input: Description in Chinese or English.
        model_name: Gemini model name.

    Returns:
        dict: Validated simulation parameters.

    Raises:
        ValueError: If API key missing or response is invalid JSON.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Please set it in your .env file."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model_name,
        contents=f"{SYSTEM_PROMPT}\n\nUser description:\n{user_input}",
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()

    # Strip markdown code block if present
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        params = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON:\n{raw}\nError: {e}")

    _validate_params(params)
    return params


def _validate_params(params: dict) -> None:
    """Basic validation of extracted parameters."""
    physics = params.get("physics")
    if physics not in ("flow", "acoustic"):
        raise ValueError(
            f"Unknown physics type: '{physics}'. Expected 'flow' or 'acoustic'."
        )

    if physics == "flow":
        for key in ("geometry", "material", "boundary", "solver"):
            if key not in params:
                raise ValueError(f"Missing required key '{key}' for flow simulation.")
        if "inlet_velocity" not in params.get("boundary", {}):
            raise ValueError("Missing 'inlet_velocity' in boundary conditions.")

    elif physics == "acoustic":
        for key in ("geometry", "source", "solver"):
            if key not in params:
                raise ValueError(f"Missing required key '{key}' for acoustic simulation.")
        if "frequency" not in params.get("source", {}):
            raise ValueError("Missing 'frequency' in acoustic source.")
