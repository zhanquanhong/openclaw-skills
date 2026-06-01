"""HTML 报告生成器。"""

import json
import os
from datetime import datetime
from typing import Any


class HtmlReportGenerator:
    """生成 HTML 格式的 Token 监控报告。"""

    def __init__(self) -> None:
        self.template_dir = os.path.join(os.path.dirname(__file__),
                                         "..", "..", "templates")

    def generate(self, stats: dict[str, Any],
                 conversations: list[dict[str, Any]],
                 daily_trends: list[dict[str, Any]],
                 waste_list: list[dict[str, Any]],
                 source_breakdown: list[dict[str, Any]],
                 output_path: str = "token_report.html") -> str:
        """生成完整 HTML 报告。

        Args:
            stats: 全局统计
            conversations: 会话列表
            daily_trends: 每日趋势
            waste_list: 高浪费对话
            source_breakdown: 来源分布
            output_path: 输出文件路径

        Returns:
            实际输出路径
        """
        # 准备 JSON 数据（嵌入 HTML）
        data_json = json.dumps({
            "stats": stats,
            "conversations": conversations,
            "daily_trends": daily_trends,
            "waste_list": waste_list,
            "source_breakdown": source_breakdown,
        }, ensure_ascii=False, default=str)

        ratio = 0
        total_out = stats.get("total_output", 0)
        total_in = stats.get("total_input", 0)
        if total_out > 0:
            ratio = round(total_in / total_out, 2)

        html = self._build_html(data_json, stats, ratio, waste_list, conversations)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _build_html(self, data_json: str, stats: dict[str, Any],
                    ratio: float,
                    waste_list: list[dict[str, Any]] | None = None,
                    conversations: list[dict[str, Any]] | None = None) -> str:
        """构建完整 HTML。"""
        waste_list = waste_list or []
        conversations = conversations or []
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token 监控报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
          background:#f5f5f5; color:#333; padding:20px; }}
  .container {{ max-width:1200px; margin:0 auto; }}
  h1 {{ font-size:24px; color:#e85418; margin-bottom:5px; }}
  .subtitle {{ color:#787878; font-size:14px; margin-bottom:20px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
            gap:16px; margin-bottom:24px; }}
  .card {{ background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .card .label {{ font-size:12px; color:#787878; margin-bottom:4px; }}
  .card .value {{ font-size:28px; font-weight:700; color:#484848; }}
  .card .value.red {{ color:#e85418; }}
  .card .value.green {{ color:#45bf82; }}
  .card .value.blue {{ color:#5ac2ff; }}
  section {{ background:#fff; border-radius:8px; padding:20px; margin-bottom:20px;
             box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  section h2 {{ font-size:16px; color:#e85418; margin-bottom:16px;
                padding-bottom:8px; border-bottom:2px solid #f8e8e0; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; padding:8px 12px; background:#f8e8e0; color:#484848; font-weight:600; }}
  td {{ padding:8px 12px; border-bottom:1px solid #eee; vertical-align:top; }}
  tr:hover {{ background:#fcf8f0; }}
  .ratio-high {{ color:#e85418; font-weight:700; }}
  .charts {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .chart-container {{ position:relative; height:250px; }}
  .badge-real {{ background:#45bf82; color:#fff; padding:2px 6px; border-radius:4px; font-size:11px; }}
  .badge-estimated {{ background:#fdbe31; color:#484848; padding:2px 6px; border-radius:4px; font-size:11px; }}
  .waste-tip {{ background:#fff8e8; border-left:4px solid #fdbe31; padding:12px; margin:8px 0; font-size:13px; }}
  .ctx-tag {{ display:inline-block; background:#f8e8e0; color:#e85418; padding:1px 6px;
              border-radius:3px; font-size:11px; margin-right:4px; }}
  .ctx-tag.info {{ background:#e8f4ff; color:#5ac2ff; }}
  .first-msg {{ max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .first-msg:hover {{ overflow:visible; white-space:normal; word-break:break-all; }}
  .last-msg {{ font-size:11px; color:#989898; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:320px; }}
  @media (max-width:768px) {{ .charts {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 Token 监控报告</h1>
  <p class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

  <div class="cards">
    <div class="card">
      <div class="label">总输入 Token</div>
      <div class="value blue">{self._fmt(stats.get('total_input', 0))}</div>
    </div>
    <div class="card">
      <div class="label">总输出 Token</div>
      <div class="value green">{self._fmt(stats.get('total_output', 0))}</div>
    </div>
    <div class="card">
      <div class="label">输入/输出比例</div>
      <div class="value red">{ratio}x</div>
    </div>
    <div class="card">
      <div class="label">预估费用</div>
      <div class="value red">${stats.get('total_cost', 0):.4f}</div>
    </div>
    <div class="card">
      <div class="label">对话总数</div>
      <div class="value">{stats.get('total_conversations', 0)}</div>
    </div>
    <div class="card">
      <div class="label">消息总数</div>
      <div class="value">{stats.get('total_messages', 0)}</div>
    </div>
  </div>

  <section>
    <h2>📈 每日 Token 趋势</h2>
    <div class="charts">
      <div class="chart-container"><canvas id="trendChart"></canvas></div>
      <div class="chart-container"><canvas id="sourceChart"></canvas></div>
    </div>
  </section>

  <section>
    <h2>⚠️ 高浪费对话 (输入/输出比例 > 3)</h2>
    {self._render_waste_table(waste_list)}
    <div class="waste-tip">
      💡 <strong>优化建议：</strong>高浪费对话通常由大量历史上下文累积导致。适时开启新会话、
      精简粘贴的代码段、避免重复提问，可有效降低输入 token 消耗。
    </div>
  </section>

  <section>
    <h2>📋 全部对话</h2>
    {self._render_conv_table(conversations)}
  </section>
</div>

<script>
const DATA = {data_json};

// 每日趋势图
const trendCtx = document.getElementById('trendChart').getContext('2d');
new Chart(trendCtx, {{
  type: 'bar',
  data: {{
    labels: DATA.daily_trends.map(d => d.day?.slice(5) || ''),
    datasets: [
      {{ label:'输入', data:DATA.daily_trends.map(d=>d.input_tokens), backgroundColor:'#5ac2ff' }},
      {{ label:'输出', data:DATA.daily_trends.map(d=>d.output_tokens), backgroundColor:'#45bf82' }}
    ]
  }},
  options: {{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'bottom' }} }},
    scales:{{ y:{{ beginAtZero:true, title:{{ display:true, text:'Tokens' }} }} }}
  }}
}});

// 来源分布图
const srcCtx = document.getElementById('sourceChart').getContext('2d');
const COLORS = ['#e85418','#5ac2ff','#45bf82','#fdbe31'];
new Chart(srcCtx, {{
  type: 'doughnut',
  data: {{
    labels: DATA.source_breakdown.map(s => s.source + ' (' + s.count + ')'),
    datasets: [{{ data:DATA.source_breakdown.map(s=>s.input_tokens),
                  backgroundColor: COLORS.slice(0, DATA.source_breakdown.length) }}]
  }},
  options: {{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'bottom' }} }}
  }}
}});
</script>
</body>
</html>"""

    def _format_context_tags(self, conv: dict[str, Any]) -> str:
        """生成对话上下文的标签 HTML。

        从 context_info 中提取轮次、时长、内容量等信息展示为标签。

        Args:
            conv: 会话数据字典

        Returns:
            标签 HTML 字符串
        """
        ctx_str = conv.get("context_info", "{}")
        if isinstance(ctx_str, str):
            try:
                ctx = json.loads(ctx_str) if ctx_str else {}
            except (json.JSONDecodeError, TypeError):
                ctx = {}
        else:
            ctx = ctx_str or {}

        tags = []

        # 轮次（按用户/AI 分别展示）
        ut = ctx.get("user_turns", 0)
        at = ctx.get("assistant_turns", 0)
        if ut > 0:
            tags.append(f'<span class="ctx-tag">用户 {ut} 次</span>')
            tags.append(f'<span class="ctx-tag info">AI {at} 条</span>')
        elif at > 0:
            tags.append(f'<span class="ctx-tag">共 {at} 条消息</span>')

        # 时长
        ts_start = ctx.get("time_start")
        ts_end = ctx.get("time_end")
        if ts_start and ts_end:
            try:
                t1_str = str(ts_start).replace("Z", "+00:00")
                t2_str = str(ts_end).replace("Z", "+00:00")
                t1 = datetime.fromisoformat(t1_str)
                t2 = datetime.fromisoformat(t2_str)
                delta_min = int((t2 - t1).total_seconds() / 60)
                if delta_min >= 60:
                    tags.append(f'<span class="ctx-tag">{delta_min // 60}h</span>')
                elif delta_min > 0:
                    tags.append(f'<span class="ctx-tag">{delta_min} 分钟</span>')
            except (ValueError, TypeError):
                pass

        # 内容量
        tc = ctx.get("total_chars", 0)
        if tc > 0:
            if tc >= 10000:
                tags.append(f'<span class="ctx-tag">{tc // 1000}K 字符</span>')
            elif tc >= 1000:
                tags.append(f'<span class="ctx-tag">{tc / 1000:.1f}K 字符</span>')
            else:
                tags.append(f'<span class="ctx-tag">{tc} 字符</span>')

        return " ".join(tags)

    def _format_last_msg(self, conv: dict[str, Any]) -> str:
        """提取最后一条用户消息。

        Args:
            conv: 会话数据字典

        Returns:
            最后消息的 HTML 字符串
        """
        ctx_str = conv.get("context_info", "{}")
        if isinstance(ctx_str, str):
            try:
                ctx = json.loads(ctx_str) if ctx_str else {}
            except (json.JSONDecodeError, TypeError):
                ctx = {}
        else:
            ctx = ctx_str or {}
        msg = ctx.get("last_msg", "")
        if not msg:
            return ""
        short = msg[:80] + "…" if len(msg) > 80 else msg
        return f'<div class="last-msg" title="{self._escape(msg)}">最后: {self._escape(short)}</div>'

    def _render_waste_table(self, waste_list: list[dict[str, Any]]) -> str:
        if not waste_list:
            return '<p style="color:#45bf82;">✅ 暂无高浪费对话</p>'
        rows = "".join(
            f"<tr>"
            f"<td>{self._fmt_time(c.get('start_time',''))}</td>"
            f"<td style='font-size:11px;color:#989898;font-family:monospace'>{self._short_id(c.get('id',''))}</td>"
            f"<td><div class='first-msg' title='{self._escape(c.get('title',''))}'>{self._escape(c.get('title','')[:100])}</div>"
            f"{self._format_context_tags(c)}</td>"
            f"<td>{self._fmt(c.get('total_input_tokens',0))}</td>"
            f"<td>{self._fmt(c.get('total_output_tokens',0))}</td>"
            f"<td class='ratio-high'>{c.get('input_output_ratio',0)}x</td>"
            f"<td><span class='badge-{c.get('accuracy','estimated')}'>{c.get('accuracy','')}</span></td>"
            f"</tr>"
            for c in waste_list
        )
        return f"""<table><thead><tr>
<th>时间</th><th>会话ID</th><th>对话首句</th><th>输入 Token</th><th>输出 Token</th><th>比例</th><th>精度</th>
</tr></thead><tbody>{rows}</tbody></table>"""

    def _render_conv_table(self, conversations: list[dict[str, Any]]) -> str:
        if not conversations:
            return "<p>暂无对话数据</p>"
        rows = "".join(
            f"<tr>"
            f"<td>{self._fmt_time(c.get('start_time',''))}</td>"
            f"<td style='font-size:11px;color:#989898;font-family:monospace'>{self._short_id(c.get('id',''))}</td>"
            f"<td><div class='first-msg' title='{self._escape(c.get('title',''))}'>{self._escape(c.get('title','')[:100])}</div>"
            f"{self._format_context_tags(c)}{self._format_last_msg(c)}</td>"
            f"<td>{self._fmt(c.get('total_input_tokens',0))}</td>"
            f"<td>{self._fmt(c.get('total_output_tokens',0))}</td>"
            f"<td>{c.get('input_output_ratio',0)}x</td>"
            f"<td>${c.get('cost_estimate',0):.4f}</td>"
            f"</tr>"
            for c in conversations
        )
        return f"""<table><thead><tr>
<th>时间</th><th>会话ID</th><th>对话首句</th><th>输入</th><th>输出</th><th>比例</th><th>费用</th>
</tr></thead><tbody>{rows}</tbody></table>"""

    @staticmethod
    def _short_id(id_str: Any) -> str:
        """缩短会话 ID 显示（去掉 openclaw_ 前缀）。"""
        s = str(id_str) if id_str else ""
        return s.replace("openclaw_", "")

    @staticmethod
    def _escape(s: Any) -> str:
        """HTML 转义。"""
        s = str(s) if s is not None else ""
        return (s.replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
                  .replace('"', "&quot;"))

    @staticmethod
    def _fmt(n: Any) -> str:
        n = int(n) if n else 0
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)

    @staticmethod
    def _fmt_time(ts: Any) -> str:
        if not ts:
            return "-"
        s = str(ts)
        return s[:16] if len(s) > 16 else s
