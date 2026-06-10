# Token Watcher

> AI 对话 Token 监控分析工具。零配置自动采集，看一眼就知道钱花哪了。

**版本**: v1.4.0 · 最后更新: 2026-06-10

---

## 快速开始

### 安装

```bash
cd ~/.openclaw/workspace/skills/token-watcher
bash install.sh         # Linux/macOS
# 或双击 install.bat    # Windows
```

### 启动

```bash
# 启动 Web Dashboard（自动采集 + 定时刷新）
token-watcher dashboard

# 打开浏览器访问 http://localhost:8100
```

> ⚠️ 如果 `token-watcher` 命令找不到，请重启终端或手动执行：
> ```bash
> export PATH="$PATH:$HOME/.local/bin"
> ```

---

## 解决什么问题

AI 编程对话中普遍存在的 **"高输入低输出"** token 浪费：

| 场景 | 表现 |
|------|------|
| 长对话不关闭 | 每次提问都把几天前的代码重新加载 |
| 大段代码反复粘贴 | 同样的代码出现在上下文里 3-4 次 |
| 不合适的模型 | 回答一句话的问题却用了最贵的模型 |
| 无上限配置 | 输出被 max_tokens 截断，对话变白痴 |

Token Watcher 帮你把这些浪费**可视化**，然后给出**精准建议**。

---

## 支持的范围

| 使用方式 | 支持情况 | 操作 |
|---------|---------|------|
| 飞书/Telegram/Discord → OpenClaw | ✅ 自动采集 | 零配置 |
| CLI/Python 调 API | ✅ 代理模式 | 改一次地址 |
| 浏览器打开 DeepSeek/ChatGPT | 🚧 浏览器扩展 | 待实现 |
| IDE 内置 AI（CodeArts/JetBrains） | ❌ 不支持 | — |

> **零配置自动采集**的是第一行。如果你只用飞书/Telegram/Discord 等渠道，装完就能用。**API 代理模式**已实现，适用于 Python/curl 直接调 API 的场景。

---

## Dashboard 功能速览

| 区域 | 看什么 |
|------|--------|
| 📊 总览 | 累计输入/输出 token、总费用、各来源占比 |
| 💡 智能建议 | **自动分析每条对话，告诉你哪里浪费了，怎么省** |
| 📋 对话列表 | 所有对话按时间排序，可搜索、按来源过滤 |
| 📉 趋势图 | 每日 token 用量曲线 |
| 🎯 来源分布 | 各渠道的 token 占比（饼图） |
| ⚠️ 浪费排查 | 输入/输出比 > 3 的高浪费对话 |
| 📄 导出报告 | 一键导出 HTML 离线报告 |

---

## 多人部署指南

每个人在自己的机器上部署 OpenClaw + 渠道后，按以下步骤配 token-watcher：

### 1. 安装

```bash
cd ~/.openclaw/workspace/skills/token-watcher
bash install.sh
```

### 2. 改端口（避免冲突）

同一台机器上多人都用，或端口 8100 已被占用时：

```bash
token-watcher dashboard --port 8101
```

### 3. 改数据库路径

每个人用不同的数据库文件，数据不串：

```bash
token-watcher dashboard --db ~/my_token_watcher.db
```

### 4. 后台运行（长期监控）

```bash
# Linux/macOS - nohup 方式
nohup token-watcher dashboard --port 8101 > tw.log 2>&1 &

# 或使用 screen/tmux
screen -S token-watcher
token-watcher dashboard --port 8101
# Ctrl+A D 分离
```

### 5. 配防火墙/安全组

如果想让其他人也能访问你的 Dashboard：

```bash
# 默认只监听本机，改为主机 IP 就能被局域网访问
token-watcher dashboard --port 8100
# 然后在浏览器访问 http://你的IP:8100
```

> Dashboard 默认需要令牌才能访问。令牌在 `src/config.py` 的 `dashboard_token` 字段，默认是 `tw2026`。
> 在启动命令中加入 `?token=tw2026` 即可：
> ```
> http://localhost:8100?token=tw2026
> ```

---

## 全部命令

```bash
# Dashboard（最常用，自动采集 + 实时刷新）
token-watcher dashboard                       # 默认端口 8100
token-watcher dashboard --port 8101            # 指定端口
token-watcher dashboard --db ~/my.db          # 指定数据库

# 一次性操作
token-watcher collect    # 手动采集一次
token-watcher stats      # 终端打印统计
token-watcher report     # 生成离线 HTML 报告

# API 代理模式（用于 CLI/Python 调 API 场景）
token-watcher proxy                           # 启动代理
token-watcher proxy --port 8090               # 指定代理端口
token-watcher proxy --upstream https://api.deepseek.com
```

---

## 智能建议规则

Dashboard 内置智能分析引擎，从多个维度自动诊断每条对话，给出针对性建议。

### 基础规则（v1.1）

| 规则 | 触发条件 | 建议 |
|------|---------|------|
| 🔴 上下文浪费 | 输入/输出比 > 3 且输出 < 1K | 开启新会话、减少历史累积 |
| 🟡 输出接近上限 | 输出 > 模型 max_tokens × 85% | 上调 max_tokens 参数 |
| 🟡 上下文溢出风险 | 输入 > 模型 context_window × 70% | 精简 system prompt、拆分任务 |
| 🔵 模型不匹配 | 高价值模型用于 < 500 token 小任务 | 切换更便宜的模型 |
| 🔵 深度会话 | 对话 > 10 轮且比例 > 2 | 拆分多个专注短会话 |

### 多维建议引擎（v1.2 新增）

v1.2 将分析维度扩展为 4 个方向，覆盖更全面的浪费场景：

**维度 A — 输入质量**
- 单条消息平均 token 超过阈值 → 提示精简消息
- 前 3 轮输入占比过高 → 提示初始 prompt 过于冗长

**维度 B — 上下文管理**
- system prompt 占比超过 25% → 提示精简系统提示词
- 推理模型 thinking/output 比例 > 2 → 提示开启简短模式
- 用户发言过多无 AI 回复 → 提示模型未返回完整内容
- user/assistant 轮次严重失衡 → 提示对话结构异常

**维度 C — 模型配置**
- 输出可能被 max_tokens 整除截断 → 提示检查 max_tokens 配置

**维度 D — 会话生命周期**
- 僵尸会话（7 天未用但占 50K+ token） → 建议清理存档
- 30 天内会话碎片化超过 20 个 → 建议聚焦长对话，减少频繁新建

每条建议标注严重度（critical / warning / info）、预估月节省金额、具体操作指引。

---

## 常见问题

**Q: 报 `ModuleNotFoundError: No module named 'src'`**
A: 确保在技能目录下运行：`cd ~/.openclaw/workspace/skills/token-watcher`

**Q: 安装 tiktoken 报错**
A: Windows 用户可能需要安装 Microsoft C++ Build Tools。或者直接跳过 pip：
```bash
pip install tiktoken --no-deps
```
缺失功能不影响核心采集，只是 token 估算精度下降。

**Q: Dashboard 没有数据**
A: 确保你已经通过 OpenClaw 完成过至少一次对话。首次对话后，运行 `token-watcher collect` 手动采集一次。

**Q: 端口被占用**
A: 加上 `--port 8101`（或其他未占用的端口）。

**Q: 怎么停止 Dashboard**
A: 按 `Ctrl+C`。

---

## 架构

```
   ┌─────────────────────┐       ┌──────────────────┐
   │ OpenClaw 会话文件   │       │ API 代理服务器   │
   │ ~/.openclaw/agents/ │       │ (拦截请求/响应)  │
   │  main/sessions/*.   │       │                  │
   │       jsonl         │       │                  │
   └──────────┬──────────┘       └────────┬─────────┘
              │                            │
              ▼                            ▼
   ┌─────────────────────────────────────────────┐
   │              SQLite 数据库                   │
   │     (conversations + messages + cache读)     │
   └─────────────────┬───────────────────────────┘
                     │
            ┌────────┴────────┬──────────────┐
            ▼                 ▼              ▼
      ┌──────────┐    ┌────────────┐   ┌──────────┐
      │Dashboard │    │ 统计分析  │   │ HTML     │
      │(Web)     │    │ (CLI)     │   │ 报告     │
      └──────────┘    └────────────┘   └──────────┘
```

## 技术说明

- **OpenClaw 渠道**：直接扫描 `~/.openclaw/agents/main/sessions/` 目录下的 `.jsonl` 会话文件，逐行解析 transcript 中的 `usage` 字段（input/cacheRead/output），不再依赖 `openclaw sessions` CLI 命令
- **Token 计费公式**：按 DeepSeek 公式 `input + cacheRead × 0.5 + output` 计算，费用估算更精准
- **API 代理**：启动后拦截发往大模型 API 的请求，自动记录 token 消耗；支持自定义上游地址（`--upstream`）
- **准确度**：全部为真实 token（直接从 API 返回的 `usage` 字段提取），数据库中 `accuracy` 恒为 `"real"`
- **数据库**：SQLite，文件路径默认 `token_watcher.db`，可通过 `--db` 参数指定
- **启动脚本**：一键安装后生成 `token-watcher` 命令，无需手动 cd 到技能目录

---

## 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.4.0 | 2026-06-10 | 采集器重构：从 CLI 模式改为直接扫描 JSONL 会话文件，新增缓存读取统计、API 调用计数、DeepSeek 计费公式 |
| v1.3.0 | 2026-06-01 | README 补全：版本标注、多维建议说明、架构图更新 |
| v1.2.0 | 2026-05-27 | 多维建议引擎（4 维度分析）、API 代理模式实现 |
| v1.1.0 | 2026-05-27 | 智能建议引擎（5 条基础规则）、Dashboard 建议面板 |
| v1.0.0 | 2026-05-26 | 初始版本：自动采集 + Dashboard + 统计报告 |
