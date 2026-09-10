# OpenCode/OmO 多模型路由配置管理

一套可一键安装、一键切换的多模型分层路由配置，解决 **配额耗尽不触发 fallback** 与 **国内模型不可访问** 两大问题。支持 macOS / Linux / Windows，全程带配置格式与模型引用校验。

---

## 📖 使用方法

### 1️⃣ 一键安装

**macOS / Linux：**
```bash
curl -fsSL https://raw.githubusercontent.com/tomzio/agent-config-optimization/main/config/omo-schemes/install.sh | bash
```

**Windows PowerShell：**
```powershell
irm https://raw.githubusercontent.com/tomzio/agent-config-optimization/main/config/omo-schemes/install.ps1 | iex
```

脚本会自动：
1. 下载全部工具到 `~/.config/opencode/omo-schemes/`
2. 运行测试套件（9/9）验证安装
3. 弹出菜单让你选择方案（1 / 2 / 3 / 4 / q）
4. 切换方案前自动做 **配置格式验证**（JSONC 语法 + 模型引用合法性），通过才应用
5. 切换时会自动**备份**当前 `~/.omo/omo.jsonc` 到 `~/.omo/backups/`

> ⚠️ `curl | bash` 方式受 GFW 与 stdin 占用影响可能无法完成交互式方案选择。脚本会**自动降级为仅下载模式**，并提示你在终端里重新运行 `bash ~/.config/opencode/omo-schemes/install.sh` 选方案。如果首次用 curl | bash，文件已下载，直接重跑安装即可，无需再 curl。

### 2️⃣ 选择方案

| 选项 | 方案 | 分层策略 |
|------|------|----------|
| **1** | Scheme 1 免费优先 | 免费 → coding-plan 套餐 → zhipuai GLM → deepseek（末位） |
| **2** | Scheme 2 套餐优先+隔离（推荐） | coding-plan → **deepseek 官方独立配额** → 免费 → zhipuai → deepseek（末位） |
| **3** | Scheme 3 纯免费（零成本） | opencode 免费 4 层降级（无任何付费调用） |

> 💡 日常推荐 **方案 2**：通过 Provider 隔离让 deepseek 走官方独立配额，套餐耗尽也不影响它，彻底解决 fallback 不触发问题。
> 方案 3 适合**完全不想产生任何付费调用**的场景（个人体验/学习/零成本开发）。

### 3️⃣ 切换后验证

```bash
# 查看当前生效方案
python3 ~/.config/opencode/omo-schemes/switch.py current

# 校验方案配置（不切换）
python3 ~/.config/opencode/omo-schemes/switch.py check 2

# 运行完整测试
python3 ~/.config/opencode/omo-schemes/test_switch.py
```

### 4️⃣ 重启生效

**重启 OpenCode** 使新配置生效，然后在 OpenCode 内运行 `/model` 确认模型列表正确，派发一个测试任务验证 fallback 链是否生效。

### 日常切换（无需重装）

已安装后，随时切换方案：

```bash
# macOS / Linux
python3 ~/.config/opencode/omo-schemes/switch.py switch 2

# Windows
python ~/.config/opencode/omo-schemes/switch.bat switch 2

# 快捷方式（脚本目录下）
cd ~/.config/opencode/omo-schemes && python3 switch.py switch 2
```

切换其他命令：

```bash
python3 switch.py list       # 列出所有可用方案
python3 switch.py current    # 查看当前生效方案
python3 switch.py check <1|2> # 校验指定方案（不切换）
python3 switch.py switch <1|2> # 切换方案
```

### 手动校验配置（独立脚本）

```bash
python3 ~/.config/opencode/omo-schemes/validate_config.py <配置路径>
# 示例
python3 ~/.config/opencode/omo-schemes/validate_config.py ~/.config/opencode/omo-schemes/scheme2-plan-first.jsonc
# 支持 --syntax / --models / --variants 单项校验
```

---

## 📦 方案对比

| 维度 | Scheme 1：免费优先 | Scheme 2：套餐优先+隔离 | Scheme 3：纯免费 |
|------|-------------------|----------------------|----------------|
| 分层顺序 | 免费 → coding-plan → zhipuai → deepseek | coding-plan → **deepseek官方** → 免费 → zhipuai → deepseek末位 | opencode 免费 4 层降级（无付费调用） |
| 核心优势 | 最大化省配额 | **deepseek 独立配额**，套餐耗尽不影响 | **零成本**，完全无付费风险 |
| 适用场景 | 套餐紧张 | 套餐充足、生产环境、追求稳定 | 个人体验、学习、零成本开发 |
| muse-spark | 主力（需代理） | **已剔除**（国内不可访问） | **已剔除**（国内不可访问） |
| 参考 Commit | `a0fa618` | `a32b23c` | Scheme 3 扩展 |

---

## 🛠 工具清单

| 工具 | 用途 |
|------|------|
| `switch.py` / `switch.bat` | 跨平台方案切换 |
| `test_switch.py` | 自动化测试套件（9/9） |
| `validate_config.py` | 配置格式验证（语法/模型引用/variant） |
| `quota-fallback-wrapper.js` | Provider Wrapper 拦截 429 触发 fallback |
| `preflight-checker.py` | Pre-flight 配额检查（5min 缓存） |
| `proxy-config.example.json` | 代理配置示例 |

---

## ⚙️ 解决的核心问题

### 配额耗尽不触发 Fallback
**根因**：coding-plan 是自定义 provider，返回 429 或错误 200 响应时，OpenCode 内部 fallback 不识别为可重试错误。

**三层方案**：
- **架构级**：Scheme 2 让 deepseek 走官方 provider 独立配额（✅ 最彻底，现状生效）
- **运行时级**：`quota-fallback-wrapper.js` 拦截 429 抛 `retryable=true`
- **应用级**：`preflight-checker.py` 调用前查配额，耗尽可自动切换

### 国内 muse-spark 不可访问
1. Scheme 2 已剔除 muse-spark 系列，全链路使用国内直连模型
2. 配置代理：`opencode.json` 的 provider.options 加 `"proxy": "http://127.0.0.1:7890"`（参考 `proxy-config.example.json`）
3. 环境变量：`export HTTPS_PROXY=http://127.0.0.1:7890`

---

## 📁 项目结构

```
config/omo-schemes/
├── README.md                       # 本文档
├── scheme1-free-first.jsonc        # 方案 1：免费优先
├── scheme2-plan-first.jsonc        # 方案 2：套餐优先+隔离（推荐）
├── scheme3-free-only.jsonc         # 方案 3：纯免费（零成本）
├── switch.py / switch.bat          # 切换工具
├── install.sh / install.ps1        # 一键安装
├── test_switch.py                  # 测试
├── validate_config.py              # 配置校验
├── quota-fallback-wrapper.js
├── preflight-checker.py
└── proxy-config.example.json
~/.omo/
├── omo.jsonc                       # 当前生效配置
└── backups/                        # 自动备份
```

---

## 📝 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.2 | 2026-09-07 | 新增 `validate_config.py` 独立校验脚本并集成到安装流程；README 重排使用方法 |
| 1.1 | 2026-09-06 | 新增一键安装脚本、完善文档、完整测试覆盖 |
| 1.0 | 2026-09-06 | 初始版本 |

---

## 🔗 相关链接

| 资源 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/tomzio/agent-config-optimization |
| 当前生效配置 | `config/omo.jsonc` |
| 方案 2 配置 | `config/omo-schemes/scheme2-plan-first.jsonc` |
| OpenCode 文档 | https://opencode.ai/docs |

---

## ⚖️ 许可证

MIT License — 可自由使用、修改、分发。
