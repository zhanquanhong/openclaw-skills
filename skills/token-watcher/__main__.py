"""token-watcher — AI 对话 Token 监控分析工具。

使用方式：
  token-watcher dashboard    启动 Web Dashboard
  token-watcher collect      手动采集一次
  token-watcher report       生成 HTML 报告
  token-watcher stats        查看统计摘要
"""

from src.main import main

if __name__ == "__main__":
    main()
