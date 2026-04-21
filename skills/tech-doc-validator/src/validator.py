# -*- coding: utf-8 -*-
"""核心验证引擎 - 生产级"""

import logging
from typing import Dict, List, Any, Optional
try:
    from .rules import RuleEngine
    from .parser import MarkdownParser
    from .reporter import Reporter
    from .fuzzy_words import get_fuzzy_words
except ImportError:
    from rules import RuleEngine
    from parser import MarkdownParser
    from reporter import Reporter
    from fuzzy_words import get_fuzzy_words

logger = logging.getLogger(__name__)


class TechDocValidator:
    """技术方案验证器 - 生产级"""
    
    def __init__(self, tech_stack: str = "java", config: Optional[Dict] = None):
        self.tech_stack = tech_stack
        self.config = config or {}
        self.rule_engine = RuleEngine(tech_stack)
        self.parser = MarkdownParser()
        self.reporter = Reporter()
        self.fuzzy_words = get_fuzzy_words(tech_stack)
    
    def validate(self, content: str, file_name: str = "未知") -> Dict[str, Any]:
        """验证技术方案文档"""
        logger.info(f"开始验证文档：{file_name}")
        
        try:
            # 解析文档
            parsed = self.parser.parse(content)
            logger.info(f"解析完成：{parsed['task_count']}个任务块，{parsed['char_count']}字符")
            
            # 执行必填项检查
            checks = self._run_required_checks(content)
            
            # 执行加分项检查
            bonus = self._run_bonus_checks(content)
            
            # 计算总分
            score = self._calculate_score(checks, bonus)
            
            # 查找模糊词
            issues = self._find_fuzzy_words(content)
            
            # 添加规则检查问题
            issues.extend(self._generate_issues(checks))
            
            # 生成建议
            suggestions = self._generate_suggestions(checks, bonus)
            
            # 评估是否可生成 WBS
            wbs_ready = score >= 70 and len([i for i in issues if i.get('severity') == 'error']) == 0
            
            # 构建结果
            result = {
                "file_name": file_name,
                "summary": {
                    "score": score,
                    "passed": score >= 70,
                    "total_checks": len(checks),
                    "passed_checks": sum(1 for c in checks.values() if c["passed"]),
                    "issues_count": len(issues),
                    "wbs_ready": wbs_ready
                },
                "checks": checks,
                "bonus": bonus,
                "issues": issues,
                "suggestions": suggestions,
                "evaluation": {
                    "level": self._get_evaluation_level(score),
                    "wbs_ready": wbs_ready,
                    "message": "可生成 WBS" if wbs_ready else "建议修复问题后再生成 WBS"
                }
            }
            
            logger.info(f"验证完成：{score}分，{'通过' if score >= 70 else '不通过'}")
            return result
            
        except Exception as e:
            logger.error(f"验证失败：{e}", exc_info=True)
            raise
    
    def _run_required_checks(self, content: str) -> Dict[str, Any]:
        """执行必填项检查"""
        return {
            "task_type": self.rule_engine.check_task_type(content),
            "dependencies": self.rule_engine.check_dependencies(content),
            "api_definition": self.rule_engine.check_api_definition(content),
            "implementation": self.rule_engine.check_implementation(content),
            "acceptance_criteria": self.rule_engine.check_acceptance_criteria(content),
        }
    
    def _run_bonus_checks(self, content: str) -> Dict[str, Any]:
        """执行加分项检查"""
        return {
            "effort": self.rule_engine.check_effort(content),
            "priority": self.rule_engine.check_priority(content),
            "background": self.rule_engine.check_background(content),
        }
    
    def _calculate_score(self, checks: Dict, bonus: Dict) -> int:
        """计算总分"""
        # 基础分（5 个必填项，每项 14 分，共 70 分）
        base_score = sum(14 for c in checks.values() if c["passed"])
        
        # 加分（3 个加分项，每项 10 分，共 30 分）
        bonus_score = sum(item["score"] for item in bonus.values())
        
        return min(base_score + bonus_score, 100)
    
    def _find_fuzzy_words(self, content: str) -> List[Dict[str, Any]]:
        """查找模糊词"""
        issues = []
        fuzzy_issues = self.parser.find_fuzzy_words(content, self.fuzzy_words)
        
        for issue in fuzzy_issues:
            issues.append({
                "line": issue["line"],
                "type": "vague_language",
                "severity": "warning",
                "text": issue["text"],
                "suggestion": issue["suggestion"],
                "rule": "避免使用模糊词汇"
            })
        
        return issues
    
    def _generate_issues(self, checks: Dict) -> List[Dict[str, Any]]:
        """生成规则检查问题"""
        issues = []
        
        for check_name, check_result in checks.items():
            if not check_result["passed"]:
                issues.append({
                    "line": "?",
                    "type": f"missing_{check_name}",
                    "severity": "error",
                    "text": check_result["message"],
                    "suggestion": self._get_suggestion_for_check(check_name),
                    "rule": f"{check_name}是必填项"
                })
        
        return issues
    
    def _get_suggestion_for_check(self, check_name: str) -> str:
        """获取检查项的修改建议"""
        suggestions = {
            "task_type": "添加任务类型标记（🆕新增/🔄优化/♻️复用/🗑️删除/🔗对接）",
            "dependencies": "说明依赖关系（如：无 / 依赖 1.1 技能列表查询接口）",
            "api_definition": "补充接口定义（URL/请求参数/返回数据/错误码）",
            "implementation": "补充实现说明（文件路径 + 方法名）",
            "acceptance_criteria": "补充验收标准（可执行的检查项）"
        }
        return suggestions.get(check_name, "请补充相关内容")
    
    def _generate_suggestions(self, checks: Dict, bonus: Dict) -> List[str]:
        """生成修改建议"""
        suggestions = []
        
        # 必填项建议
        for check_name, check_result in checks.items():
            if not check_result["passed"]:
                suggestions.append(f"必须修复：{check_result['message']}")
        
        # 加分项建议
        if not bonus["effort"]["present"]:
            suggestions.append("建议补充工作量评估（如：2 人天）")
        if not bonus["priority"]["present"]:
            suggestions.append("建议补充优先级标注（P0/P1/P2）")
        if not bonus["background"]["present"]:
            suggestions.append("建议补充业务背景说明")
        
        return suggestions
    
    def _get_evaluation_level(self, score: int) -> str:
        """获取评价等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "合格"
        elif score >= 60:
            return "需改进"
        else:
            return "不合格"
