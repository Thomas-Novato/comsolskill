"""
test_script_generator.py — 验证 MATLAB 脚本生成正确性
无需 COMSOL / MATLAB 即可运行。
"""
import os, json, re, pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
from core.script_generator import generate_script, _build_flow_replacements

FLOW = {
    "physics": "flow",
    "geometry": {"type": "pipe", "length": 0.10, "radius": 0.005},
    "material": {"fluid": "water", "density": 1000.0, "viscosity": 0.001},
    "boundary": {"inlet_velocity": 0.01, "outlet_condition": "pressure_zero"},
    "mesh": "normal", "solver": "stationary",
}
ACOUSTIC = {
    "physics": "acoustic",
    "geometry": {"type": "room", "length": 4.0, "width": 3.0},
    "source": {"type": "monopole", "x": 1.0, "y": 1.0, "frequency": 500.0, "power": 1e-3},
    "boundary": {"walls": "sound_hard"},
    "mesh": "normal", "solver": "frequency_domain",
}


def _content(params, tmp_path):
    return Path(generate_script(params, str(tmp_path))).read_text(encoding="utf-8")


def test_flow_script_created(tmp_path):
    assert Path(generate_script(FLOW, str(tmp_path))).exists()

def test_flow_geometry_values(tmp_path):
    c = _content(FLOW, tmp_path)
    assert "0.005" in c and "0.1" in c

def test_flow_physics_keywords(tmp_path):
    c = _content(FLOW, tmp_path)
    assert "LaminarFlow" in c and "InletBoundary" in c and "0.01" in c

def test_flow_no_unreplaced_placeholders(tmp_path):
    c = _content(FLOW, tmp_path)
    assert re.findall(r"%%[A-Z_]+%%", c) == []

def test_flow_json_saved(tmp_path):
    generate_script(FLOW, str(tmp_path))
    files = list(tmp_path.glob("flow_params_*.json"))
    assert files and json.loads(files[0].read_text())["physics"] == "flow"

def test_acoustic_script_created(tmp_path):
    assert Path(generate_script(ACOUSTIC, str(tmp_path))).exists()

def test_acoustic_physics_keywords(tmp_path):
    c = _content(ACOUSTIC, tmp_path)
    assert "PressureAcoustics" in c and "MonopolePointSource" in c and "500.0" in c

def test_acoustic_no_unreplaced_placeholders(tmp_path):
    assert re.findall(r"%%[A-Z_]+%%", _content(ACOUSTIC, tmp_path)) == []

@pytest.mark.parametrize("mesh,expected", [("fine","3"),("normal","4"),("coarse","5")])
def test_mesh_size_map(tmp_path, mesh, expected):
    assert _build_flow_replacements({**FLOW,"mesh":mesh}, str(tmp_path))["%%MESH_SIZE%%"] == expected

def test_invalid_physics(tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        generate_script({**FLOW, "physics": "thermal"}, str(tmp_path))
