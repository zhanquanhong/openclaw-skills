"""用户白名单管理器 - 方案 C 生产级实现"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional


class UserWhitelistManager:
    """用户白名单管理器（支持本地学习 + 可选共享）"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化白名单管理器
        
        Args:
            data_dir: 数据目录（默认：data/）
        """
        if data_dir is None:
            # 默认使用代码目录下的 data/
            self.data_dir = Path(__file__).parent.parent / 'data'
        else:
            self.data_dir = Path(data_dir)
        
        self.data_dir.mkdir(exist_ok=True)
        
        # 文件路径
        self.official_whitelist = self.data_dir / 'whitelist.yaml'
        self.user_whitelist = self.data_dir / 'user_whitelist.yaml'
        self.merged_whitelist_cache = self.data_dir / '.merged_whitelist.yaml'
    
    def load_official(self) -> Dict:
        """加载官方白名单"""
        if not self.official_whitelist.exists():
            return {}
        
        with open(self.official_whitelist, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def load_user(self) -> Dict:
        """加载用户白名单"""
        if not self.user_whitelist.exists():
            return {}
        
        with open(self.user_whitelist, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def save_user(self, whitelist: Dict, auto_merge: bool = True):
        """
        保存用户白名单
        
        Args:
            whitelist: 用户白名单
            auto_merge: 是否自动合并到缓存
        """
        with open(self.user_whitelist, 'w', encoding='utf-8') as f:
            yaml.dump(whitelist, f, allow_unicode=True, default_flow_style=False)
        
        if auto_merge:
            self.merge_whitelists()
    
    def merge_whitelists(self) -> Dict:
        """
        合并官方 + 用户白名单（用户优先）
        
        Returns:
            dict: 合并后的白名单
        """
        official = self.load_official()
        user = self.load_user()
        
        # 深拷贝官方白名单
        merged = {}
        for module, items in official.items():
            merged[module] = list(items) if isinstance(items, list) else items
        
        # 用户白名单覆盖/补充
        for module, items in user.items():
            if module not in merged:
                merged[module] = []
            
            # 合并任务（去重）
            existing_contents = set()
            if isinstance(merged[module], list):
                for item in merged[module]:
                    if isinstance(item, dict) and '任务内容' in item:
                        existing_contents.add(item['任务内容'])
                    elif isinstance(item, str):
                        existing_contents.add(item)
            
            for item in items:
                content = item.get('任务内容', '') if isinstance(item, dict) else item
                if content not in existing_contents:
                    merged[module].append(item)
                    existing_contents.add(content)
        
        # 保存缓存
        with open(self.merged_whitelist_cache, 'w', encoding='utf-8') as f:
            yaml.dump(merged, f, allow_unicode=True, default_flow_style=False)
        
        return merged
    
    def get_merged(self) -> Dict:
        """获取合并后的白名单（优先使用缓存）"""
        if self.merged_whitelist_cache.exists():
            with open(self.merged_whitelist_cache, 'r', encoding='utf-8') as f:
                cached = yaml.safe_load(f)
                if cached:
                    return cached
        
        return self.merge_whitelists()
    
    def export(self, output_path: str, include_official: bool = False):
        """
        导出用户白名单（用于共享）
        
        Args:
            output_path: 输出路径
            include_official: 是否包含官方白名单
        """
        if include_official:
            whitelist = self.get_merged()
        else:
            whitelist = self.load_user()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(whitelist, f, allow_unicode=True, default_flow_style=False)
        
        print(f'✅ 导出成功：{output_path}')
        print(f'   模块数：{len(whitelist)}')
        print(f'   任务数：{sum(len(items) for items in whitelist.values())}')
    
    def import_whitelist(self, input_path: str, merge: bool = True):
        """
        导入用户白名单（从其他用户/官方共享）
        
        Args:
            input_path: 输入路径
            merge: 是否合并到现有用户白名单
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f'文件不存在：{input_path}')
        
        with open(input_path, 'r', encoding='utf-8') as f:
            imported = yaml.safe_load(f) or {}
        
        if merge:
            # 合并到现有用户白名单
            existing = self.load_user()
            for module, items in imported.items():
                if module not in existing:
                    existing[module] = []
                
                # 去重合并
                existing_contents = set()
                for item in existing[module]:
                    content = item.get('任务内容', '') if isinstance(item, dict) else item
                    existing_contents.add(content)
                
                for item in items:
                    content = item.get('任务内容', '') if isinstance(item, dict) else item
                    if content not in existing_contents:
                        existing[module].append(item)
                        existing_contents.add(content)
            
            self.save_user(existing)
        else:
            # 覆盖用户白名单
            self.save_user(imported)
        
        print(f'✅ 导入成功：{input_path}')
        print(f'   模块数：{len(imported)}')
        print(f'   任务数：{sum(len(items) for items in imported.values())}')
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        official = self.load_official()
        user = self.load_user()
        
        return {
            'official_modules': len(official),
            'official_tasks': sum(len(items) for items in official.values()),
            'user_modules': len(user),
            'user_tasks': sum(len(items) for items in user.values()),
            'has_user_data': self.user_whitelist.exists(),
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        
        print('=' * 60)
        print('📊 wbs-skill 白名单统计')
        print('=' * 60)
        print(f'📁 官方白名单：{stats["official_modules"]} 个模块，{stats["official_tasks"]} 个任务')
        print(f'👤 用户白名单：{stats["user_modules"]} 个模块，{stats["user_tasks"]} 个任务')
        print(f'💾 用户数据：{"✅ 已存在" if stats["has_user_data"] else "❌ 未创建"}')
        print('=' * 60)


# 便捷函数
def get_manager(data_dir: str = None) -> UserWhitelistManager:
    """获取白名单管理器实例"""
    return UserWhitelistManager(data_dir)


def load_whitelist(data_dir: str = None) -> Dict:
    """加载合并后的白名单（推荐使用）"""
    manager = UserWhitelistManager(data_dir)
    return manager.get_merged()
