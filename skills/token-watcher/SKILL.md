# token-watcher 技能说明

## 技能名称
token-watcher — Token 监控分析工具

## 功能
自动捕获 AI 对话的输入/输出 token 消耗，统计分析浪费场景，通过 Web Dashboard 和 HTML 报告展示。

## 触发方式
```bash
# 启动 Dashboard（含自动采集）
python3 -m src.main dashboard

# 命令行查看统计
python3 -m src.main stats

# 生成离线 HTML 报告
python3 -m src.main report
```

## 数据流
```
OpenClaw sessions API → 采集器 → SQLite 数据库
                                      ↓
                            统计分析 → Web Dashboard
                                      ↓
                            报告生成 → HTML 报告
```

## 输出
- Web Dashboard: `http://localhost:8080`
- HTML 报告: `token_report.html`

## 依赖
- tiktoken (token 计数)
- SQLite (数据库，Python 内置)
- Chart.js (图表，CDN 加载)
