# -*- coding: utf-8 -*-
"""模糊词库 - 生产级"""

FUZZY_WORDS = {
    # 模糊动词
    "优化一下": "添加索引，查询时间从 Xms 降低到 Yms",
    "改一下": "修改 [具体文件] 的 [具体方法]",
    "弄一下": "实现 [具体功能]",
    "搞一下": "开发 [具体接口]",
    "看一下": "检查 [具体条件]",
    "查一下": "查询 [具体表/条件]",
    
    # 模糊程度词
    "大概": "删除或给出具体数字",
    "左右": "删除或给出具体范围",
    "差不多": "删除或给出精确值",
    "基本": "删除或给出具体比例",
    "几乎": "删除或给出具体比例",
    
    # 模糊时间词
    "很快": "<100ms 或 实时",
    "立即": "<50ms",
    "稍后": "给出具体时间（如 5 秒后）",
    "过一会": "给出具体时间",
    
    # 模糊数量词
    "大量": ">1000 条 或 QPS>100",
    "很多": "给出具体数字",
    "少量": "<10 条",
    "一些": "给出具体数字",
    "几个": "给出具体数字",
    
    # 模糊频率词
    "偶尔": "错误率<1% 或 概率<5%",
    "有时": "给出具体比例",
    "经常": "给出具体比例",
    "通常": "给出具体比例",
    
    # 模糊质量词
    "良好": "给出具体指标（如成功率>99%）",
    "优秀": "给出具体指标（如成功率>99.9%）",
    "较好": "给出具体对比",
    "可以": "给出明确结论",
    "还行": "给出明确结论",
    
    # 模糊技术词
    "考虑扩展性": "预留 X 个扩展字段，支持 [具体场景]",
    "处理异常": "捕获 [具体异常类型]，返回 [具体错误码]",
    "性能优化": "从 Xms 优化到 Yms，通过 [具体手段]",
    "支持多种": "支持 [具体数量] 种：[列举]",
    "等等": "删除或完整列举",
    "相关": "删除或明确具体项",
}

# JAVA 特定模糊词
JAVA_FUZZY_WORDS = {
    "新建一个 Controller": "新建 `XxxController.java`，路径：`项目名/src/main/java/com/xxx/controller/XxxController.java`",
    "新建一个 Service": "新建 `XxxService.java`，路径：`项目名/src/main/java/com/xxx/service/XxxService.java`",
    "新建一个 Mapper": "新建 `XxxMapper.xml`，路径：`项目名/src/main/resources/mapper/XxxMapper.xml`",
    "加个方法": "新增方法：`methodName(@RequestBody XxxRequest request)`",
    "改个字段": "修改字段：`fieldName`，类型：`String`，说明：`[具体说明]`",
}

def get_fuzzy_words(tech_stack="java"):
    """获取模糊词库"""
    words = FUZZY_WORDS.copy()
    if tech_stack == "java":
        words.update(JAVA_FUZZY_WORDS)
    return words
