"""
matlab_runner.py
通过 subprocess 调用 MATLAB 执行 COMSOL LiveLink 仿真脚本，
并（可选）自动启动 COMSOL 服务进程。
"""

import os
import subprocess
import threading
import time
import signal
import yaml
from pathlib import Path

# Load config once at module level
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── COMSOL Server management ──────────────────────────────────────────────────

_comsol_process: subprocess.Popen | None = None


def start_comsol_server(config: dict | None = None) -> subprocess.Popen:
    """
    Start COMSOL server process in the background.
    Only needed if config.comsol.auto_start_server = true.
    """
    global _comsol_process
    cfg = config or _load_config()
    server_exe = cfg["comsol"]["server_exe"]
    port       = cfg["matlab"]["comsol_server_port"]

    if not os.path.exists(server_exe):
        raise FileNotFoundError(
            f"COMSOL server executable not found:\n  {server_exe}\n"
            "Please update 'comsol.server_exe' in config.yaml."
        )

    cmd = [server_exe, "-port", str(port)]
    _comsol_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Give COMSOL server a moment to start
    time.sleep(5)
    print(f"[COMSOL] Server started (PID {_comsol_process.pid}) on port {port}")
    return _comsol_process


def stop_comsol_server() -> None:
    """Terminate the running COMSOL server (if started by this module)."""
    global _comsol_process
    if _comsol_process and _comsol_process.poll() is None:
        _comsol_process.terminate()
        _comsol_process.wait(timeout=10)
        print("[COMSOL] Server stopped.")
    _comsol_process = None


# ── MATLAB execution ──────────────────────────────────────────────────────────

def run_matlab_script(
    script_path: str,
    config: dict | None = None,
    log_callback=None,
) -> dict:
    """
    Execute a MATLAB script via subprocess and return results.

    Args:
        script_path:  Absolute path to the generated .m script.
        config:       Optional pre-loaded config dict (avoids re-reading file).
        log_callback: Optional callable(line: str) for streaming log lines.

    Returns:
        dict with keys:
            success  (bool)
            stdout   (str)
            stderr   (str)
            returncode (int)
            output_dir (str) — extracted from script filename
    """
    cfg     = config or _load_config()
    matlab  = cfg["matlab"]["exe_path"]
    timeout = cfg["matlab"].get("timeout", 600)

    script_path = os.path.abspath(script_path)
    script_name = Path(script_path).stem
    script_dir  = str(Path(script_path).parent)

    # MATLAB command: change to script dir, run script, then exit
    matlab_cmd = (
        f"cd('{script_dir}'); "
        f"try, run('{script_name}'); catch e, "
        f"disp(['ERROR: ' e.message]); end; exit;"
    )

    cmd = [
        matlab,
        "-nosplash",
        "-nodesktop",
        "-batch",
        matlab_cmd,
    ]

    # Auto-start COMSOL server if requested
    if cfg["comsol"].get("auto_start_server", False):
        start_comsol_server(cfg)

    stdout_lines = []
    stderr_lines = []

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        def _stream(pipe, storage, prefix=""):
            for line in pipe:
                storage.append(line)
                if log_callback:
                    log_callback(f"{prefix}{line.rstrip()}")

        t_out = threading.Thread(target=_stream, args=(process.stdout, stdout_lines))
        t_err = threading.Thread(target=_stream, args=(process.stderr, stderr_lines, "[ERR] "))
        t_out.start()
        t_err.start()

        process.wait(timeout=timeout)
        t_out.join()
        t_err.join()

        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        rc     = process.returncode

        success = (rc == 0) and ("ERROR:" not in stdout) and ("ERROR:" not in stderr)

        return {
            "success":    success,
            "stdout":     stdout,
            "stderr":     stderr,
            "returncode": rc,
            "output_dir": script_dir,
        }

    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "success":    False,
            "stdout":     "".join(stdout_lines),
            "stderr":     f"Timeout: MATLAB did not finish within {timeout} seconds.",
            "returncode": -1,
            "output_dir": script_dir,
        }
    except FileNotFoundError:
        return {
            "success":    False,
            "stdout":     "",
            "stderr":     (
                f"MATLAB executable not found: '{matlab}'.\n"
                "Please update 'matlab.exe_path' in config.yaml "
                "or add MATLAB to your system PATH."
            ),
            "returncode": -1,
            "output_dir": script_dir,
        }


def collect_result_files(output_dir: str) -> dict:
    """
    Scan output directory for simulation result files.

    Returns:
        dict with keys: images, csvs, mph_files
    """
    output_dir = Path(output_dir)
    return {
        "images":    sorted(output_dir.glob("*.png")),
        "csvs":      sorted(output_dir.glob("*.csv")),
        "mph_files": sorted(output_dir.glob("*.mph")),
    }
