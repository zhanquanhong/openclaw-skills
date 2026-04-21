# -*- coding: utf-8 -*-
"""验证规则定义 - 生产级"""

import re
from typing import Dict, List, Any, Optional

# 任务类型标记
TASK_TYPES = {
    "🆕": "新增",
    "🔄": "优化",
    "♻️": "复用",
    "🗑️": "删除",
    "🔗": "对接",
    "新增": "新增",
    "优化": "优化",
    "复用": "复用",
    "删除": "删除",
    "对接": "对接",
}

# 必填项检查规则
REQUIRED_CHECKS = [
    "task_type",       # 任务类型标记
    "dependencies",    # 依赖关系
    "api_definition",  # 接口定义完整性
    "implementation",  # 实现说明具体性
    "acceptance_criteria",  # 验收标准可执行性
]

# 加分项检查规则
BONUS_CHECKS = [
    "effort",      # 工作量评估
    "priority",    # 优先级标注
    "background",  # 业务背景
]


class RuleEngine:
    """规则引擎 - 生产级"""
    
    def __init__(self, tech_stack: str = "java"):
        self.tech_stack = tech_stack
    
    def check_task_type(self, content: str) -> Dict[str, Any]:
        """检查任务类型标记"""
        for mark in TASK_TYPES.keys():
            if mark in content:
                return {
                    "passed": True,
                    "value": mark,
                    "message": f"任务类型标记清晰 ({mark}{TASK_TYPES[mark]})"
                }
        return {
            "passed": False,
            "value": None,
            "message": "缺少任务类型标记（🆕/🔄/♻️/🗑️/🔗）"
        }
    
    def check_dependencies(self, content: str) -> Dict[str, Any]:
        """检查依赖关系"""
        patterns = [
            r"\*\*依赖\*\*:\s*(.+)",
            r"依赖 [：:]\s*(.+)",
            r"前置 [任务 | 条件]:\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                return {
                    "passed": True,
                    "value": value,
                    "message": "依赖关系明确"
                }
        return {
            "passed": False,
            "value": None,
            "message": "缺少依赖关系说明"
        }
    
    def check_api_definition(self, content: str) -> Dict[str, Any]:
        """检查接口定义完整性"""
        checks = {
            "url": any(p in content for p in ["URL", "url", "接口地址", "HTTP"]),
            "params": any(p in content for p in ["请求参数", "参数", "入参"]),
            "response": any(p in content for p in ["返回", "响应", "出参"]),
            "error_codes": any(p in content for p in ["错误码", "错误", "errorCode"]),
        }
        
        missing = [k for k, v in checks.items() if not v]
        
        if not missing:
            return {
                "passed": True,
                "value": "完整",
                "message": "接口定义包含 URL/参数/返回/错误码"
            }
        
        return {
            "passed": False,
            "value": f"缺少：{', '.join(missing)}",
            "message": f"接口定义不完整：缺少{', '.join(missing)}"
        }
    
    def check_implementation(self, content: str) -> Dict[str, Any]:
        """检查实现说明具体性"""
        # JAVA 特定路径模式
        java_patterns = [
            r"src/main/java/.+\.java",
            r"src/main/resources/.+\.xml",
            r"src/test/java/.+\.java",
        ]
        
        # 通用文件路径模式
        general_patterns = [
            r"[a-zA-Z0-9_-]+/[^:\n]+\.java",
            r"[a-zA-Z0-9_-]+/[^:\n]+\.py",
            r"[a-zA-Z0-9_-]+/[^:\n]+\.xml",
            r"Controller\.java",
            r"Service\.java",
            r"Mapper\.xml",
        ]
        
        # 检查是否有具体文件路径
        has_path = False
        patterns = java_patterns + general_patterns
        
        for pattern in patterns:
            if re.search(pattern, content):
                has_path = True
                break
        
        # 检查是否有方法名
        has_method = any(p in content for p in ["方法", "method", "()", "(@"])
        
        if has_path and has_method:
            return {
                "passed": True,
                "value": "具体",
                "message": "实现说明精确到文件和方法"
            }
        elif has_path:
            return {
                "passed": True,
                "value": "较具体",
                "message": "实现说明包含文件路径"
            }
        
        return {
            "passed": False,
            "value": None,
            "message": "实现说明不具体（缺少文件路径或方法名）"
        }
    
    def check_acceptance_criteria(self, content: str) -> Dict[str, Any]:
        """检查验收标准可执行性"""
        # 检查是否有验收标准
        patterns = [
            r"验收标准",
            r"验收条件",
            r"Acceptance Criteria",
            r"测试用例",
        ]
        
        has_section = any(p in content for p in patterns)
        
        if not has_section:
            return {
                "passed": False,
                "value": None,
                "message": "缺少验收标准"
            }
        
        # 检查是否有可执行的检查项
        checklist_patterns = [
            r"\[ ]",  # Markdown 复选框
            r"^\s*[-*]\s+",  # 列表项
            r"^\s*\d+\.\s+",  # 编号列表
        ]
        
        has_checklist = False
        for pattern in checklist_patterns:
            if re.search(pattern, content, re.MULTILINE):
                has_checklist = True
                break
        
        # 检查是否有具体指标
        has_metrics = any(p in content for p in ["<", "ms", "QPS", "%", "返回", "错误"])
        
        if has_checklist and has_metrics:
            return {
                "passed": True,
                "value": "可执行",
                "message": "验收标准包含具体检查项和指标"
            }
        elif has_checklist:
            return {
                "passed": True,
                "value": "可执行",
                "message": "验收标准包含检查项"
            }
        
        return {
            "passed": False,
            "value": None,
            "message": "验收标准不可执行（缺少具体检查项或指标）"
        }
    
    def check_effort(self, content: str) -> Dict[str, Any]:
        """检查工作量评估（加分项）"""
        patterns = [
            r"\*\*工作量\*\*:\s*(.+)",
            r"工作量 [：:]\s*(.+)",
            r"(\d+\.?\d*)\s*[人天|天|小时]",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                return {
                    "present": True,
                    "value": value.strip(),
                    "score": 10
                }
        
        return {
            "present": False,
            "value": None,
            "score": 0
        }
    
    def check_priority(self, content: str) -> Dict[str, Any]:
        """检查优先级标注（加分项）"""
        patterns = [
            r"\*\*优先级\*\*:\s*(P[0-2])",
            r"优先级 [：:]\s*(P[0-2])",
            r"(P[0-2])",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return {
                    "present": True,
                    "value": match.group(1),
                    "score": 10
                }
        
        return {
            "present": False,
            "value": None,
            "score": 0
        }
    
    def check_background(self, content: str) -> Dict[str, Any]:
        """检查业务背景（加分项）"""
        patterns = [
            r"业务背景",
            r"需求背景",
            r"背景介绍",
            "Background",
            r"使用场景",
        ]
        
        has_section = any(p in content for p in patterns)
        
        if has_section:
            return {
                "present": True,
                "value": "有业务背景说明",
                "score": 10
            }
        
        return {
            "present": False,
            "value": None,
            "score": 0
        }
