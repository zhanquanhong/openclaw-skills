# -*- coding: utf-8 -*-
"""单元测试 - 生产级"""

import pytest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rules import RuleEngine
from parser import MarkdownParser
from validator import TechDocValidator


class TestRuleEngine:
    """规则引擎测试"""
    
    def setup_method(self):
        self.engine = RuleEngine(tech_stack="java")
    
    def test_check_task_type_valid(self):
        """测试任务类型标记 - 有效"""
        content = "### 1.1 技能列表查询接口 🆕新增"
        result = self.engine.check_task_type(content)
        assert result["passed"] is True
        assert "🆕" in result["value"]
    
    def test_check_task_type_invalid(self):
        """测试任务类型标记 - 无效"""
        content = "### 1.1 技能列表查询接口"
        result = self.engine.check_task_type(content)
        assert result["passed"] is False
    
    def test_check_dependencies_valid(self):
        """测试依赖关系 - 有效"""
        content = "**依赖**: 无"
        result = self.engine.check_dependencies(content)
        assert result["passed"] is True
    
    def test_check_dependencies_invalid(self):
        """测试依赖关系 - 无效"""
        content = "### 接口定义"
        result = self.engine.check_dependencies(content)
        assert result["passed"] is False
    
    def test_check_api_definition_complete(self):
        """测试接口定义 - 完整"""
        content = """
        **URL**: `POST /api/test`
        **请求参数**: page, size
        **返回数据**: total, list
        **错误码**: 200, 400, 500
        """
        result = self.engine.check_api_definition(content)
        assert result["passed"] is True
    
    def test_check_api_definition_incomplete(self):
        """测试接口定义 - 不完整"""
        content = "**URL**: `POST /api/test`"
        result = self.engine.check_api_definition(content)
        assert result["passed"] is False
    
    def test_check_implementation_specific(self):
        """测试实现说明 - 具体"""
        content = """
        路径：`yun-ai-api-openclaw/src/main/java/com/xxx/controller/SkillController.java`
        方法：`list(@RequestBody SkillListRequest request)`
        """
        result = self.engine.check_implementation(content)
        assert result["passed"] is True
    
    def test_check_implementation_vague(self):
        """测试实现说明 - 模糊"""
        content = "在 Controller 里加个方法"
        result = self.engine.check_implementation(content)
        assert result["passed"] is False
    
    def test_check_acceptance_criteria_valid(self):
        """测试验收标准 - 有效"""
        content = """
        #### 验收标准
        - [ ] 接口可正常调用，返回 HTTP 200
        - [ ] 响应时间 < 200ms
        """
        result = self.engine.check_acceptance_criteria(content)
        assert result["passed"] is True
    
    def test_check_acceptance_criteria_invalid(self):
        """测试验收标准 - 无效"""
        content = "#### 验收标准\n功能正常"
        result = self.engine.check_acceptance_criteria(content)
        assert result["passed"] is False
    
    def test_check_effort_valid(self):
        """测试工作量评估 - 有效"""
        content = "**工作量**: 2 人天"
        result = self.engine.check_effort(content)
        assert result["present"] is True
        assert result["score"] == 10
    
    def test_check_effort_invalid(self):
        """测试工作量评估 - 无效"""
        content = "### 接口定义"
        result = self.engine.check_effort(content)
        assert result["present"] is False
        assert result["score"] == 0
    
    def test_check_priority_valid(self):
        """测试优先级标注 - 有效"""
        content = "**优先级**: P0"
        result = self.engine.check_priority(content)
        assert result["present"] is True
        assert result["score"] == 10
    
    def test_check_background_valid(self):
        """测试业务背景 - 有效"""
        content = "#### 业务背景\n用户在技能管理页面需要查看技能列表"
        result = self.engine.check_background(content)
        assert result["present"] is True
        assert result["score"] == 10


class TestMarkdownParser:
    """Markdown 解析器测试"""
    
    def setup_method(self):
        self.parser = MarkdownParser()
    
    def test_parse_basic(self):
        """测试基础解析"""
        content = """
        # 技术方案
        
        ### 1.1 技能列表查询接口 🆕新增
        
        **依赖**: 无
        
        ### 1.2 技能搜索接口 🆕新增
        
        **依赖**: 1.1
        """
        result = self.parser.parse(content)
        assert result["task_count"] == 2
        assert len(result["task_blocks"]) == 2
    
    def test_extract_task_blocks(self):
        """测试任务块提取"""
        content = """
        ### 1.1 接口 1 🆕新增
        内容 1
        
        ### 1.2 接口 2 🔄优化
        内容 2
        """
        blocks = self.parser._extract_task_blocks(content)
        assert len(blocks) == 2
        assert "接口 1" in blocks[0]["title"]
        assert "接口 2" in blocks[1]["title"]


class TestTechDocValidator:
    """验证器集成测试"""
    
    def setup_method(self):
        self.validator = TechDocValidator(tech_stack="java")
    
    def test_validate_good_doc(self):
        """测试合格文档"""
        content = """
        ### 1.1 技能列表查询接口 🆕新增
        
        **依赖**: 无
        **优先级**: P0
        **工作量**: 2 人天
        
        #### 业务背景
        用户需要查看技能列表
        
        #### 接口定义
        **URL**: `POST /api/test`
        **请求参数**: page, size
        **返回数据**: total, list
        **错误码**: 200, 400
        
        #### 实现说明
        路径：`src/main/java/com/xxx/controller/SkillController.java`
        方法：`list()`
        
        #### 验收标准
        - [ ] 接口可正常调用
        - [ ] 响应时间 < 200ms
        """
        result = self.validator.validate(content, "test.md")
        assert result["summary"]["score"] >= 70
        assert result["summary"]["passed"] is True
        assert result["evaluation"]["wbs_ready"] is True
    
    def test_validate_bad_doc(self):
        """测试不合格文档"""
        content = """
        ### 1.1 技能列表查询接口
        
        优化一下查询性能
        """
        result = self.validator.validate(content, "test.md")
        assert result["summary"]["score"] < 70
        assert result["summary"]["passed"] is False
        assert len(result["issues"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
