# -*- coding: utf-8 -*-
"""报告生成器 - 生产级"""

from typing import Dict, List, Any
from datetime import datetime


# 高频问题 TOP3 正确示例
CORRECT_EXAMPLES = {
    "missing_api_definition": """
【正确示例】
#### 接口定义
**URL**: `POST /api/openclaw/skill/list`

**请求参数**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | number | 是 | 页码，默认 1 |
| size | number | 是 | 每页数量，默认 20 |

**返回数据**:
```json
{
  "code": 200,
  "data": {
    "total": 100,
    "list": [{"skillId": "sk_001", "name": "OCR"}]
  }
}
```

**错误码**:
| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 500 | 服务器错误 |
""",
    
    "missing_implementation": """
【正确示例】
#### 实现说明
1. ✅ 新建 `SkillController.java`
   - 路径：`yun-ai-api-openclaw/src/main/java/com/xxx/controller/SkillController.java`
   - 方法：`list(@RequestBody SkillListRequest request)`

2. ✅ 新建 `SkillService.java`
   - 路径：`yun-ai-api-openclaw/src/main/java/com/xxx/service/SkillService.java`
   - 方法：`list(SkillListRequest request)`

3. ✅ 新建 `SkillMapper.xml`
   - 路径：`yun-ai-api-openclaw/src/main/resources/mapper/SkillMapper.xml`
   - 查询：`selectList`
""",
    
    "missing_acceptance_criteria": """
【正确示例】
#### 验收标准
- [ ] 接口可正常调用，返回 HTTP 200
- [ ] 必填参数缺失时返回 HTTP 400，错误码 PARAM_ERROR
- [ ] 分页参数生效：page=1,size=10 返回第 1-10 条数据
- [ ] 关键词搜索模糊匹配："OCR" 可匹配 "OCR 文字提取"
- [ ] 响应时间 < 200ms（P95）
- [ ] 无技能时返回空列表，不报错
"""
}


class Reporter:
    """报告生成器 - 生产级"""
    
    def __init__(self, max_message_length: int = 4096, split_messages: bool = True):
        self.version = "1.0.0"
        self.max_message_length = max_message_length
        self.split_messages = split_messages
    
    def generate_markdown(self, result: Dict[str, Any]) -> str:
        """生成 Markdown 格式报告"""
        return self._generate_full_report(result)
    
    def generate_split_messages(self, result: Dict[str, Any]) -> List[str]:
        """生成多条消息（用于飞书等有限制的平台）"""
        full_report = self._generate_full_report(result)
        
        # 如果报告长度在限制内，返回单条消息
        if len(full_report) <= self.max_message_length:
            return [full_report]
        
        # 分割报告为多条消息
        messages = []
        current_msg = ""
        
        for line in full_report.split('\n'):
            # 如果当前行加上当前消息会超长
            if len(current_msg) + len(line) + 1 > self.max_message_length:
                # 保存当前消息
                if current_msg:
                    messages.append(current_msg)
                    current_msg = ""
                
                # 如果单行就超长，强制截断
                if len(line) > self.max_message_length:
                    messages.append(line[:self.max_message_length] + "... (续)")
                    current_msg = line[self.max_message_length:]
                else:
                    current_msg = line
            else:
                current_msg += '\n' + line if current_msg else line
        
        # 添加最后一条消息
        if current_msg:
            messages.append(current_msg)
        
        return messages
    
    def _generate_full_report(self, result: Dict[str, Any]) -> str:
        """生成完整报告（内部方法）"""
        lines = []
        
        # 标题
        lines.append("🔍 技术方案规范验证器 v" + self.version)
        lines.append(f"📄 检查文档：{result.get('file_name', '未知')}")
        lines.append(f"⏰ 检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 合规率
        score = result["summary"]["score"]
        passed = result["summary"]["passed"]
        lines.append("━" * 40)
        status = "✅" if passed else "❌"
        lines.append(f"{status} 合规率：{score}/100")
        lines.append("━" * 40)
        lines.append("")
        
        # 必填项检查
        lines.append("📋 必填项检查")
        for check_name, check_result in result["checks"].items():
            icon = "✅" if check_result["passed"] else "❌"
            value = check_result.get("value", "")
            value_str = f" ({value})" if value else ""
            lines.append(f"  {icon} {self._format_check_name(check_name)}:{value_str}")
        lines.append("")
        
        # 加分项
        bonus_total = sum(item["score"] for item in result["bonus"].values())
        lines.append(f"⭐ 加分项（{bonus_total}分）")
        for check_name, check_result in result["bonus"].items():
            icon = "✅" if check_result["present"] else "❌"
            value = check_result.get("value", "")
            value_str = f" ({value})" if value else ""
            score_str = f" +{check_result['score']}分" if check_result['score'] > 0 else ""
            lines.append(f"  {icon} {self._format_check_name(check_name)}:{value_str}{score_str}")
        lines.append("")
        
        # 问题列表
        if result["issues"]:
            lines.append(f"⚠️  发现问题（{len(result['issues'])}个）")
            
            # 分离必填项问题和模糊词问题
            required_issues = [i for i in result["issues"] if i.get('type', '').startswith('missing_')]
            fuzzy_issues = [i for i in result["issues"] if i.get('type') == 'vague_language']
            
            # 先显示必填项问题（带示例）
            if required_issues:
                for i, issue in enumerate(required_issues, 1):
                    lines.append(f"  {i}. 第{issue.get('line', '?')}行：{issue.get('type', '问题')}")
                    if issue.get('text'):
                        lines.append(f"     → 内容：\"{issue['text']}\"")
                    if issue.get('suggestion'):
                        lines.append(f"     → 建议：{issue['suggestion']}")
                    
                    # 为必填项问题添加正确示例
                    issue_type = issue.get('type', '')
                    if issue_type in CORRECT_EXAMPLES:
                        lines.append("     → 完整示例:")
                        example_lines = CORRECT_EXAMPLES[issue_type].strip().split('\n')
                        for example_line in example_lines:
                            lines.append(f"     {example_line}")
                lines.append("")
            
            # 再显示模糊词问题
            if fuzzy_issues:
                lines.append(f"  📝 模糊词（{len(fuzzy_issues)}个）:")
                for issue in fuzzy_issues[:5]:  # 最多显示 5 个
                    lines.append(f"    - 第{issue.get('line', '?')}行：\"{issue.get('text', '')}\" → {issue.get('suggestion', '')}")
                if len(fuzzy_issues) > 5:
                    lines.append(f"    ... 还有{len(fuzzy_issues) - 5}个")
                lines.append("")
        
        # 修改建议
        if result.get("suggestions"):
            lines.append("💡 修改建议")
            for suggestion in result["suggestions"]:
                lines.append(f"  - {suggestion}")
            lines.append("")
        
        # 总体评价
        lines.append("━" * 40)
        eval_level = result["evaluation"]["level"]
        wbs_ready = result["evaluation"]["wbs_ready"]
        wbs_str = "可生成 WBS" if wbs_ready else "暂不可生成 WBS"
        lines.append(f"🎯 总体评价：{eval_level}，{wbs_str}")
        lines.append("━" * 40)
        
        return '\n'.join(lines)
    
    def generate_json(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """生成 JSON 格式报告"""
        return {
            "version": self.version,
            "file_name": result.get("file_name", ""),
            "check_time": datetime.now().isoformat(),
            "summary": result["summary"],
            "checks": result["checks"],
            "bonus": result["bonus"],
            "issues": result["issues"],
            "suggestions": result.get("suggestions", []),
            "evaluation": result["evaluation"]
        }
    
    def generate_text(self, result: Dict[str, Any]) -> str:
        """生成纯文本报告"""
        lines = []
        
        score = result["summary"]["score"]
        passed = result["summary"]["passed"]
        
        lines.append(f"技术方案验证报告")
        lines.append(f"合规率：{score}/100 ({'通过' if passed else '不通过'})")
        lines.append("")
        
        # 必填项
        lines.append("必填项检查:")
        for check_name, check_result in result["checks"].items():
            status = "通过" if check_result["passed"] else "不通过"
            lines.append(f"  - {check_name}: {status}")
        lines.append("")
        
        # 问题
        if result["issues"]:
            lines.append(f"发现问题：{len(result['issues'])}个")
            for issue in result["issues"]:
                lines.append(f"  - 第{issue.get('line', '?')}行：{issue.get('type', '问题')}")
        
        return '\n'.join(lines)
    
    def _format_check_name(self, name: str) -> str:
        """格式化检查项名称"""
        names = {
            "task_type": "任务类型标记",
            "dependencies": "依赖关系",
            "api_definition": "接口定义",
            "implementation": "实现说明",
            "acceptance_criteria": "验收标准",
            "effort": "工作量评估",
            "priority": "优先级标注",
            "background": "业务背景"
        }
        return names.get(name, name)
