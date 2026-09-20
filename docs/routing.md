# OpenCode / OmO 多模型路由分层

> 本文档独立维护。如果你只关心「怎么把配置跑起来」，看 [README.md](../README.md)。

按「**按角色能力选型 + 4 层降级**」原则，为 [OpenCode](https://opencode.ai) 与 OhMyOpenCode(OmO) 插件设计的多模型 Agent 路由配置。目标是在保证质量的前提下把付费调用压到最低。

## 设计原则

### 1. 按角色负载特征选主模型

| 角色类别 | 代表 Agent / Category | 选型依据 |
|---|---|---|
| **核心执行** | `sisyphus`、`hephaestus` | 用套餐旗舰（质量优先、调用频次最高、套餐内成本最低） |
| **高推理** | `oracle`、`metis`、`momus`、`ultrabrain`、`deep` | 推理基准最高的免费模型 |
| **高频轻量** | `librarian`、`explore`、`quick`、`unspecified-low`、`sisyphus-junior` | 快、便宜、context 够大的 flash 模型 |
| **规划创作** | `prometheus`、`atlas`、`artistry`、`unspecified-high`、`writing` | 输出自然语言为主，对齐限时免费 v4.1-flash |
| **多模态** | `multimodal-looker`、`visual-engineering` | 支持 image/video/pdf 的免费模型 |

### 2. 4 层降级（fallback）链

```
① opencode 免费（主力，零成本）
        ↓
② zhipuai GLM 按量（付费前的最后一道闸）
        ↓
③ deepseek 按量（v4-flash / 限时免费的 v4.1-flash）
        ↓
④ coding-plan 套餐（仅核心执行角色用做主模型，套餐额度作为最后兜底）
```

OpenCode Zen 的免费模型属「限时免费 / 反馈收集期」，随时可能下线。每条链都必须有付费兜底，否则模型消失时 Agent 直接崩溃（`ProviderModelNotFoundError`）。

### 3. `variant` 只写给真正支持的模型

`variant`（推理强度预设）只有在模型自身声明了对应 variants 时才生效，写错会被静默 normalize。

| 模型 | 可用 variant |
|---|---|
| `opencode/ling-3.0-flash-fin-free` | `low` / `medium` / `high` |
| `deepseek/deepseek-v4-flash` | `low` / `high` / `max` |
| `deepseek/deepseek-v4-flash-vision-exp` | `low` / `high` / `max` |
| `zhipuai/glm-5.2` | `high` / `max` |
| `zhipuai/glm-5.3`、`zhipuai/glm-5.3-flash` | `low` / `high` / `max` |
| `opencode-go/muse-spark-1.2/1.3-contributor` | `minimal` / `low` / `medium` / `high` / `xhigh` |
| `opencode-go/gpt-5.6-luna` | `none` / `low` / `medium` / `high` / `xhigh` / `max` |
| `opencode-go/grok-4.6`、`qwen3.8-flash`、`qwen3.8-max` | `low` / `medium` / `high` / `xhigh` |
| `opencode-go/deepseek-v4-flash`、`deepseek-v4.1-flash`、`glm-5.3`、`glm-5.3-flash` | `low` / `high` / `max` |
| `opencode-go/kimi-k3` | 仅 `max`；`minimax-m3` 仅 `none` / `thinking` |
| `coding-plan/*`、`opencode/{big-pickle, mimo, nemotron-*}` | **无**（不要写） |

> 当 `opencode models` 输出与本表不一致时，**以 `opencode models` 为准**。本表更新于 2026-09-20。

### 4. 套餐模型不能配 variant（火山 coding-plan）

`coding-plan/*` 是火山引擎 Coding Plan 套餐内的具体模型（`ark-code-latest` 除外，它是服务端自动路由别名）。所有套餐模型目录中无 variants，配了会被静默忽略。

> 注意区分：**Opencode Go 套餐**（`opencode-go/*`）的模型多数**支持** variant（见上表），与火山 coding-plan 不同。

## 模型能力对照

### 免费层 · opencode（cost = 0）

| 模型 | context | output | 多模态 | variant | 用途 |
|---|---|---|---|---|---|
| `nemotron-3-ultra-free` | 1M | 128k | — | 无 | 推理最强（SWE-Bench 70.7） |
| `nemotron-3.5-lightning-free` | 262k | **262k** | — | 无 | 超长输出 |
| `ling-3.0-flash-fin-free` | 262k | 32k | — | low/medium/high | 高频轻量检索 |
| `big-pickle` | 200k | 32k | — | 无 | 主动探索、幻觉偏多 |
| `mimo-v2.5-free` | 200k | 32k | image/video/audio | 无 | 多模态备选 |

> ⚠️ `muse-spark-1.2/1.3-contributor-free` 综合最强但国内不可访问，已剔除。

### 套餐层 · coding-plan（火山引擎 Coding Plan）

| 模型 | 用途 | variant |
|---|---|---|
| `glm-5.3` | 通用旗舰（sisyphus 主模型） | 无 |
| `kimi-k2.7-code` | 代码特化（hephaestus 主模型） | 无 |
| `deepseek-v4-flash` / `deepseek-v4-pro` | 套餐内按量 | 无 |
| `doubao-seed-2-1-turbo` / `doubao-seed-2.0-lite` / `doubao-seed-evolving` | 豆包多模态 | 无 |
| `glm-5.2` | 上一代旗舰 | 无 |
| `minimax-m3` | MiniMax 旗舰 | 无 |
| `ark-code-latest` | 服务端自动路由别名（响应中 `model=auto`） | — |

> ⚠️ 套餐白名单以火山引擎 Coding Plan 控制台为准，不要用 `GET /models` 判断可用性。

### 套餐层 · opencode-go（Opencode Go 订阅，Scheme 4 主力）

一个订阅聚合多厂商旗舰，国内直连；**套餐版 muse-spark 国内可达**（免费版不可达）。

| 模型 | 厂商 | variant | 用途 |
|---|---|---|---|
| `glm-5.3` / `glm-5.3-flash` / `glm-5.2` / `glm-5.1` | 智谱 | 5.3: low/high/max | 通用旗舰 + flash 轻量 |
| `kimi-k3` / `kimi-k2.7-code` / `kimi-k2.6` | 月之暗面 | k3 仅 max | k3 顶配推理、k2.7 代码特化 |
| `deepseek-v4-flash` / `deepseek-v4.1-flash` / `deepseek-v4-flash-vision-exp` / `deepseek-v4-pro` | DeepSeek | flash: low/high/max | v4.1-flash 是 0910 继任者 |
| `gpt-5.6-luna` | OpenAI | none~xhigh/max | 跨厂兜底旗舰 |
| `grok-4.6` | xAI | low/medium/high/xhigh | 500k output，创作 |
| `qwen3.8-max` / `qwen3.8-flash` / `qwen3.7-max` / `qwen3.7-plus` / `qwen3.6-plus` | 阿里 | max/flash: low/medium/xhigh | flash 高频轻量 |
| `muse-spark-1.2/1.3-contributor` | Mozilla | minimal~xhigh | **国内可达**，agentic/多模态 |
| `minimax-m3` / `minimax-m2.7` | MiniMax | m3: none/thinking | — |
| `mimo-v2.5` / `mimo-v2.5-pro` | 小米 | 无 | 多模态 |
| `longcat-2.0`、`hy3`、`hy4-preview` | 美团/虎牙 | longcat: low/medium/high | 补充位 |

### 按量层 · zhipuai GLM

| 模型 | 价格 in/out (per 1M) | 多模态 | variant |
|---|---|---|---|
| `glm-5.3` | $1.4 / $4.4 | — | low/high/max |
| `glm-5.3-flash` | **$0.075 / $0.25** | image/video/pdf | low/high/max |
| `glm-5.2` | 上一代旗舰 | — | high/max |
| `glm-4.7` | 按量 | — | 无 |
| `glm-4.7-flash` | **$0 / $0** | — | 无 |
| `glm-4.7-flashx` | $0.07 / $0.4 | — | 无 |

### 末位层 · deepseek 按量

| 模型 | 价格 in/out (per 1M) | variant | 备注 |
|---|---|---|---|
| `deepseek-v4-flash` | $0.14 / $0.28 | low/high/max | 写作链路兜底 |
| `deepseek-v4-pro` | $0.435 / $0.87 | high/max | **2026-09-14 12:00 下线** |
| ~~`deepseek-v4.1-flash-expires-on-0910`~~ | ~~$0 / $0~~ | 无 | **2026-09-10 到期下线**，继任者 `opencode-go/deepseek-v4.1-flash`（Go 套餐内） |

## 完整路由表（基于 Scheme 2）

> `cp/` = `coding-plan/`，`ds/` = `deepseek/`，`go/` = `opencode-go/`，无前缀 = `opencode/`

### Agents

| Agent | 路由链（主模型 → 降级顺序） |
|---|---|
| `sisyphus` | `cp/glm-5.3` → `big-pickle` → `ds/v4-flash`(high) |
| `hephaestus` | `cp/kimi-k2.7-code` → `big-pickle` → `ds/v4-flash`(high) → `zhipuai/glm-5.3`(high) |
| `oracle` | `nemotron-3-ultra` → `go/v4.1-flash` → `ds/v4-flash`(high) |
| `librarian` | `ling-3.0-flash-fin` → `zhipuai/glm-4.7-flash` → `zhipuai/glm-4.7` |
| `explore` | `ling-3.0-flash-fin` → `go/v4.1-flash` → `ds/v4-flash`(high) → `zhipuai/glm-4.7-flash` |
| `multimodal-looker` | `mimo-v2.5` → `go/v4.1-flash` → `ds/v4-flash`(high) → `zhipuai/glm-5.3`(low) |
| `prometheus` | `go/v4.1-flash` → `nemotron-3-ultra` → `ds/v4-flash`(high) → `zhipuai/glm-5.3` |
| `metis` | `big-pickle` → `nemotron-3-ultra` → `ds/v4-flash`(high) → `zhipuai/glm-5.3`(high) |
| `momus` | `big-pickle` → `nemotron-3-ultra` → `ds/v4-flash`(high) → `zhipuai/glm-5.3`(max) |
| `atlas` | `go/v4.1-flash` → `big-pickle` → `go/v4.1-flash` → `zhipuai/glm-5.3` |
| `sisyphus-junior` | `nemotron-3.5-lightning` → `go/v4.1-flash` → `ds/v4-flash`(high) → `zhipuai/glm-4.7` |

### Categories

| Category | 路由链 |
|---|---|
| `visual-engineering` | `mimo-v2.5` → `go/v4.1-flash` → `zhipuai/glm-5.3`(max) → `ds/v4-flash`(high) |
| `ultrabrain` | `nemotron-3-ultra` → `go/v4.1-flash` → `ds/v4-flash`(high) → `zhipuai/glm-5.3`(max) |
| `deep` | `big-pickle` → `nemotron-3-ultra` → `ds/v4-flash`(high) |
| `artistry` | `go/v4.1-flash` → `mimo-v2.5` → `zhipuai/glm-5.3`(high) → `ds/v4-flash`(high) |
| `quick` | `ling-3.0-flash-fin` → `zhipuai/glm-4.7-flash` |
| `unspecified-low` | `ling-3.0-flash-fin`(high) → `go/v4.1-flash` → `zhipuai/glm-4.7` → `ds/v4-flash`(high) |
| `unspecified-high` | `go/v4.1-flash` → `nemotron-3-ultra` → `ds/v4-flash`(high) → `zhipuai/glm-5.3` |
| `writing` | `go/v4.1-flash` → `zhipuai/glm-5.3` → `zhipuai/glm-4.7` → `ds/v4-flash`(high) |

## Scheme 3：纯免费（零成本）

> 适用场景：完全不想产生任何付费调用（个人体验 / 学习 / 零成本开发）。
> 不引用 `coding-plan/*`、`zhipuai/*`、`deepseek/*`，全链路仅用 5 个 opencode 免费模型。

### 主模型分配（按角色能力）

| 角色 | Agent / Category | 主模型 | 选型依据 |
|---|---|---|---|
| 核心执行 / 高推理 | `sisyphus`、`hephaestus`、`oracle`、`metis`、`momus`、`ultrabrain`、`deep` | `nemotron-3-ultra-free` | SWE-Bench 70.7，推理最强 |
| 规划创作 | `prometheus`、`atlas`、`writing` | `nemotron-3.5-lightning-free` | 262k output，长文输出 |
| 创意类 | `artistry` | `big-pickle` | 主动探索，幻觉偏多反而是优点 |
| 高频轻量 | `librarian`、`explore`、`quick`、`unspecified-low`、`sisyphus-junior` | `ling-3.0-flash-fin-free` | 快 + 262k ctx，支持 low/medium/high |
| 多模态 | `multimodal-looker`、`visual-engineering` | `mimo-v2.5-free` | image/video/audio |

### 4 层降级（仅 opencode 内）

```
主模型（按角色）
  → 同组其他免费模型（写作位用 big-pickle / 创意用 nemotron-3.5）
  → 跨组免费模型（补位：multimodal-looker 进 ling / ling 进 nemotron）
  → big-pickle（末位）
```

**关键差异**：Scheme 3 没有付费兜底层。如果 5 个 opencode 免费模型同时下线（极端情况），Agent 会立即崩溃。仅在「零成本」是首要约束时使用。

### 完整路由表

> 无前缀 = `opencode/`

#### Agents

| Agent | 路由链 |
|---|---|
| `sisyphus` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `mimo-v2.5` → `ling-3.0-flash-fin`(high) → `big-pickle` |
| `hephaestus` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `oracle` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `librarian` | `ling-3.0-flash-fin` → `nemotron-3.5-lightning` → `nemotron-3-ultra` → `mimo-v2.5` → `big-pickle` |
| `explore` | `ling-3.0-flash-fin` → `nemotron-3.5-lightning` → `nemotron-3-ultra` → `mimo-v2.5` → `big-pickle` |
| `multimodal-looker` | `mimo-v2.5` → `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(medium) → `big-pickle` |
| `prometheus` | `nemotron-3.5-lightning` → `nemotron-3-ultra` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `metis` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `momus` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `atlas` | `nemotron-3.5-lightning` → `nemotron-3-ultra` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `sisyphus-junior` | `ling-3.0-flash-fin` → `nemotron-3.5-lightning` → `nemotron-3-ultra` → `mimo-v2.5` → `big-pickle` |

#### Categories

| Category | 路由链 |
|---|---|
| `visual-engineering` | `mimo-v2.5` → `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `big-pickle` |
| `ultrabrain` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `deep` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `artistry` | `big-pickle` → `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` |
| `quick` | `ling-3.0-flash-fin` → `nemotron-3.5-lightning` → `nemotron-3-ultra` → `mimo-v2.5` → `big-pickle` |
| `unspecified-low` | `ling-3.0-flash-fin`(high) → `nemotron-3.5-lightning` → `nemotron-3-ultra` → `mimo-v2.5` → `big-pickle` |
| `unspecified-high` | `nemotron-3-ultra` → `nemotron-3.5-lightning` → `ling-3.0-flash-fin`(high) → `mimo-v2.5` → `big-pickle` |
| `writing` | `nemotron-3.5-lightning` → `nemotron-3-ultra` → `ling-3.0-flash-fin`(medium) → `mimo-v2.5` → `big-pickle` |

### 风险与权衡

| 风险 | 缓解 |
|---|---|
| 免费模型随时下线，Agent 立即崩溃 | 定期 `opencode models` 检查 + 设置「模型消失」告警 |
| 推理质量整体低于 Scheme 2 | `nemotron-3-ultra` 是当前免费模型推理最强，承担主力 |
| 无付费兜底 | 不用于生产关键任务，仅适合学习/体验 |
| 不可用 `muse-spark-*`（国内） | 5 个模型全国内直连，无代理需求 |

切换：`python3 switch.py switch 3`（前提是 `~/.omo/omo.jsonc` 已被方案 3 覆盖；详见 `config/omo-schemes/README.md`）。

---

## Scheme 4：Opencode Go 套餐优先（Go 订阅推荐）

> 适用场景：已订阅 **Opencode Go**。一个订阅聚合多厂商旗舰（GLM / Kimi / DeepSeek / GPT / Grok / Qwen / muse-spark / MiniMax / 小米），国内直连。
> 主链全走 `opencode-go/*`，链尾用 `opencode/*` 免费模型兜底；**零 coding-plan / zhipuai / deepseek 按量 provider，零按量费用**。
> 关键红利：套餐版 `muse-spark-*` 国内可达（免费版不可达）。

### 主模型分配（按角色能力）

| 角色 | Agent / Category | 主模型 | variant |
|---|---|---|---|
| 核心执行 | `sisyphus` | `go/glm-5.3` | — |
| 代码特化 | `hephaestus` | `go/kimi-k2.7-code` | — |
| 重推理 / 评审 | `oracle`、`metis`、`momus`、`ultrabrain`、`deep` | `go/muse-spark-1.3-contributor` | xhigh |
| 顶配规划 | `prometheus`、`atlas`、`unspecified-high` | `go/kimi-k3` | max |
| 创作 | `artistry`、`writing` | `go/grok-4.6`（500k output） | high |
| 高频轻量 | `librarian`、`explore`、`quick`、`unspecified-low`、`sisyphus-junior` | `go/glm-5.3-flash` / `go/qwen3.8-flash` | medium/high |
| 多模态 | `multimodal-looker`、`visual-engineering` | `go/mimo-v2.5-pro` / `go/deepseek-v4-flash-vision-exp` | high/max |

### 降级链

```
opencode-go 主模型（按角色）
  → opencode-go 跨厂旗舰（gpt-5.6-luna / grok-4.6 / glm-5.3 / deepseek-v4.1-flash，仍在订阅内）
  → opencode 免费兜底（nemotron-3-ultra-free / nemotron-3.5-lightning-free / big-pickle / ling / mimo）
```

### 完整路由表

> `go/` = `opencode-go/`，无前缀 = `opencode/`

#### Agents

| Agent | 路由链（主模型 → 降级顺序） |
|---|---|
| `sisyphus` | `go/glm-5.3` → `go/gpt-5.6-luna`(high) → `big-pickle` |
| `hephaestus` | `go/kimi-k2.7-code` → `go/glm-5.3`(high) → `go/deepseek-v4.1-flash`(high) → `big-pickle` |
| `oracle` | `go/muse-spark-1.3-contributor`(xhigh) → `go/gpt-5.6-luna`(max) → `go/grok-4.6`(xhigh) → `nemotron-3-ultra-free` |
| `librarian` | `go/glm-5.3-flash` → `go/qwen3.8-flash`(medium) → `ling-3.0-flash-fin-free`(high) |
| `explore` | `go/glm-5.3-flash` → `go/deepseek-v4-flash`(high) → `go/longcat-2.0`(medium) → `ling-3.0-flash-fin-free`(high) |
| `multimodal-looker` | `go/mimo-v2.5-pro` → `go/deepseek-v4-flash-vision-exp`(high) → `go/muse-spark-1.3-contributor`(low) → `mimo-v2.5-free` |
| `prometheus` | `go/kimi-k3`(max) → `go/grok-4.6`(high) → `go/glm-5.3`(max) → `nemotron-3-ultra-free` |
| `metis` | `go/muse-spark-1.3-contributor`(xhigh) → `go/gpt-5.6-luna`(high) → `go/glm-5.3`(max) → `big-pickle` |
| `momus` | `go/muse-spark-1.3-contributor`(xhigh) → `go/grok-4.6`(xhigh) → `go/gpt-5.6-luna`(max) → `nemotron-3-ultra-free` |
| `atlas` | `go/kimi-k3`(max) → `go/gpt-5.6-luna`(high) → `go/glm-5.3`(max) → `big-pickle` |
| `sisyphus-junior` | `go/glm-5.3-flash` → `go/qwen3.8-flash`(medium) → `go/deepseek-v4-flash`(high) → `nemotron-3.5-lightning-free` |

#### Categories

| Category | 路由链 |
|---|---|
| `visual-engineering` | `go/mimo-v2.5-pro` → `go/muse-spark-1.3-contributor`(high) → `go/deepseek-v4-flash-vision-exp`(max) → `mimo-v2.5-free` |
| `ultrabrain` | `go/muse-spark-1.3-contributor`(xhigh) → `go/gpt-5.6-luna`(max) → `go/grok-4.6`(xhigh) → `nemotron-3-ultra-free` |
| `deep` | `go/muse-spark-1.3-contributor`(xhigh) → `go/kimi-k3`(max) → `go/glm-5.3`(max) → `big-pickle` |
| `artistry` | `go/grok-4.6`(high) → `go/minimax-m3`(thinking) → `go/mimo-v2.5-pro` → `big-pickle` |
| `quick` | `go/glm-5.3-flash` → `go/qwen3.8-flash`(medium) → `ling-3.0-flash-fin-free`(high) |
| `unspecified-low` | `go/glm-5.3-flash`(high) → `go/qwen3.8-flash`(medium) → `go/deepseek-v4-flash`(high) → `ling-3.0-flash-fin-free`(high) |
| `unspecified-high` | `go/kimi-k3`(max) → `go/gpt-5.6-luna`(xhigh) → `go/muse-spark-1.3-contributor`(high) → `nemotron-3-ultra-free` |
| `writing` | `go/grok-4.6`(high) → `go/minimax-m3`(thinking) → `go/kimi-k3`(max) → `nemotron-3.5-lightning-free` |

### 风险与权衡

| 风险 | 缓解 |
|---|---|
| Go 订阅到期后全链主模型失效 | 链尾保留 opencode 免费兜底；到期后切回 Scheme 2/3 |
| 免费模型同时下线（极端） | 同 Scheme 3，需定期 `opencode models` 检查 |
| 不依赖按量 provider | 订阅内跨厂旗舰互为降级，无按量费用 |

切换：`python3 switch.py switch 4`（详见 `config/omo-schemes/README.md`）。

---

## 模型生命周期与下线处理

| 事件 | 影响范围 | 处理 |
|---|---|---|
| 用户订阅 Opencode Go | — | 新增 Scheme 4，opencode-go 套餐优先 + 免费兜底 |
| 免费版 `muse-spark-*` 国内不可访问 | Scheme 1/2/3 | 已剔除；Scheme 4 改用**套餐版** `opencode-go/muse-spark-*`（国内可达） |
| `deepseek-v4-pro` 2026-09-14 下线 | 当前配置无引用 | 已在路由表中移除 v4-pro；如未来再需用，仅限重推理岗 `oracle` / `momus` / `ultrabrain` |
| `deepseek-v4.1-flash-expires-on-0910` 2026-09-10 到期 | Scheme 2（14 处） | 继任者 `opencode-go/deepseek-v4.1-flash`（Go 套餐同名转正版，零按量费） |
| `opencode/deepseek-v4-flash-free` 已失效 | 全量 | 先替换为 0910 限时免费，0910 到期后改 opencode-go 版 |
| `opencode/north-mini-code-free` 不存在 | 全量 | 替换为 `ling-3.0-flash-fin-free` |
| `opencode/big-pickle-free` 不存在 | 全量 | 替换为 `opencode/big-pickle`（无 -free 后缀） |
| `glm/glm-4-*` provider 名错 | 全量 | provider 改为 `zhipuai`，模型升 4.7/5.3 系列 |

当新模型加入或下线时，先跑 `opencode models` 确认清单，再用 `python3 validate_config.py` 全量校验；不要手动搜目录缓存。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-20 | 新增 Scheme 4（Opencode Go 套餐优先），opencode-go 订阅全模型 + 免费兜底，零按量费 |
| 2026-09-20 | `deepseek-v4.1-flash-expires-on-0910` 到期下线，Scheme 2 中 14 处由 `opencode-go/deepseek-v4.1-flash` 继任 |
| 2026-09-10 | 新增 Scheme 3 纯免费（零成本）方案；不引用 coding-plan / zhipuai / deepseek，仅用 5 个 opencode 免费模型 |
| 2026-09-10 | 重写顶层注释为「按角色分层」；剔除 muse-spark、glm/glm-4-*、big-pickle-free、north-mini-code-free；ark-code-latest 替换为具体模型；纠正全部非法 variant |
| 2026-09-07 | ark-code-latest 替换为具体模型（commit 32c5018） |
| 2026-09-04 | 层级反转：coding-plan 套餐优先 → 免费 → GLM → deepseek 兜底（commit a32b23c） |
| 2026-09-04 | 初始化（commit a0fa618） |
