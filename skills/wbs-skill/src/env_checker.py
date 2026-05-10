#!/usr/bin/env python3
"""环境检查器

检查运行环境是否满足要求：
1. Python 版本 >= 3.8
2. 核心依赖是否安装
3. 必要目录是否存在

使用方式：
    checker = EnvChecker()
    ok, msg = checker.check()
    if not ok:
        print(f'环境检查失败：{msg}')
        sys.exit(1)
"""

import sys
import logging
from pathlib import Path
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)


class EnvChecker:
    """环境检查器

    检查 Python 版本、依赖包、必要目录。

    Attributes:
        required_packages: 必须安装的 Python 包及其用途说明
        required_dirs: 必须存在的目录列表
    """

    REQUIRED_PACKAGES: Dict[str, str] = {
        'PyPDF2': 'PDF 文本解析',
        'pdfplumber': 'PDF 表格解析',
        'openpyxl': 'Excel 输出',
        'yaml': 'YAML 配置解析',
    }

    REQUIRED_DIRS: List[str] = ['config', 'data', 'output']

    MIN_PYTHON_VERSION: Tuple[int, int] = (3, 8)

    def check(self) -> Tuple[bool, str]:
        """执行完整环境检查

        Returns:
            (是否通过, 错误信息)

        检查顺序：
            1. Python 版本
            2. 核心依赖
            3. 必要目录
        """
        # 检查 1：Python 版本
        py_ok, py_msg = self._check_python_version()
        if not py_ok:
            return False, py_msg

        # 检查 2：核心依赖
        deps_ok, deps_msg = self._check_dependencies()
        if not deps_ok:
            return False, deps_msg

        # 检查 3：必要目录
        dirs_ok, dirs_msg = self._check_directories()
        if not dirs_ok:
            return False, dirs_msg

        return True, '环境就绪'

    def _check_python_version(self) -> Tuple[bool, str]:
        """检查 Python 版本是否满足要求

        Returns:
            (是否通过, 错误信息)
        """
        current = sys.version_info[:2]
        if current < self.MIN_PYTHON_VERSION:
            version_str = f'{current[0]}.{current[1]}'
            required_str = f'{self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]}'
            return False, (
                f'Python 版本过低：{version_str}（需要 {required_str}+）\n'
                f'当前路径：{sys.executable}'
            )
        return True, f'Python {sys.version_info.major}.{sys.version_info.minor} 版本满足要求'

    def _check_dependencies(self) -> Tuple[bool, str]:
        """检查核心依赖是否已安装

        Returns:
            (是否通过, 错误信息)
        """
        missing = []
        for package, desc in self.REQUIRED_PACKAGES.items():
            try:
                __import__(package)
                logger.debug(f'依赖已安装：{package}')
            except ImportError:
                missing.append(f'{package}（{desc}）')

        if missing:
            return False, (
                f'缺少依赖：{", ".join(missing)}\n'
                f'请运行安装脚本：\n'
                f'  Mac/Linux: ./install.sh\n'
                f'  Windows:   install.bat'
            )

        return True, '所有依赖已安装'

    def _check_directories(self) -> Tuple[bool, str]:
        """检查必要目录是否存在，不存在则自动创建

        Returns:
            (是否通过, 错误信息)
        """
        skill_dir = Path(__file__).parent.parent
        created = []

        for dir_name in self.REQUIRED_DIRS:
            dir_path = skill_dir / dir_name
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created.append(dir_name)
                    logger.info(f'自动创建目录：{dir_path}')
                except OSError as e:
                    return False, (
                        f'无法创建目录 {dir_name}：{e}\n'
                        f'请检查目录权限或手动创建：{dir_path}'
                    )

        if created:
            return True, f'自动创建目录：{", ".join(created)}'
        return True, '所有必要目录已存在'

    def check_python_only(self) -> Tuple[bool, str]:
        """仅检查 Python 版本（用于安装脚本前置检查）

        Returns:
            (是否通过, 错误信息)
        """
        return self._check_python_version()

    def get_system_info(self) -> Dict[str, str]:
        """获取系统信息（用于调试）

        Returns:
            系统信息字典
        """
        return {
            'python_version': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
            'python_path': sys.executable,
            'platform': sys.platform,
            'cwd': str(Path.cwd()),
            'skill_dir': str(Path(__file__).parent.parent),
        }
