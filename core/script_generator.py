"""
script_generator.py
将结构化仿真参数 JSON → MATLAB LiveLink 脚本
使用 %%PLACEHOLDER%% 替换模板中的参数。
"""

import os
import json
import yaml
from pathlib import Path
from datetime import datetime

# Template directory (relative to this file's parent)
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_CONFIG_PATH  = Path(__file__).parent.parent / "config.yaml"

# Mesh size map: COMSOL 1=extremely fine ↔ 9=extremely coarse
MESH_SIZE_MAP = {
    "extremely_fine": 1,
    "extra_fine":     2,
    "fine":           3,
    "normal":         4,
    "coarse":         5,
    "extra_coarse":   6,
    "extremely_coarse": 7,
}


def generate_script(params: dict, output_dir: str) -> str:
    """
    Generate a MATLAB LiveLink script from simulation parameters.

    Args:
        params: Structured simulation parameters (from llm_parser).
        output_dir: Absolute path to the output directory.

    Returns:
        str: Absolute path to the generated .m script file.
    """
    physics = params["physics"]

    if physics == "flow":
        template_path = TEMPLATE_DIR / "flow_template.m"
        replacements = _build_flow_replacements(params, output_dir)
    elif physics == "acoustic":
        template_path = TEMPLATE_DIR / "acoustic_template.m"
        replacements = _build_acoustic_replacements(params, output_dir)
    else:
        raise ValueError(f"Unsupported physics type: {physics}")

    template = template_path.read_text(encoding="utf-8")
    script = _apply_replacements(template, replacements)

    # Save generated script
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_path = os.path.join(output_dir, f"{physics}_sim_{timestamp}.m")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    # Also save params as JSON alongside the script
    params_path = os.path.join(output_dir, f"{physics}_params_{timestamp}.json")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, ensure_ascii=False)

    return script_path


def _load_comsol_replacements() -> dict:
    """Load COMSOL server connection info from config.yaml."""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return {
        "%%COMSOL_MLI_PATH%%": cfg["matlab"]["comsol_mli_path"].replace("\\", "/"),
        "%%COMSOL_PORT%%":     str(cfg["matlab"]["comsol_server_port"]),
    }


def _build_flow_replacements(params: dict, output_dir: str) -> dict:
    """Build replacement dict for flow template."""
    geo = params["geometry"]
    mat = params["material"]
    bc  = params["boundary"]
    mesh_str = params.get("mesh", "normal")
    mesh_size = MESH_SIZE_MAP.get(mesh_str, 4)

    output_dir_m = output_dir.replace("\\", "/")

    return {
        **_load_comsol_replacements(),
        "%%LENGTH%%":         str(float(geo["length"])),
        "%%RADIUS%%":         str(float(geo["radius"])),
        "%%DENSITY%%":        str(float(mat["density"])),
        "%%VISCOSITY%%":      str(float(mat["viscosity"])),
        "%%INLET_VELOCITY%%": str(float(bc["inlet_velocity"])),
        "%%MESH_SIZE%%":      str(mesh_size),
        "%%OUTPUT_DIR%%":     output_dir_m,
    }


def _build_acoustic_replacements(params: dict, output_dir: str) -> dict:
    """Build replacement dict for acoustic template."""
    geo  = params["geometry"]
    src  = params["source"]
    mesh_str = params.get("mesh", "normal")
    mesh_size = MESH_SIZE_MAP.get(mesh_str, 4)

    src_x = src.get("x", float(geo["length"]) / 3.0)
    src_y = src.get("y", float(geo["width"])  / 3.0)
    output_dir_m = output_dir.replace("\\", "/")

    return {
        **_load_comsol_replacements(),
        "%%ROOM_LENGTH%%":  str(float(geo["length"])),
        "%%ROOM_WIDTH%%":   str(float(geo["width"])),
        "%%SRC_X%%":        str(float(src_x)),
        "%%SRC_Y%%":        str(float(src_y)),
        "%%FREQUENCY%%":    str(float(src["frequency"])),
        "%%SOURCE_POWER%%": str(float(src.get("power", 1e-3))),
        "%%MESH_SIZE%%":    str(mesh_size),
        "%%OUTPUT_DIR%%":   output_dir_m,
    }


def _apply_replacements(template: str, replacements: dict) -> str:
    """Replace all %%KEY%% placeholders in the template."""
    for key, value in replacements.items():
        template = template.replace(key, value)

    # Warn if any placeholders remain
    import re
    remaining = re.findall(r"%%[A-Z_]+%%", template)
    if remaining:
        import warnings
        warnings.warn(f"Unreplaced placeholders in template: {remaining}")

    return template
