#!/usr/bin/env python3
"""
代码审查多代理协作系统

用法:
    python code-review-multi-agent.py /path/to/project
    python code-review-multi-agent.py --pr 123
    python code-review-multi-agent.py /path/to/file.java --focus security
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import argparse

# 工作区路径
WORKSPACE = Path.home() / ".openclaw" / "workspace"
SCRIPTS_DIR = WORKSPACE / "scripts"
REPORTS_DIR = WORKSPACE / "code-reports"

# 确保报告目录存在
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def run_code_reviewer(target_path: str, focus: str = "all", output_file: str = None):
    """
    调用 code-reviewer 技能进行代码审查
    
    Args:
        target_path: 目标路径（文件或目录）
        focus: 审查焦点 (all/security/style/performance)
        output_file: 输出文件名
    
    Returns:
        报告内容
    """
    reviewer_script = SCRIPTS_DIR / "code-reviewer.py"
    
    if not reviewer_script.exists():
        print(f"❌ 未找到 code-reviewer 脚本：{reviewer_script}")
        return None
    
    # 构建命令
    cmd = [
        sys.executable,
        str(reviewer_script),
        target_path,
        "--output", "markdown"
    ]
    
    # 添加焦点参数
    if focus != "all":
        cmd.extend(["--focus", focus])
    
    # 添加输出文件
    if output_file:
        output_path = REPORTS_DIR / output_file
        cmd.extend(["-o", str(output_path)])
    
    print(f"🔍 执行审查：{' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 分钟超时
        )
        
        if result.returncode == 0:
            print(f"✅ 审查完成")
            if output_file:
                return (REPORTS_DIR / output_file).read_text()
            return result.stdout
        else:
            print(f"❌ 审查失败：{result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"⏰ 审查超时（>5 分钟）")
        return None
    except Exception as e:
        print(f"❌ 执行异常：{e}")
        return None


def spawn_subagent(task: str, label: str, timeout: int = 300):
    """
    通过 OpenClaw sessions_spawn 创建子代理
    
    注意：这个函数需要在 OpenClaw 环境中调用
    实际使用时通过 message 工具发送到主会话
    """
    # 这里只是示例，实际调用需要通过 OpenClaw API
    print(f"🤖 启动子代理 [{label}]: {task}")
    return {"label": label, "status": "running"}


def generate_summary_report(reports: dict, target_path: str):
    """
    生成综合审查报告
    
    Args:
        reports: 各子代理的报告内容
        target_path: 审查目标路径
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    summary = f"""# 🔍 代码审查报告

**审查时间:** {timestamp}  
**审查范围:** {target_path}  

---

## 📊 审查概览

"""
    
    # 添加各子报告摘要
    for label, content in reports.items():
        if content:
            summary += f"### {label.upper()} 审查\n\n"
            # 提取前 500 字作为摘要
            summary += content[:500] + "...\n\n"
        else:
            summary += f"### {label.upper()} 审查\n\n⚠️ 审查失败或无结果\n\n"
    
    # 添加下一步行动
    summary += f"""---

## ✅ 下一步行动

- [ ] 修复严重/高危问题（优先级：高）
- [ ] 优化中危问题（优先级：中）
- [ ] 补充业务逻辑审查（负责人：@老成员）
- [ ] 复查修复结果

---

*报告生成时间：{timestamp}*
*详细报告见：{REPORTS_DIR}*
"""
    
    # 保存综合报告
    summary_file = REPORTS_DIR / "code-review-summary.md"
    summary_file.write_text(summary)
    
    print(f"📄 综合报告已保存：{summary_file}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="代码审查多代理协作系统")
    parser.add_argument("target", nargs="?", help="审查目标（文件/目录路径）")
    parser.add_argument("--pr", type=int, help="审查指定 PR 编号")
    parser.add_argument("--focus", choices=["all", "security", "style", "performance"], 
                       default="all", help="审查焦点")
    parser.add_argument("--output", "-o", help="输出报告文件名")
    parser.add_argument("--multi-agent", action="store_true", 
                       help="启用多代理模式（并行执行）")
    
    args = parser.parse_args()
    
    # 确定审查目标
    target_path = args.target
    if not target_path:
        if args.pr:
            print(f"📝 获取 PR #{args.pr} 变更文件...")
            # TODO: 实现 PR 文件获取逻辑
            target_path = "."
        else:
            target_path = "."
    
    print(f"🎯 审查目标：{target_path}")
    print(f"🔬 审查模式：{'多代理并行' if args.multi_agent else '单代理串行'}")
    
    # 执行审查
    if args.multi_agent:
        # 多代理模式
        print("\n🚀 启动多代理协作审查...")
        
        reports = {}
        
        # 并行启动子代理
        print("\n📡 启动安全审查子代理...")
        reports["security"] = run_code_reviewer(
            target_path, 
            focus="security", 
            output_file="security-report.md"
        )
        
        print("\n📡 启动规范审查子代理...")
        reports["style"] = run_code_reviewer(
            target_path, 
            focus="style", 
            output_file="style-report.md"
        )
        
        print("\n📡 启动性能分析子代理...")
        reports["performance"] = run_code_reviewer(
            target_path, 
            focus="performance", 
            output_file="performance-report.md"
        )
        
        # 生成综合报告
        print("\n📊 生成综合报告...")
        generate_summary_report(reports, target_path)
        
    else:
        # 单代理模式
        print("\n🔍 执行单代理审查...")
        output_file = args.output or "code-review-report.md"
        report = run_code_reviewer(target_path, focus=args.focus, output_file=output_file)
        
        if report:
            print(f"\n✅ 审查完成，报告已保存：{REPORTS_DIR / output_file}")
    
    print("\n✨ 代码审查完成")


if __name__ == "__main__":
    main()
