"""Token Watcher — CLI 入口和调度器。

使用方式：
  token-watcher dashboard   启动 Web Dashboard
  token-watcher collect     手动采集一次
  token-watcher report      生成 HTML 报告
  token-watcher proxy       启动 API 代理服务器
  token-watcher stats       查看统计摘要
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from .config import config
from .database import Database
from .collector.openclaw import OpenClawCollector
from .reporter.html_report import HtmlReportGenerator
from .analyzer.advisor import analyze as analyze_sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("token-watcher")


class DashboardHandler(BaseHTTPRequestHandler):
    """Dashboard HTTP 请求处理器。"""

    db: Database = None  # type: ignore[assignment]
    report_generator: HtmlReportGenerator = None  # type: ignore[assignment]

    def _check_auth(self) -> bool:
        """检查访问令牌。"""
        token = config.dashboard_token
        if not token:
            return True
        # 从查询参数获取
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        if qs.get("token", [""])[0] == token:
            return True
        # 从 Authorization header 获取
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and auth[7:] == token:
            return True
        return False

    def _require_auth(self) -> None:
        """返回 401 要求认证。"""
        self.send_response(401)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            ("<html><body style='font-family:sans-serif;padding:40px;"
             "text-align:center;margin-top:80px;'>"
             "<h2 style='color:#e85418;'>🔒 Token Watcher</h2>"
             "<p style='color:#787878;'>需要访问令牌</p>"
             "<form method='get' action='/'>"
             "<input name='token' type='password' placeholder='输入访问令牌' "
             "style='padding:8px 12px;border:1px solid #ddd;border-radius:4px;"
             "width:240px;font-size:14px;'>"
             "<button type='submit' style='padding:8px 20px;background:#e85418;"
             "color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;"
             "margin-left:8px;'>进入</button>"
             "</form></body></html>"
            ).encode("utf-8")
        )

    def do_GET(self) -> None:
        if not self._check_auth():
            self._require_auth()
            return
        from urllib.parse import urlparse
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._serve_dashboard()
        elif path == "/api/data":
            self._serve_api_data()
        elif path == "/api/export":
            self._serve_export()
        elif self.path.startswith("/static/"):
            self._serve_static()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _serve_dashboard(self) -> None:
        template = os.path.join(
            os.path.dirname(__file__), "..", "templates", "dashboard.html"
        )
        if os.path.isfile(template):
            with open(template, "rb") as f:
                content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Dashboard template not found")

    def _serve_api_data(self) -> None:
        try:
            data = self._build_api_data()
            body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            logger.error("API 数据生成失败: %s", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _serve_export(self) -> None:
        try:
            data = self._build_api_data()
            output_path = os.path.join(os.getcwd(), "token_report.html")
            self.report_generator.generate(
                stats=data["stats"],
                conversations=data["conversations"],
                daily_trends=data["daily_trends"],
                waste_list=data["waste_list"],
                source_breakdown=data["source_breakdown"],
                output_path=output_path,
            )
            with open(output_path, "rb") as f:
                content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="token_report.html"')
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
        except Exception as e:
            logger.error("导出失败: %s", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _serve_static(self) -> None:
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def _build_api_data(self) -> dict[str, Any]:
        convs = self.db.list_conversations(limit=500)
        daily_trends = self.db.get_daily_trends(days=30)
        waste_list = self.db.get_high_waste_conversations(
            threshold=config.waste_ratio_threshold
        )
        source_breakdown = self.db.get_source_breakdown()
        stats = self.db.get_total_stats()
        # 智能分析：对会话执行规则引擎，注入 recommendations
        try:
            analyzed = analyze_sessions(
                convs,
                pricing_map=config.model_pricing,
                waste_threshold=config.waste_ratio_threshold,
            )
        except Exception as e:
            logger.warning("智能分析失败（降级）: %s", e)
            analyzed = convs
        return {
            "stats": stats,
            "conversations": analyzed,
            "daily_trends": daily_trends,
            "waste_list": waste_list,
            "source_breakdown": source_breakdown,
            "recommendations_summary": self._build_recommendations_summary(
                analyzed
            ),
        }

    @staticmethod
    def _build_recommendations_summary(
        analyzed: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """汇总所有会话的建议，按维度+严重度分组统计。

        Returns:
            {
              "groups": {"input_quality": [...], "context_management": [...], ...},
              "by_severity": {"critical": N, "warning": N, "info": N},
              "total": N
            }
        """
        grouped: dict[str, list[dict]] = {}
        by_severity: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
        total = 0
        for conv in analyzed:
            for rec in conv.get("recommendations", []):
                dim = rec.get("dimension", "unknown")
                if dim not in grouped:
                    grouped[dim] = []
                item = {
                    "session_title": (conv.get("title", "") or "")[:60],
                    "session_id": conv.get("id", ""),
                    "model": conv.get("model", ""),
                    **rec,
                }
                grouped[dim].append(item)
                sev = rec.get("severity", "info")
                if sev in by_severity:
                    by_severity[sev] += 1
                total += 1
        return {"groups": grouped, "by_severity": by_severity, "total": total}

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("HTTP: %s", format % args)


def cmd_collect(db: Database) -> list[dict[str, Any]]:
    """执行一次采集。"""
    collector = OpenClawCollector(
        history_days=config.openclaw_history_days,
        session_limit=config.openclaw_session_limit,
    )
    logger.info("开始采集 OpenClaw 会话...")
    convs = collector.collect()
    logger.info("采集到 %d 个会话", len(convs))

    saved = 0
    for conv in convs:
        try:
            existing = db.get_conversation(conv["id"])
            if existing:
                # 已存在 → 更新（source_id 匹配）
                if existing.get("source_id") == conv.get("source_id"):
                    db.upsert_conversation(conv)
                    saved += 1
            else:
                db.upsert_conversation(conv)
                saved += 1
        except Exception as e:
            logger.warning("保存会话失败 %s: %s", conv.get("id"), e)

    logger.info("已保存 %d / %d 个会话", saved, len(convs))
    return convs


def cmd_dashboard(db: Database) -> None:
    """启动 Web Dashboard 并持续采集。"""
    DashboardHandler.db = db
    DashboardHandler.report_generator = HtmlReportGenerator()

    # 先采集一次
    cmd_collect(db)

    # 启动 HTTP 服务
    server = HTTPServer(
        (config.dashboard_host, config.dashboard_port),
        DashboardHandler,
    )
    logger.info("Dashboard: http://%s:%s", config.dashboard_host,
                config.dashboard_port)

    # 轮询采集（后台线程）
    import threading

    def poll_loop() -> None:
        while True:
            time.sleep(config.openclaw_poll_interval_sec)
            try:
                cmd_collect(db)
            except Exception as e:
                logger.error("轮询采集失败: %s", e)

    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Dashboard 已停止")
        server.shutdown()


def cmd_report(db: Database, output: str) -> None:
    """生成 HTML 报告。"""
    cmd_collect(db)  # 先采集最新数据
    convs = db.list_conversations(limit=500)
    daily = db.get_daily_trends(days=30)
    waste = db.get_high_waste_conversations(config.waste_ratio_threshold)
    sources = db.get_source_breakdown()
    stats = db.get_total_stats()

    gen = HtmlReportGenerator()
    path = gen.generate(
        stats=stats,
        conversations=convs,
        daily_trends=daily,
        waste_list=waste,
        source_breakdown=sources,
        output_path=output,
    )
    logger.info("报告已生成: %s", path)


def cmd_stats(db: Database) -> None:
    """打印统计摘要到终端。"""
    cmd_collect(db)
    convs = db.list_conversations(limit=500)
    stats = db.get_total_stats()

    total_in = stats.get("total_input", 0)
    total_out = stats.get("total_output", 0)
    ratio = round(total_in / total_out, 2) if total_out > 0 else 0

    print()
    print("=" * 50)
    print("  📊 Token Watcher 统计摘要")
    print("=" * 50)
    print(f"  对话总数:     {stats.get('total_conversations', 0)}")
    print(f"  消息总数:     {stats.get('total_messages', 0)}")
    print(f"  总输入 Token: {total_in:,}")
    print(f"  总输出 Token: {total_out:,}")
    print(f"  输入/输出比:  {ratio}x")
    print(f"  预估费用:     ${stats.get('total_cost', 0):.4f}")
    print("-" * 50)

    if convs:
        print("\n  📋 最近对话:")
        for c in convs[:10]:
            ratio_c = c.get("input_output_ratio", 0)
            marker = " ⚠️" if ratio_c > config.waste_ratio_threshold else ""
            print(f"    {c.get('title','')[:40]:40s} "
                  f"输入:{str(c.get('total_input_tokens',0)):>8s} "
                  f"输出:{str(c.get('total_output_tokens',0)):>8s} "
                  f"比例:{ratio_c}{marker}")
    print()


def cmd_proxy(db: Database) -> None:
    """启动 API 代理服务器。

    支持多端口监听，每个端口对应一个渠道来源。
    使用 asyncio 事件循环运行 aiohttp 服务器。
    """
    from .proxy.server import MultiPortProxyServer

    async def _run() -> None:
        proxy = MultiPortProxyServer(db)
        ports = await proxy.start()

        port_info = ", ".join(
            f"{p}→{config.proxy_port_mappings.get(p, 'default')}"
            for p in ports
        )
        print()
        print("=" * 56)
        print("  🌐 Token Watcher API Proxy")
        print("=" * 56)
        print(f"  上游:     {config.proxy_upstream_url}")
        print(f"  监听端口: {port_info}")
        print(f"  Health:   http://localhost:{ports[0]}/health")
        print()
        print("  📡 客户端将 API 地址改为代理地址即可截获用量")
        print("  按 Ctrl+C 停止")
        print("-" * 56)

        # 保持运行
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await proxy.stop()
            print()
            logger.info("代理服务器已停止")

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("代理服务器已停止")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Token Watcher — AI 对话 Token 监控分析工具",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["dashboard", "collect", "report", "stats", "proxy"],
        default="dashboard",
        help="子命令",
    )
    parser.add_argument("--output", "-o", default="token_report.html",
                        help="报告输出路径 (用于 report 命令)")
    parser.add_argument("--db", default=config.db_path,
                        help="数据库路径")
    parser.add_argument("--port", type=int, default=config.dashboard_port,
                        help="Dashboard 端口")
    parser.add_argument("--proxy-port", type=int, default=config.proxy_port,
                        help="代理端口")
    parser.add_argument("--upstream", default=config.proxy_upstream_url,
                        help="上游 API 地址")
    parser.add_argument("--map-port", action="append", default=None,
                        help="端口映射，格式: port=channel (可多次指定)")

    args = parser.parse_args()

    # 更新配置
    config.db_path = args.db
    config.dashboard_port = args.port
    config.proxy_port = args.proxy_port
    config.proxy_upstream_url = args.upstream

    # 处理端口映射
    if args.map_port:
        mappings = {}
        for mapping in args.map_port:
            if "=" in mapping:
                port_str, channel = mapping.split("=", 1)
                try:
                    mappings[int(port_str)] = channel
                except ValueError:
                    logger.warning("无效端口映射: %s", mapping)
            else:
                logger.warning("无效端口映射格式 (期望 port=channel): %s", mapping)
        if mappings:
            config.proxy_port_mappings = mappings

    db = Database(config.db_path)

    try:
        if args.command == "dashboard":
            cmd_dashboard(db)
        elif args.command == "collect":
            cmd_collect(db)
        elif args.command == "report":
            cmd_report(db, args.output)
        elif args.command == "stats":
            cmd_stats(db)
        elif args.command == "proxy":
            cmd_proxy(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
