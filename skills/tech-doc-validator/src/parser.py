# -*- coding: utf-8 -*-
"""Markdown 解析器 - 生产级"""

import re
from typing import Dict, List, Any, Optional


class MarkdownParser:
    """Markdown 解析器 - 生产级"""
    
    def __init__(self):
        self.task_blocks = []
    
    def parse(self, content: str) -> Dict[str, Any]:
        """解析 Markdown 内容"""
        # 提取所有任务块（### 标题开始）
        self.task_blocks = self._extract_task_blocks(content)
        
        # 提取元数据
        metadata = self._extract_metadata(content)
        
        return {
            "content": content,
            "metadata": metadata,
            "task_blocks": self.task_blocks,
            "char_count": len(content),
            "task_count": len(self.task_blocks)
        }
    
    def _extract_task_blocks(self, content: str) -> List[Dict[str, Any]]:
        """提取任务块"""
        blocks = []
        
        # 匹配 ### 标题开始的任务块
        pattern = r'^###\s+(.+)$'
        lines = content.split('\n')
        
        current_title = None
        current_content = []
        
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                # 保存上一个块
                if current_title:
                    blocks.append({
                        "title": current_title,
                        "content": '\n'.join(current_content),
                        "line_start": len(blocks) + 1
                    })
                
                # 开始新块
                current_title = match.group(1).strip()
                current_content = [line]
            else:
                if current_title:
                    current_content.append(line)
        
        # 保存最后一个块
        if current_title:
            blocks.append({
                "title": current_title,
                "content": '\n'.join(current_content),
                "line_start": len(blocks) + 1
            })
        
        return blocks
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """提取元数据"""
        metadata = {}
        
        # 提取版本
        version_match = re.search(r'\*\*版本\*\*:\s*(.+)', content)
        if version_match:
            metadata["version"] = version_match.group(1).strip()
        
        # 提取创建时间
        time_match = re.search(r'\*\*创建时间\*\*:\s*(.+)', content)
        if time_match:
            metadata["create_time"] = time_match.group(1).strip()
        
        # 提取技术栈
        if "java" in content.lower() or "spring" in content.lower():
            metadata["tech_stack"] = "java"
        elif "python" in content.lower() or "fastapi" in content.lower():
            metadata["tech_stack"] = "python"
        else:
            metadata["tech_stack"] = "unknown"
        
        return metadata
    
    def get_task_block(self, index: int) -> Optional[Dict[str, Any]]:
        """获取指定任务块"""
        if 0 <= index < len(self.task_blocks):
            return self.task_blocks[index]
        return None
    
    def find_fuzzy_words(self, content: str, fuzzy_dict: Dict[str, str]) -> List[Dict[str, Any]]:
        """查找模糊词"""
        issues = []
        
        for fuzzy, suggestion in fuzzy_dict.items():
            if fuzzy in content:
                # 找到位置（行号）
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if fuzzy in line:
                        issues.append({
                            "line": i,
                            "text": fuzzy,
                            "suggestion": suggestion,
                            "context": line.strip()
                        })
        
        return issues
