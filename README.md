# Agent 配置优化

按「**成本优先 + 能力匹配**」原则为 [OpenCode](https://opencode.ai) 与 OhMyOpenCode(OmO) 插件设计的多模型 Agent 路由配置。

📘 **多模型路由分层（核心文档）** → [docs/routing.md](docs/routing.md)

> 该文档独立维护，包含完整设计原则、模型能力对照、路由表、生命周期说明。

## 5 分钟快速开始

### 1. 一键安装（推荐）

#### macOS / Linux
```bash
curl -fsSL https://raw.githubusercontent.com/tomzio/agent-config-optimization/main/config/omo-schemes/install.sh | bash
```

#### Windows PowerShell
```powershell
irm https://raw.githubusercontent.com/tomzio/agent-config-optimization/main/config/omo-schemes/install.ps1 | iex
```

> ⚠️ **curl|bash / irm|iex 在非交互场景下会自动退出**。`read` 拿不到 stdin 会立即 EOF，配合 `set -e` 触发 exit 1。安装脚本已做 TTY 检测，非 TTY 场景会自动降级为「仅下载模式」。如想交互选方案，请直接下载脚本后 `./install.sh` 运行。

安装脚本会自动：
1. 下载所有方案文件到 `~/.config/opencode/omo-schemes/`
2. 运行 `test_switch.py` 验证（10 项测试）
3. 交互式菜单选择方案
4. 切换前调用 `validate_config.py` 校验，失败则取消切换

### 2. 手动安装

```bash
git clone https://github.com/tomzio/agent-config-optimization.git
cd agent-config-optimization

# 1. OmO 路由配置
mkdir -p ~/.omo && cp config/omo.jsonc ~/.omo/omo.jsonc

# 2. OpenCode 主配置（先备份自己的）
cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.bak
cp config/opencode.json ~/.config/opencode/opencode.json

# 3. 凭证（本仓库不含任何 key，需自行提供）
export ARK_API_KEY="<你的火山引擎 Coding Plan key>"
opencode auth login   # 依次添加 deepseek / zhipuai

# 4. 重启 opencode 生效
```

### 3. 日常切换方案

```bash
python3 ~/.config/opencode/omo-schemes/switch.py list              # 列出可用方案
python3 ~/.config/opencode/omo-schemes/switch.py switch 2          # 切换到方案 2（推荐）
python3 ~/.config/opencode/omo-schemes/validate_config.py <file>   # 手动校验
python3 ~/.config/opencode/omo-schemes/test_switch.py              # 跑 10 项测试
```

## 方案对比

| 方案 | 主策略 | 适用场景 |
|---|---|---|
| **Scheme 1** 免费优先 | opencode 免费 → 套餐 → GLM → deepseek 兜底 | 套餐额度紧张、想最大化免费模型 |
| **Scheme 2** 套餐优先 + 角色分层（推荐） | 见 [docs/routing.md](docs/routing.md) | 套餐充足、追求稳定、按角色能力匹配 |
| **Scheme 3** 纯免费（零成本） | 全部 opencode 免费模型，按角色能力分层 | 付费额度耗尽、压测免费上限、拒绝任何按量调用 |

详细方案对比见 `config/omo-schemes/README.md`。

## 工具链

| 工具 | 用途 |
|---|---|
| `switch.py` | 方案切换（带备份、自动校验） |
| `validate_config.py` | 独立配置格式校验（语法 / 模型引用 / variant） |
| `test_switch.py` | 切换脚本 10 项回归测试 |
| `install.sh` / `install.ps1` | 一键安装（带 TTY 检测，非交互场景降级为仅下载） |
| `preflight-checker.py` | 启动前环境检查 |
| `quota-fallback-wrapper.js` | 套餐配额耗尽时降级包装器 |

## 项目结构

```
.
├── README.md                       # 本文件（项目总览）
├── docs/
│   └── routing.md                  # OpenCode/OmO 多模型路由分层（独立维护）
├── .gitignore
└── config/
    ├── omo.jsonc                   # 当前生效的 OmO 路由配置（Scheme 2）
    ├── opencode.json               # OpenCode 主配置：provider / plugin / MCP
    └── omo-schemes/                # 方案文件目录
        ├── README.md               # 方案说明、命令参考
        ├── scheme1-free-first.jsonc
        ├── scheme2-plan-first.jsonc
        ├── scheme3-free-only.jsonc
        ├── switch.py / switch.bat
        ├── validate_config.py
        ├── test_switch.py
        ├── install.sh / install.ps1
        ├── preflight-checker.py
        ├── quota-fallback-wrapper.js
        └── proxy-config.example.json
```

## 踩坑记录

- **`curl | bash` / `irm | iex` 在非交互场景下会自动退出**。`read` 拿不到 stdin 会立即 EOF，配合 `set -e` 触发 exit 1，导致配置根本没切换。本仓库安装脚本已做 TTY 检测，非交互场景自动降级为「仅下载模式」并提示重跑命令。
- **模型 ID 必须逐字核对**。写不存在的模型（如给 `big-pickle` 加 `-free` 后缀）会让 Agent 立即抛 `ProviderModelNotFoundError`，后台任务 0 秒失败、难以察觉。**用 `opencode models` 取实际目录**。
- **`opencode.json` 的 `agent.*.model` 覆盖优先级高于 OmO 配置**，改了 `omo.jsonc` 不生效时先检查这里。
- **顶层键 `plugins` 不存在**，正确的是 `plugin`，写错会被静默忽略。
- **GLM 在 provider 列表里不叫 GLM**：国内按量是 `zhipuai`、国内套餐是 `zhipuai-coding-plan`，海外对应 `zai` / `zai-coding-plan`，搜索要输 `zhipu`。
- **`coding-plan/ark-code-latest` 是服务端路由别名**（响应中 `model=auto`），实际模型不固定；如需稳定行为，改用具体模型。
- **不要用 `GET /models` 判断套餐可用性**，它返回的是通用目录而非套餐白名单。
- 所有配置改动都需要**重启 opencode** 才生效。

## 安全说明

`config/opencode.json` 已将凭证字段替换为 `{env:ARK_API_KEY}` 形式，**不包含任何真实 API key**。请勿把带明文 key 的配置提交到公开仓库。
