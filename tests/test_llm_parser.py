"""
test_llm_parser.py — 验证 LLM 解析器
使用 mock 避免真实 API 调用。
"""
import json, pytest
from unittest.mock import patch, MagicMock
from core.llm_parser import parse_simulation_description, _validate_params

# ── Mock helpers ──────────────────────────────────────────────────────────────

def _make_mock_response(payload: dict):
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(payload)
    return mock_resp

FLOW_JSON = {
    "physics": "flow",
    "geometry": {"type": "pipe", "length": 0.10, "radius": 0.005},
    "material": {"fluid": "water", "density": 1000, "viscosity": 0.001},
    "boundary": {"inlet_velocity": 0.01, "outlet_condition": "pressure_zero"},
    "mesh": "normal", "solver": "stationary",
}
ACOUSTIC_JSON = {
    "physics": "acoustic",
    "geometry": {"type": "room", "length": 4.0, "width": 3.0},
    "source": {"type": "monopole", "x": 1.0, "y": 1.0, "frequency": 500.0, "power": 1e-3},
    "boundary": {"walls": "sound_hard"},
    "mesh": "normal", "solver": "frequency_domain",
}

# ── parse_simulation_description ──────────────────────────────────────────────

@patch("core.llm_parser.genai.Client")
@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_parse_flow_description(MockClient):
    MockClient.return_value.models.generate_content.return_value = _make_mock_response(FLOW_JSON)
    result = parse_simulation_description("圆管流场仿真")
    assert result["physics"] == "flow"
    assert result["geometry"]["radius"] == 0.005
    assert result["boundary"]["inlet_velocity"] == 0.01


@patch("core.llm_parser.genai.Client")
@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_parse_acoustic_description(MockClient):
    MockClient.return_value.models.generate_content.return_value = _make_mock_response(ACOUSTIC_JSON)
    result = parse_simulation_description("矩形房间声场")
    assert result["physics"] == "acoustic"
    assert result["source"]["frequency"] == 500.0


@patch.dict("os.environ", {}, clear=True)
def test_missing_api_key_raises():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        parse_simulation_description("any description")


@patch("core.llm_parser.genai.Client")
@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_invalid_json_raises(MockClient):
    bad = MagicMock()
    bad.text = "This is not JSON at all"
    MockClient.return_value.models.generate_content.return_value = bad
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_simulation_description("any")


# ── _validate_params ──────────────────────────────────────────────────────────

def test_validate_flow_ok():
    _validate_params(FLOW_JSON)   # should not raise

def test_validate_acoustic_ok():
    _validate_params(ACOUSTIC_JSON)

def test_validate_unknown_physics():
    with pytest.raises(ValueError, match="Unknown physics"):
        _validate_params({**FLOW_JSON, "physics": "thermal"})

def test_validate_flow_missing_inlet():
    bad = {**FLOW_JSON, "boundary": {"outlet_condition": "pressure_zero"}}
    with pytest.raises(ValueError, match="inlet_velocity"):
        _validate_params(bad)

def test_validate_acoustic_missing_frequency():
    bad = {**ACOUSTIC_JSON, "source": {"type": "monopole"}}
    with pytest.raises(ValueError, match="frequency"):
        _validate_params(bad)
