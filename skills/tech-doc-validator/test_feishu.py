#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""飞书 Skill 测试脚本"""

import asyncio
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from feishu_handler import FeishuSkillHandler


async def test_validate_pdf():
    """测试 PDF 验证"""
    handler = FeishuSkillHandler()
    
    # 模拟飞书消息（带文件）
    test_data = '/home/admin/.openclaw/workspace/test-data'
    pdf_file = [f for f in os.listdir(test_data) if '分享' in f and f.endswith('.pdf')][0]
    pdf_path = os.path.join(test_data, pdf_file)
    
    message = {
        "text": "/validate",
        "file_path": pdf_path,
        "file_url": ""
    }
    
    print("🔍 测试 PDF 验证...")
    report = await handler.handle_message(message)
    print(report)
    return report


async def test_validate_text():
    """测试文本验证"""
    handler = FeishuSkillHandler()
    
    # 模拟飞书消息（带文本）
    message = {
        "text": "/validate " + """
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
    }
    
    print("\n🔍 测试文本验证...")
    report = await handler.handle_message(message)
    print(report)
    return report


async def main():
    """主函数"""
    print("=" * 60)
    print("🧪 飞书 Skill 测试")
    print("=" * 60)
    
    # 测试 1: PDF 验证
    try:
        await test_validate_pdf()
    except Exception as e:
        print(f"❌ PDF 测试失败：{e}")
    
    # 测试 2: 文本验证
    try:
        await test_validate_text()
    except Exception as e:
        print(f"❌ 文本测试失败：{e}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
