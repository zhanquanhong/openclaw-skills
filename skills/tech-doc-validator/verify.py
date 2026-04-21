#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速验证脚本 - 生产级"""

import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from validator import TechDocValidator
from reporter import Reporter

def main():
    """主函数"""
    # 创建验证器
    validator = TechDocValidator(tech_stack="java")
    reporter = Reporter()
    
    # 测试文档
    test_doc = """
### 1.1 技能列表查询接口 🆕新增

**任务类型**: 🆕新增接口
**工作量**: 2 人天
**优先级**: P0
**依赖**: 无

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
    
    # 执行验证
    print("🔍 技术方案规范验证器 v1.0.0")
    print("📄 测试文档：示例技术方案")
    print("")
    
    result = validator.validate(test_doc, "示例技术方案")
    report = reporter.generate_markdown(result)
    
    print(report)
    
    # 返回退出码
    sys.exit(0 if result["summary"]["passed"] else 1)

if __name__ == "__main__":
    main()
