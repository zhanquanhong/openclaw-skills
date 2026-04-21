# -*- coding: utf-8 -*-
"""Skill 主入口 - 生产级"""

import logging
import re
from typing import Optional, Dict, Any
from .validator import TechDocValidator
from .reporter import Reporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TechDocValidatorSkill:
    """技术方案验证器 Skill - 生产级"""
    
    def __init__(self):
        self.validator = TechDocValidator(tech_stack="java")
        self.reporter = Reporter()
    
    async def handle_command(self, command: str, args: str, context: Dict[str, Any]) -> str:
        """处理 Skill 命令"""
        logger.info(f"收到命令：{command}, 参数：{args}")
        
        try:
            # 提取文档链接或文本
            doc_input = self._extract_input(args, context)
            
            if not doc_input:
                return self._error_response("未找到文档内容", "请提供飞书文档链接或粘贴技术方案内容")
            
            # 获取文档内容
            content = await self._get_document_content(doc_input, context)
            
            if not content:
                return self._error_response("无法获取文档内容", "请检查链接是否有效或您是否有访问权限")
            
            # 提取文件名
            file_name = self._extract_file_name(doc_input, context)
            
            # 执行验证
            result = self.validator.validate(content, file_name)
            
            # 生成报告
            report = self.reporter.generate_markdown(result)
            
            logger.info(f"验证完成：{result['summary']['score']}分")
            return report
            
        except Exception as e:
            logger.error(f"验证失败：{e}", exc_info=True)
            return self._error_response("验证失败", str(e))
    
    def _extract_input(self, args: str, context: Dict[str, Any]) -> Optional[str]:
        """提取输入（链接或文本）"""
        # 优先从参数提取
        if args and args.strip():
            return args.strip()
        
        # 从上下文提取（回复消息）
        if context.get("reply_to"):
            reply_content = context.get("reply_to", "")
            # 提取链接
            url_match = re.search(r'https://[^\s]+', reply_content)
            if url_match:
                return url_match.group(0)
        
        return None
    
    async def _get_document_content(self, doc_input: str, context: Dict[str, Any]) -> Optional[str]:
        """获取文档内容"""
        # 判断是链接还是直接文本
        if doc_input.startswith("http"):
            # 飞书文档链接 - 调用 Feishu API
            return await self._fetch_feishu_doc(doc_input, context)
        else:
            # 直接粘贴的文本
            return doc_input
    
    async def _fetch_feishu_doc(self, url: str, context: Dict[str, Any]) -> Optional[str]:
        """获取飞书文档内容"""
        try:
            # 从 URL 提取 doc_token
            # 格式：https://feishu.cn/docx/XXX 或 https://[tenant].feishu.cn/docx/XXX
            match = re.search(r'/docx/([a-zA-Z0-9]+)', url)
            if not match:
                logger.warning(f"无法解析飞书文档 URL: {url}")
                return None
            
            doc_token = match.group(1)
            logger.info(f"解析 doc_token: {doc_token}")
            
            # 注意：实际使用时需要调用 Feishu API
            # 这里返回一个标记，实际由 OpenClaw 框架处理
            return f"__FEISHU_DOC__:{doc_token}"
            
        except Exception as e:
            logger.error(f"获取飞书文档失败：{e}")
            return None
    
    def _extract_file_name(self, doc_input: str, context: Dict[str, Any]) -> str:
        """提取文件名"""
        if doc_input.startswith("http"):
            # 从 URL 提取
            match = re.search(r'/docx/([a-zA-Z0-9]+)', doc_input)
            if match:
                return f"飞书文档 ({match.group(1)})"
            return "飞书文档"
        else:
            return "技术方案文本"
    
    def _error_response(self, title: str, message: str) -> str:
        """生成错误响应"""
        return f"""❌ {title}

原因：{message}

建议：
  1. 检查输入是否正确
  2. 确认您有文档访问权限
  3. 重新尝试或联系管理员

如需帮助，请发送：/validate --help"""


# Skill 导出
skill = TechDocValidatorSkill()
