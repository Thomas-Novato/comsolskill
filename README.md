#依旧希望大佬支持，给予意见
# 🌊 COMSOL AI Simulation System

> 用自然语言描述，自动生成并运行 COMSOL 6.3 流场 / 声场仿真

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![COMSOL](https://img.shields.io/badge/COMSOL-6.3-orange)](https://comsol.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ 功能概述

| 功能 | 说明 |
|------|------|
| 🤖 自然语言解析 | 用中文 / 英文描述几何、材料、边界条件，AI 自动提取结构化参数 |
| 🔧 MATLAB 脚本生成 | 自动生成 COMSOL LiveLink MATLAB 脚本，无需手动编写 |
| 🚀 一键仿真 | 通过 subprocess 调用 MATLAB + COMSOL，实时显示日志 |
| 📊 结果可视化 | 速度场、压力场、声压级图像直接在界面展示并可下载 |
| 🌊 流场仿真 | 2D 轴对称管道层流（Laminar Flow），支持自定义几何与材料 |
| 🔊 声场仿真 | 2D 矩形腔压力声学（Frequency Domain），单极子声源 |

---

## 🏗️ 系统架构

```
用户自然语言输入
       │
       ▼
 Streamlit Web UI (app.py)
       │
       ▼
 LLM Parser (Gemini API)        ← core/llm_parser.py
 自然语言 → JSON 参数
       │
       ▼
 Script Generator               ← core/script_generator.py
 JSON 参数 → MATLAB .m 脚本
       │
       ▼
 MATLAB Runner                  ← core/matlab_runner.py
 subprocess → matlab.exe
       │
       ▼
 COMSOL 6.3 LiveLink
 执行仿真 → 导出图像 / CSV
       │
       ▼
 Streamlit 展示结果
```

---

## 📋 前置要求

| 软件 | 版本要求 | 说明 |
|------|---------|------|
| COMSOL Multiphysics | **6.3** | 需含 CFD 模块（流场）和声学模块（声场） |
| MATLAB | R2022b ~ R2024b | 与 COMSOL 6.3 LiveLink 兼容 |
| Python | 3.10+ | 运行 Streamlit 前端 |
| Google Gemini API Key | — | 用于自然语言解析 |

### COMSOL LiveLink 配置

1. 打开 COMSOL Multiphysics → `文件 > 首选项 > LiveLink`
2. 确认 **LiveLink for MATLAB** 已启用
3. 记录 `mli` 文件夹路径，默认为：
   ```
   C:\Program Files\COMSOL\COMSOL63\Multiphysics\mli
   ```
4. 启动 COMSOL 服务（两种方式任选其一）：
   - **方式 A（推荐）**：在 COMSOL 中通过 `文件 > LiveLink > 启动 MATLAB` 打开 MATLAB
   - **方式 B（命令行）**：
     ```powershell
     & "C:\Program Files\COMSOL\COMSOL63\Multiphysics\bin\win64\comsolserver.exe"
     ```

---

## 🚀 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/<your-username>/comsolskill.git
cd comsolskill
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

```bash
# 复制并编辑 .env 文件
copy .env.example .env
```

编辑 `.env`，填入你的 Gemini API Key：
```
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. 编辑 `config.yaml`

```yaml
matlab:
  exe_path: "matlab.exe"          # 或完整路径，如 C:/Program Files/MATLAB/R2024b/bin/matlab.exe
  comsol_mli_path: "C:/Program Files/COMSOL/COMSOL63/Multiphysics/mli"
  comsol_server_port: 2036
  timeout: 600

comsol:
  auto_start_server: false        # 若要 Python 自动启动 COMSOL 服务则改为 true
```

### 5. 启动应用

```bash
streamlit run app.py
```

浏览器将自动打开 `http://localhost:8501`

---

## 💬 使用示例

### 流场仿真

在输入框中输入：
```
建立一个长10cm、直径10mm的圆管，水以0.01m/s速度从底部流入，
顶部为零压出口，做稳态层流仿真，使用正常网格。
```

AI 解析结果：
```json
{
  "physics": "flow",
  "geometry": { "type": "pipe", "length": 0.1, "radius": 0.005 },
  "material": { "fluid": "water", "density": 1000, "viscosity": 0.001 },
  "boundary": { "inlet_velocity": 0.01, "outlet_condition": "pressure_zero" },
  "mesh": "normal",
  "solver": "stationary"
}
```

输出结果：
- `velocity_field.png` — 速度场云图 + 速度矢量
- `pressure_field.png` — 压力场云图
- `centerline_data.csv` — 轴线速度 / 压力数据

---

### 声场仿真

```
在4m×3m的矩形房间中，距左下角(1,1)处有一个500Hz的点声源，
四周为刚性墙，进行声压分布仿真。
```

输出结果：
- `spl_field.png` — 声压级（dB）分布图
- `pressure_field.png` — 声压实部分布图

---

## 📁 项目结构

```
comsolskill/
├── app.py                   # Streamlit 主程序
├── config.yaml              # MATLAB / COMSOL / LLM 配置
├── requirements.txt         # Python 依赖
├── .env.example             # API Key 模板
├── .gitignore
│
├── core/
│   ├── llm_parser.py        # 自然语言 → JSON 参数（Gemini API）
│   ├── script_generator.py  # JSON 参数 → MATLAB .m 脚本
│   └── matlab_runner.py     # subprocess 调用 MATLAB + 结果收集
│
├── templates/
│   ├── flow_template.m      # COMSOL 层流仿真模板
│   └── acoustic_template.m  # COMSOL 压力声学仿真模板
│
├── output/                  # 生成的脚本、图像、CSV、.mph 文件
│   └── .gitkeep
│
└── tests/
    ├── test_llm_parser.py       # LLM 解析器单元测试（含 mock）
    └── test_script_generator.py # 脚本生成器单元测试
```

---

## 🧪 运行测试

```bash
cd comsolskill
python -m pytest tests/ -v
```

> 测试不需要 COMSOL / MATLAB 环境，LLM 调用使用 mock。

---

## ⚠️ 常见问题

**Q: MATLAB 找不到 COMSOL LiveLink？**
> 确认 `config.yaml` 中 `comsol_mli_path` 路径正确，且 COMSOL 服务正在运行。

**Q: 运行时提示 `mphstart` 失败？**
> 先手动在命令行运行 `comsolserver.exe`，或在 COMSOL GUI 中启动 LiveLink。

**Q: 声场仿真中声源点索引错误？**
> COMSOL 中几何点编号依赖于建模顺序。如报错，请打开生成的 `.mph` 文件，在 COMSOL GUI 中确认点编号后修改 `acoustic_template.m` 中 `selection.set([5])` 的值。

**Q: Gemini API 报 quota 错误？**
> 更换 API Key 或等待配额重置；也可在 `config.yaml` 中将模型改为 `gemini-1.5-flash`（更快、配额更宽松）。

---

## 🔮 未来规划

- [ ] 支持 3D 几何（球形腔、复杂管道）
- [ ] 湍流模型（k-ε / k-ω SST）
- [ ] 流固声耦合仿真
- [ ] 参数化扫描（Reynolds 数 / 频率扫描）
- [ ] 支持 OpenAI GPT-4o 作为 LLM 后端

---

## 📄 License

MIT © 2026
