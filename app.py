"""
app.py  —  COMSOL AI Simulation System
自然语言驱动的 COMSOL 6.3 流场 / 声场仿真平台
运行方式：  streamlit run app.py
"""

import json
import os
import time
from pathlib import Path

import streamlit as st
import yaml

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="COMSOL AI Sim",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #0b0e1a !important;
    color: #e0e6f8 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #111628 !important;
    border-right: 1px solid rgba(100,120,255,0.15) !important;
}

/* Cards */
.sim-card {
    background: linear-gradient(135deg, #161d35 0%, #1a2240 100%);
    border: 1px solid rgba(100,140,255,0.18);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}

/* Section header */
.section-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #6a82fb;
    margin-bottom: 10px;
}

/* Prompt area */
textarea {
    background: #0d1225 !important;
    border: 1px solid rgba(100,140,255,0.25) !important;
    border-radius: 10px !important;
    color: #e0e6f8 !important;
    font-size: 15px !important;
}

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f6ef7, #7b4fff) !important;
    border: none !important;
    color: #fff !important;
    padding: 0.55rem 1.8rem !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(100,100,255,0.45) !important;
}

/* JSON editor */
.stTextArea textarea { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }

/* Log box */
.log-box {
    background: #070b18;
    border: 1px solid rgba(100,140,255,0.15);
    border-radius: 10px;
    padding: 14px 18px;
    font-family: monospace;
    font-size: 12.5px;
    color: #8af0a0;
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
}

/* Result image */
img { border-radius: 12px !important; }

/* Info chip */
.chip {
    display: inline-block;
    background: rgba(79,110,247,0.18);
    border: 1px solid rgba(79,110,247,0.35);
    border-radius: 20px;
    padding: 3px 14px;
    font-size: 12px;
    color: #8aabff;
    margin: 3px 2px;
}

/* Divider */
hr { border-color: rgba(100,140,255,0.12) !important; }
</style>
""", unsafe_allow_html=True)

# ── Config helpers ────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.yaml"

@st.cache_data
def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 配置")
    cfg = load_config()

    st.markdown("**MATLAB 设置**")
    matlab_exe = st.text_input("matlab.exe 路径", value=cfg["matlab"]["exe_path"], key="matlab_exe")
    mli_path   = st.text_input("COMSOL mli 路径", value=cfg["matlab"]["comsol_mli_path"], key="mli_path")
    port       = st.number_input("COMSOL 服务端口", value=cfg["matlab"]["comsol_server_port"],
                                  min_value=1024, max_value=65535, step=1, key="port")
    timeout    = st.number_input("超时时间 (秒)", value=cfg["matlab"].get("timeout", 600),
                                  min_value=60, max_value=3600, step=60, key="timeout")

    st.markdown("**LLM 设置**")
    api_key = st.text_input("Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""),
                             type="password", key="api_key")
    llm_model = st.selectbox("模型", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
                              index=0, key="llm_model")

    if st.button("💾 保存配置", use_container_width=True):
        cfg["matlab"]["exe_path"]           = matlab_exe
        cfg["matlab"]["comsol_mli_path"]    = mli_path
        cfg["matlab"]["comsol_server_port"] = int(port)
        cfg["matlab"]["timeout"]            = int(timeout)
        cfg["llm"]["model"]                 = llm_model
        save_config(cfg)
        load_config.clear()
        st.success("配置已保存！")

    st.divider()
    st.markdown("**输出目录**")
    out_dir = Path(__file__).parent / cfg["output"]["dir"]
    st.code(str(out_dir), language=None)

    auto_start = st.toggle("自动启动 COMSOL 服务", value=cfg["comsol"].get("auto_start_server", False))

# ── Set API key from sidebar ──────────────────────────────────────────────────
if api_key:
    os.environ["GEMINI_API_KEY"] = api_key

# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 10px 0 4px 0;">
  <h1 style="font-size:2.2rem; font-weight:700; margin:0;
             background: linear-gradient(135deg,#6a82fb,#fc5c7d);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
    🌊 COMSOL AI Simulation
  </h1>
  <p style="color:#6b7db3; font-size:15px; margin-top:6px;">
    用自然语言描述 → 自动生成 COMSOL 6.3 流场 / 声场仿真
  </p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ── Input section ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-title">📝 仿真描述</div>', unsafe_allow_html=True)

    prompt = st.text_area(
        label="用中文或英文描述你的仿真需求",
        placeholder=(
            "示例（流场）：建立一个长10cm、直径10mm的圆管，水以0.01m/s速度从左端流入，右端为零压出口，做稳态流场仿真。\n\n"
            "示例（声场）：在4m×3m的矩形房间中，距左下角(1,1)处有一个500Hz的点声源，四周为刚性墙，进行声压分布仿真。"
        ),
        height=180,
        key="prompt",
        label_visibility="collapsed",
    )

    col_parse, col_run = st.columns([1, 1])
    with col_parse:
        parse_btn = st.button("🔍 解析参数", use_container_width=True, type="primary")
    with col_run:
        run_btn = st.button("🚀 运行仿真", use_container_width=True, disabled="sim_params" not in st.session_state)

    # ── Example prompts ───────────────────────────────────────────────────────
    st.markdown("**快速示例：**")
    examples = {
        "🔵 管道流场": "建立一个长10cm、半径5mm的圆管，水以0.01m/s从底部流入，顶部为零压出口，做稳态层流仿真。",
        "🟡 高速流场": "圆管长20cm半径3mm，流体密度1000 kg/m³黏度0.001 Pa·s，入口速度0.1m/s，稳态求解，使用细网格。",
        "🔴 矩形声场": "4m×3m矩形房间，在(1.0, 0.8)位置有500Hz单极子声源，四周刚性墙，声压仿真。",
        "🟢 低频声场": "6m×4m矩形室内声学，声源位于(2,1.5)，频率200Hz，声源强度0.01，粗网格。",
    }
    for label, ex_prompt in examples.items():
        if st.button(label, use_container_width=True, key=f"ex_{label}"):
            st.session_state["prompt_fill"] = ex_prompt
            st.rerun()

    # Fill from example button
    if "prompt_fill" in st.session_state:
        st.session_state["prompt"] = st.session_state.pop("prompt_fill")
        st.rerun()

with col_right:
    st.markdown('<div class="section-title">🔧 解析的仿真参数 (可编辑)</div>', unsafe_allow_html=True)

    if "sim_params" in st.session_state:
        params_json = st.text_area(
            "params_json",
            value=json.dumps(st.session_state["sim_params"], indent=2, ensure_ascii=False),
            height=280,
            key="params_editor",
            label_visibility="collapsed",
        )
        try:
            edited_params = json.loads(params_json)
            st.session_state["sim_params"] = edited_params
            phys = edited_params.get("physics", "?")
            st.markdown(
                f'<span class="chip">类型: {phys}</span>'
                f'<span class="chip">网格: {edited_params.get("mesh","normal")}</span>'
                f'<span class="chip">求解: {edited_params.get("solver","?")}</span>',
                unsafe_allow_html=True,
            )
        except json.JSONDecodeError as e:
            st.error(f"JSON 格式错误：{e}")
    else:
        st.markdown("""
        <div style="height:280px; display:flex; align-items:center; justify-content:center;
                    color:#3d4f80; font-size:15px; border:1px dashed rgba(100,140,255,0.2);
                    border-radius:12px;">
            点击「解析参数」后，结构化参数将显示在这里
        </div>
        """, unsafe_allow_html=True)

# ── Parse action ──────────────────────────────────────────────────────────────
if parse_btn:
    if not prompt.strip():
        st.warning("请先输入仿真描述！")
    elif not os.environ.get("GEMINI_API_KEY"):
        st.error("请在左侧侧边栏填入 Gemini API Key。")
    else:
        from core.llm_parser import parse_simulation_description
        with st.spinner("🤖 AI 正在解析仿真需求..."):
            try:
                params = parse_simulation_description(prompt, model_name=llm_model)
                st.session_state["sim_params"] = params
                st.success("✅ 参数解析成功！可在右侧编辑后点击「运行仿真」。")
                st.rerun()
            except Exception as e:
                st.error(f"解析失败：{e}")

# ── Run simulation action ─────────────────────────────────────────────────────
if run_btn and "sim_params" in st.session_state:
    from core.script_generator import generate_script
    from core.matlab_runner import run_matlab_script, collect_result_files

    st.divider()
    st.markdown('<div class="section-title">⚙️ 仿真运行日志</div>', unsafe_allow_html=True)

    params   = st.session_state["sim_params"]
    out_dir  = str(Path(__file__).parent / cfg["output"]["dir"])
    log_area = st.empty()
    log_lines: list[str] = []

    def append_log(line: str):
        log_lines.append(line)
        log_area.markdown(
            f'<div class="log-box">{"<br>".join(log_lines[-30:])}</div>',
            unsafe_allow_html=True,
        )

    with st.spinner("正在生成 MATLAB 脚本..."):
        try:
            # Override config from sidebar
            cfg["matlab"]["exe_path"]           = matlab_exe
            cfg["matlab"]["comsol_mli_path"]    = mli_path
            cfg["matlab"]["comsol_server_port"] = int(port)
            cfg["matlab"]["timeout"]            = int(timeout)
            cfg["comsol"]["auto_start_server"]  = auto_start

            script_path = generate_script(params, out_dir)
            append_log(f"✅ 脚本生成: {script_path}")
        except Exception as e:
            st.error(f"脚本生成失败：{e}")
            st.stop()

    append_log("🚀 正在启动 MATLAB + COMSOL LiveLink ...")
    t0 = time.time()
    result = run_matlab_script(script_path, config=cfg, log_callback=append_log)
    elapsed = time.time() - t0

    if result["success"]:
        st.success(f"✅ 仿真完成！耗时 {elapsed:.1f} 秒")
    else:
        st.error("❌ 仿真失败，请检查日志。")
        with st.expander("stderr"):
            st.code(result["stderr"])

    # ── Show results ──────────────────────────────────────────────────────────
    files = collect_result_files(out_dir)
    if files["images"]:
        st.divider()
        st.markdown('<div class="section-title">📊 仿真结果</div>', unsafe_allow_html=True)
        img_cols = st.columns(min(len(files["images"]), 2))
        for i, img_path in enumerate(files["images"]):
            with img_cols[i % 2]:
                st.image(str(img_path), caption=img_path.name, use_container_width=True)
                with open(img_path, "rb") as f:
                    st.download_button(f"⬇ 下载 {img_path.name}", f, file_name=img_path.name,
                                       mime="image/png", use_container_width=True)

    if files["csvs"]:
        import pandas as pd
        st.markdown('<div class="section-title">📄 数据导出</div>', unsafe_allow_html=True)
        for csv_path in files["csvs"]:
            with st.expander(f"📋 {csv_path.name}"):
                try:
                    df = pd.read_csv(csv_path, comment="%")
                    st.dataframe(df, use_container_width=True)
                    with open(csv_path, "rb") as f:
                        st.download_button(f"⬇ 下载 {csv_path.name}", f,
                                           file_name=csv_path.name, mime="text/csv")
                except Exception:
                    st.code(csv_path.read_text())

    if files["mph_files"]:
        st.markdown('<div class="section-title">💾 COMSOL 模型文件</div>', unsafe_allow_html=True)
        for mph in files["mph_files"]:
            st.markdown(f"`{mph}`")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<p style="text-align:center;color:#2d3a5e;font-size:12px;">'
    'COMSOL AI Simulation System · COMSOL 6.3 + MATLAB LiveLink · Powered by Gemini</p>',
    unsafe_allow_html=True,
)
