# -*- coding: utf-8 -*-
"""飞书 Skill 处理器 - 生产级"""

import logging
import re
import os
from typing import Optional, Dict, Any
try:
    from .validator import TechDocValidator
    from .reporter import Reporter
    from .pdf_parser import PDFParser
except ImportError:
    from validator import TechDocValidator
    from reporter import Reporter
    from pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class FeishuSkillHandler:
    """飞书 Skill 处理器 - 生产级"""
    
    def __init__(self, app_id: str = "cli_a93a64c12179dbcb"):
        self.app_id = app_id
        self.validator = TechDocValidator(tech_stack="java")
        self.reporter = Reporter()
        self.pdf_parser = PDFParser()
    
    async def handle_message(self, message: Dict[str, Any]) -> str:
        """处理飞书消息"""
        try:
            logger.info(f"收到消息：{message}")
            
            # 提取命令和内容
            text = message.get("text", "").strip()
            
            # 检查是否是 /validate 命令
            if not text.startswith("/validate"):
                return ""
            
            # 提取参数
            params = text.replace("/validate", "").strip()
            
            # 检查是否有文件附件
            file_url = message.get("file_url")
            file_path = message.get("file_path")
            
            content = None
            file_name = "未知文档"
            
            # 优先处理文件
            if file_path:
                logger.info(f"检查文件：{file_path}, 存在：{os.path.exists(file_path)}")
                if os.path.exists(file_path):
                    logger.info(f"处理文件：{file_path}")
                    if file_path.endswith(".pdf"):
                        content = self.pdf_parser.extract(file_path)
                        file_name = os.path.basename(file_path)
                    elif file_path.endswith(".md"):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        file_name = os.path.basename(file_path)
            
            # 其次处理链接
            elif params.startswith("http"):
                logger.info(f"处理链接：{params}")
                # 飞书文档链接处理（需要 API 权限）
                doc_token = self._extract_doc_token(params)
                if doc_token:
                    # TODO: 调用飞书 API 获取文档内容
                    logger.warning(f"飞书 API 读取未实现：{doc_token}")
                    return self._error_response(
                        "飞书文档读取中",
                        "当前飞书 API 权限不足，请：\n1. 分享文档给机器人\n2. 或开启公开链接\n3. 或直接粘贴文档内容"
                    )
            
            # 直接粘贴文本
            elif params:
                content = params
                file_name = "技术方案文本"
            
            # 无内容
            if not content:
                return self._error_response(
                    "未找到文档内容",
                    "请提供：\n1. 飞书文档链接\n2. PDF/Markdown 文件\n3. 或直接粘贴技术方案文本"
                )
            
            # 执行验证
            logger.info(f"开始验证：{file_name}")
            result = self.validator.validate(content, file_name)
            
            # 生成多条消息（避免超长）
            messages = self.reporter.generate_split_messages(result)
            
            logger.info(f"验证完成：{result['summary']['score']}分，消息数：{len(messages)}")
            
            # 返回多条消息（用分隔符）
            return '\n\n---\n\n'.join(messages)
            
        except Exception as e:
            logger.error(f"处理失败：{e}", exc_info=True)
            return self._error_response("验证失败", str(e))
    
    def _extract_doc_token(self, url: str) -> Optional[str]:
        """从飞书链接提取 doc_token"""
        # wiki 链接
        match = re.search(r'/wiki/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        
        # docx 链接
        match = re.search(r'/docx/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        
        return None
    
    def _error_response(self, title: str, message: str) -> str:
        """生成错误响应"""
        return f"""❌ {title}

原因：{message}

💡 使用方式：
1. `/validate https://feishu.cn/docx/xxx`
2. `/validate` + 上传 PDF/Markdown 文件
3. `/validate` + 粘贴技术方案文本"""


# Skill 导出
skill_handler = FeishuSkillHandler()
