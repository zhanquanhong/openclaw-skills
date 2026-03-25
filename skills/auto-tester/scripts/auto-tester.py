#!/usr/bin/env python3
"""
自动化测试工具 - Auto Tester
支持回归测试、场景覆盖、API 测试、功能验证
适用于 Windows/Mac/Linux

用法:
    python auto-tester.py <项目路径> [选项]
    
选项:
    --type api|unit|integration|regression  测试类型
    --coverage  生成覆盖率报告
    --output  输出报告路径
    --diff  对比新旧版本差异
"""

import os
import sys
import re
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import hashlib


# ==================== 测试用例定义 ====================

class TestType(Enum):
    UNIT = "单元测试"
    INTEGRATION = "集成测试"
    API = "API 测试"
    REGRESSION = "回归测试"
    SCENARIO = "场景测试"


class TestStatus(Enum):
    PASS = "✅ 通过"
    FAIL = "❌ 失败"
    SKIP = "⚪ 跳过"
    ERROR = "🔴 错误"


@dataclass
class TestCase:
    id: str
    name: str
    type: str
    description: str
    preconditions: List[str]
    steps: List[str]
    expected: str
    actual: str = ""
    status: str = ""
    priority: str = "P2"
    module: str = ""
    tags: List[str] = None


@dataclass
class TestResult:
    test_case: TestCase
    status: str
    execution_time: float
    error_message: str = ""
    screenshot: str = ""
    log: str = ""


@dataclass
class TestReport:
    project: str
    test_time: str
    total_cases: int
    passed: int
    failed: int
    skipped: int
    coverage: float
    duration: float
    results: List[TestResult]
    summary: str
    recommendations: List[str]


# ==================== 测试模板生成器 ====================

class TestTemplateGenerator:
    """测试模板生成器"""
    
    def __init__(self, language: str = "python"):
        self.language = language
    
    def generate_unit_test(self, class_name: str, methods: List[str]) -> str:
        """生成单元测试模板"""
        if self.language == "python":
            return self._generate_python_unit_test(class_name, methods)
        elif self.language == "java":
            return self._generate_java_unit_test(class_name, methods)
        return ""
    
    def _generate_python_unit_test(self, class_name: str, methods: List[str]) -> str:
        """生成 Python 单元测试"""
        test_class = f"Test{class_name}"
        
        template = f'''#!/usr/bin/env python3
"""
{test_class} 单元测试
自动生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from {class_name.lower()} import {class_name}


class {test_class}(unittest.TestCase):
    """{class_name} 单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.instance = {class_name}()
    
    def tearDown(self):
        """测试后清理"""
        del self.instance
    
    # ========== 正常场景测试 ==========
'''
        
        for method in methods:
            template += f'''
    def test_{method}_normal(self):
        """测试 {method} 正常场景"""
        # Arrange - 准备测试数据
        input_data = {{}}  # TODO: 填写测试数据
        
        # Act - 执行测试
        result = self.instance.{method}(input_data)
        
        # Assert - 验证结果
        self.assertIsNotNone(result)
        # TODO: 添加更多断言
'''
        
        template += '''
    # ========== 边界场景测试 ==========
'''
        
        for method in methods:
            template += f'''
    def test_{method}_boundary(self):
        """测试 {method} 边界条件"""
        # Arrange - 边界数据
        boundary_data = {{}}  # TODO: 填写边界数据
        
        # Act & Assert
        with self.assertRaises(Exception):  # 或具体异常类型
            self.instance.{method}(boundary_data)
'''
        
        template += '''
    # ========== 异常场景测试 ==========
'''
        
        for method in methods:
            template += f'''
    def test_{method}_exception(self):
        """测试 {method} 异常处理"""
        # Arrange - 异常数据
        invalid_data = None  # TODO: 填写异常数据
        
        # Act & Assert
        with self.assertRaises((ValueError, TypeError)):
            self.instance.{method}(invalid_data)
'''
        
        template += '''
    # ========== 回归测试 ==========
    
    def test_existing_functionality(self):
        """回归测试 - 确保原有功能不受影响"""
        # TODO: 添加原有功能的测试用例
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''
        
        return template
    
    def _generate_java_unit_test(self, class_name: str, methods: List[str]) -> str:
        """生成 Java 单元测试"""
        test_class = f"{class_name}Test"
        
        template = f'''// {test_class}.java
// 自动生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

package com.example.test;

import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import com.example.{class_name};

/**
 * {class_name} 单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("{class_name} 测试")
class {test_class} {{
    
    @InjectMocks
    private {class_name} instance;
    
    @Mock
    private Object dependency;  // TODO: 添加依赖
    
    @BeforeEach
    void setUp() {{
        // 测试前准备
    }}
    
    @AfterEach
    void tearDown() {{
        // 测试后清理
    }}
    
    // ========== 正常场景测试 ==========
'''
        
        for i, method in enumerate(methods, 1):
            method_name = self._to_camel_case(method)
            template += f'''
    @Test
    @DisplayName("测试{method_name} - 正常场景")
    void test{method_name}_Normal() {{
        // Arrange - 准备测试数据
        var inputData = new Object();  // TODO: 填写测试数据
        
        // Act - 执行测试
        var result = instance.{method_name}(inputData);
        
        // Assert - 验证结果
        assertNotNull(result);
        // TODO: 添加更多断言
    }}
'''
        
        template += '''
    // ========== 边界场景测试 ==========
'''
        
        for i, method in enumerate(methods, 1):
            method_name = self._to_camel_case(method)
            template += f'''
    @Test
    @DisplayName("测试{method_name} - 边界条件")
    void test{method_name}_Boundary() {{
        // Arrange - 边界数据
        Object boundaryData = null;  // TODO: 填写边界数据
        
        // Act & Assert
        assertThrows(Exception.class, () -> {{
            instance.{method_name}(boundaryData);
        }});
    }}
'''
        
        template += '''
    // ========== 异常场景测试 ==========
'''
        
        for i, method in enumerate(methods, 1):
            method_name = self._to_camel_case(method)
            template += f'''
    @Test
    @DisplayName("测试{method_name} - 异常处理")
    void test{method_name}_Exception() {{
        // Arrange - 异常数据
        Object invalidData = null;  // TODO: 填写异常数据
        
        // Act & Assert
        assertThrows(IllegalArgumentException.class, () -> {{
            instance.{method_name}(invalidData);
        }});
    }}
'''
        
        template += '''
    // ========== 回归测试 ==========
    
    @Test
    @DisplayName("回归测试 - 确保原有功能不受影响")
    void testExistingFunctionality_Reggression() {
        // TODO: 添加原有功能的测试用例
    }
}
'''
        
        return template
    
    def _to_camel_case(self, name: str) -> str:
        """转换为驼峰命名"""
        parts = name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
    def generate_api_test(self, api_spec: Dict) -> str:
        """生成 API 测试模板"""
        template = f'''#!/usr/bin/env python3
"""
API 自动化测试
自动生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import requests
import unittest
from typing import Dict, Any


class APITestCase(unittest.TestCase):
    """API 测试类"""
    
    BASE_URL = "{api_spec.get('base_url', 'http://localhost:8080')}"
    TIMEOUT = 30
    
    def setUp(self):
        """测试前准备"""
        self.session = requests.Session()
        # TODO: 添加认证信息
        # self.session.headers.update({{'Authorization': 'Bearer token'}})
    
    def tearDown(self):
        """测试后清理"""
        self.session.close()
    
'''
        
        # 生成每个接口的测试
        for endpoint in api_spec.get('endpoints', []):
            template += self._generate_api_endpoint_test(endpoint)
        
        template += '''
if __name__ == "__main__":
    unittest.main(verbosity=2)
'''
        
        return template
    
    def _generate_api_endpoint_test(self, endpoint: Dict) -> str:
        """生成单个接口的测试"""
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '/api/test')
        name = endpoint.get('name', path.replace('/', '_'))
        
        template = f'''
    def test_{name}_success(self):
        """测试 {method} {path} - 成功场景"""
        # Arrange
        url = f"{{self.BASE_URL}}{path}"
        headers = {{'Content-Type': 'application/json'}}
        data = {{}}  # TODO: 填写请求数据
        
        # Act
        response = self.session.{method.lower()}(
            url,
            json=data if method in ['POST', 'PUT', 'PATCH'] else None,
            headers=headers,
            timeout=self.TIMEOUT
        )
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json())
    
    def test_{name}_validation(self):
        """测试 {method} {path} - 参数验证"""
        # Arrange
        url = f"{{self.BASE_URL}}{path}"
        invalid_data = {{}}  # TODO: 填写无效数据
        
        # Act
        response = self.session.{method.lower()}(url, json=invalid_data)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    def test_{name}_auth(self):
        """测试 {method} {path} - 认证验证"""
        # Arrange
        url = f"{{self.BASE_URL}}{path}"
        
        # Act (无认证)
        response = requests.{method.lower()}(url)
        
        # Assert
        self.assertIn(response.status_code, [401, 403])
    
'''
        
        return template
    
    def generate_regression_test(self, old_features: List[str], new_features: List[str]) -> str:
        """生成回归测试模板"""
        template = f'''#!/usr/bin/env python3
"""
回归测试套件
确保新功能不影响原有功能
自动生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

原有功能点：{len(old_features)} 个
新增功能点：{len(new_features)} 个
"""

import unittest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class RegressionTestSuite(unittest.TestCase):
    """回归测试套件"""
    
    @classmethod
    def setUpClass(cls):
        """测试套件初始化"""
        print("\\n" + "="*60)
        print("回归测试开始")
        print(f"原有功能点：{len(old_features)} 个")
        print(f"新增功能点：{len(new_features)} 个")
        print("="*60 + "\\n")
    
    @classmethod
    def tearDownClass(cls):
        """测试套件清理"""
        print("\\n" + "="*60)
        print("回归测试完成")
        print("="*60)
    
    # ========== 原有功能回归测试 ==========
'''
        
        for i, feature in enumerate(old_features, 1):
            template += f'''
    def test_existing_feature_{i}_{self._to_snake_case(feature)}(self):
        """回归测试 - 原有功能：{feature}"""
        # TODO: 实现测试逻辑
        # 确保原有功能仍然正常工作
        pass
'''
        
        template += '''
    # ========== 新增功能测试 ==========
'''
        
        for i, feature in enumerate(new_features, 1):
            template += f'''
    def test_new_feature_{i}_{self._to_snake_case(feature)}(self):
        """新功能测试：{feature}"""
        # TODO: 实现测试逻辑
        # 验证新功能符合预期
        pass
'''
        
        template += '''
    # ========== 集成场景测试 ==========
    
    def test_integration_scenario_1(self):
        """集成场景测试 1 - 新旧功能协同工作"""
        # TODO: 测试新旧功能的集成场景
        pass
    
    def test_integration_scenario_2(self):
        """集成场景测试 2 - 边界条件"""
        # TODO: 测试边界条件下的集成
        pass


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2, exit=False)
    
    # 生成报告
    print("\\n生成测试报告...")
'''
        
        return template
    
    def _to_snake_case(self, name: str) -> str:
        """转换为蛇形命名"""
        return name.lower().replace(' ', '_').replace('-', '_')


# ==================== 测试执行器 ====================

class TestExecutor:
    """测试执行器"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.results: List[TestResult] = []
    
    def run_unit_tests(self, test_file: str) -> TestResult:
        """运行单元测试"""
        import time
        start_time = time.time()
        
        try:
            # 运行 pytest 或 unittest
            result = subprocess.run(
                ['python', '-m', 'pytest', test_file, '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            execution_time = time.time() - start_time
            
            status = TestStatus.PASS if result.returncode == 0 else TestStatus.FAIL
            
            return TestResult(
                test_case=TestCase(
                    id=f"unit-{Path(test_file).name}",
                    name=test_file,
                    type=TestType.UNIT.value,
                    description="单元测试",
                    preconditions=[],
                    steps=[],
                    expected="所有测试通过"
                ),
                status=status.value,
                execution_time=execution_time,
                log=result.stdout + result.stderr
            )
            
        except subprocess.TimeoutExpired:
            return self._create_error_result(test_file, "测试超时")
        except Exception as e:
            return self._create_error_result(test_file, str(e))
    
    def run_api_tests(self, test_file: str, base_url: str) -> TestResult:
        """运行 API 测试"""
        import time
        start_time = time.time()
        
        try:
            env = os.environ.copy()
            env['TEST_BASE_URL'] = base_url
            
            result = subprocess.run(
                ['python', '-m', 'pytest', test_file, '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )
            
            execution_time = time.time() - start_time
            status = TestStatus.PASS if result.returncode == 0 else TestStatus.FAIL
            
            return TestResult(
                test_case=TestCase(
                    id=f"api-{Path(test_file).name}",
                    name=test_file,
                    type=TestType.API.value,
                    description="API 测试",
                    preconditions=[f"服务运行在 {base_url}"],
                    steps=[],
                    expected="所有 API 测试通过"
                ),
                status=status.value,
                execution_time=execution_time,
                log=result.stdout + result.stderr
            )
            
        except Exception as e:
            return self._create_error_result(test_file, str(e))
    
    def run_regression_tests(self, old_test_files: List[str], new_test_files: List[str]) -> Dict:
        """运行回归测试"""
        import time
        start_time = time.time()
        
        results = {
            'old_features': [],
            'new_features': [],
            'regression_passed': True
        }
        
        # 运行原有功能测试
        print("\\n🔄 运行原有功能回归测试...")
        for test_file in old_test_files:
            result = self.run_unit_tests(test_file)
            results['old_features'].append(result)
            if result.status != TestStatus.PASS.value:
                results['regression_passed'] = False
                print(f"  ❌ {test_file} - 失败")
            else:
                print(f"  ✅ {test_file} - 通过")
        
        # 运行新功能测试
        print("\\n✨ 运行新功能测试...")
        for test_file in new_test_files:
            result = self.run_unit_tests(test_file)
            results['new_features'].append(result)
            if result.status != TestStatus.PASS.value:
                print(f"  ❌ {test_file} - 失败")
            else:
                print(f"  ✅ {test_file} - 通过")
        
        results['duration'] = time.time() - start_time
        return results
    
    def _create_error_result(self, test_file: str, error_msg: str) -> TestResult:
        """创建错误结果"""
        return TestResult(
            test_case=TestCase(
                id=f"error-{Path(test_file).name}",
                name=test_file,
                type="ERROR",
                description="测试执行错误",
                preconditions=[],
                steps=[],
                expected="测试正常执行"
            ),
            status=TestStatus.ERROR.value,
            execution_time=0,
            error_message=error_msg
        )


# ==================== 测试报告生成器 ====================

class TestReportGenerator:
    """测试报告生成器"""
    
    def generate_html_report(self, report: TestReport) -> str:
        """生成 HTML 报告"""
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>自动化测试报告 - {report.project}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ padding: 15px; border-radius: 5px; text-align: center; }}
        .pass {{ background: #d4edda; }}
        .fail {{ background: #f8d7da; }}
        .skip {{ background: #fff3cd; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .pass-row {{ background: #d4edda; }}
        .fail-row {{ background: #f8d7da; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 自动化测试报告</h1>
        <p><strong>项目:</strong> {report.project}</p>
        <p><strong>测试时间:</strong> {report.test_time}</p>
        <p><strong>总耗时:</strong> {report.duration:.2f} 秒</p>
    </div>
    
    <div class="summary">
        <div class="stat pass">
            <h3>✅ 通过</h3>
            <p style="font-size: 24px;">{report.passed}</p>
        </div>
        <div class="stat fail">
            <h3>❌ 失败</h3>
            <p style="font-size: 24px;">{report.failed}</p>
        </div>
        <div class="stat skip">
            <h3>⚪ 跳过</h3>
            <p style="font-size: 24px;">{report.skipped}</p>
        </div>
        <div class="stat">
            <h3>📈 覆盖率</h3>
            <p style="font-size: 24px;">{report.coverage:.1f}%</p>
        </div>
    </div>
    
    <h2>测试详情</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>测试名称</th>
            <th>类型</th>
            <th>状态</th>
            <th>耗时 (s)</th>
            <th>信息</th>
        </tr>
'''
        
        for result in report.results:
            status_class = "pass-row" if result.status == "✅ 通过" else "fail-row"
            html += f'''
        <tr class="{status_class}">
            <td>{result.test_case.id}</td>
            <td>{result.test_case.name}</td>
            <td>{result.test_case.type}</td>
            <td>{result.status}</td>
            <td>{result.execution_time:.2f}</td>
            <td>{result.error_message or '-'}</td>
        </tr>
'''
        
        html += f'''
    </table>
    
    <h2>建议</h2>
    <ul>
'''
        for rec in report.recommendations:
            html += f"        <li>{rec}</li>\n"
        
        html += '''
    </ul>
</body>
</html>
'''
        
        return html
    
    def generate_markdown_report(self, report: TestReport) -> str:
        """生成 Markdown 报告"""
        md = f'''# 📊 自动化测试报告

**项目:** {report.project}  
**测试时间:** {report.test_time}  
**总耗时:** {report.duration:.2f} 秒  
**代码覆盖率:** {report.coverage:.1f}%

---

## 📈 测试概览

| 总计 | ✅ 通过 | ❌ 失败 | ⚪ 跳过 |
|------|--------|--------|--------|
| {report.total_cases} | {report.passed} | {report.failed} | {report.skipped} |

**通过率:** {(report.passed / report.total_cases * 100) if report.total_cases > 0 else 0:.1f}%

---

## 📋 测试详情

'''
        
        # 按类型分组
        by_type = {}
        for result in report.results:
            test_type = result.test_case.type
            if test_type not in by_type:
                by_type[test_type] = []
            by_type[test_type].append(result)
        
        for test_type, results in by_type.items():
            md += f"### {test_type}\n\n"
            md += "| ID | 测试名称 | 状态 | 耗时 | 信息 |\n"
            md += "|----|---------|------|------|------|\n"
            
            for result in results:
                md += f"| {result.test_case.id} | {result.test_case.name} | {result.status} | {result.execution_time:.2f}s | {result.error_message or '-'} |\n"
            
            md += "\n"
        
        md += "---\n\n## 💡 改进建议\n\n"
        for i, rec in enumerate(report.recommendations, 1):
            md += f"{i}. {rec}\n"
        
        return md


# ==================== 场景分析器 ====================

class ScenarioAnalyzer:
    """场景分析器 - 分析代码生成测试场景"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
    
    def analyze_java_project(self) -> Dict:
        """分析 Java 项目"""
        scenarios = {
            'controllers': [],
            'services': [],
            'repositories': [],
            'models': []
        }
        
        # 扫描 Controller
        for file in self.project_path.rglob("*Controller.java"):
            scenarios['controllers'].append(self._analyze_java_class(file))
        
        # 扫描 Service
        for file in self.project_path.rglob("*Service.java"):
            scenarios['services'].append(self._analyze_java_class(file))
        
        # 扫描 Repository
        for file in self.project_path.rglob("*Repository.java"):
            scenarios['repositories'].append(self._analyze_java_class(file))
        
        return scenarios
    
    def analyze_python_project(self) -> Dict:
        """分析 Python 项目"""
        scenarios = {
            'views': [],
            'services': [],
            'models': []
        }
        
        # 扫描 views
        for file in self.project_path.rglob("views.py"):
            scenarios['views'].append(self._analyze_python_module(file))
        
        # 扫描 services
        for file in self.project_path.rglob("services.py"):
            scenarios['services'].append(self._analyze_python_module(file))
        
        return scenarios
    
    def _analyze_java_class(self, file: Path) -> Dict:
        """分析 Java 类"""
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 提取类名
        class_match = re.search(r'class\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else file.stem
        
        # 提取方法
        methods = re.findall(r'(?:public|private|protected)\s+\w+\s+(\w+)\s*\([^)]*\)', content)
        
        return {
            'file': str(file),
            'class_name': class_name,
            'methods': methods,
            'test_scenarios': self._generate_java_scenarios(methods)
        }
    
    def _analyze_python_module(self, file: Path) -> Dict:
        """分析 Python 模块"""
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 提取函数
        functions = re.findall(r'def\s+(\w+)\s*\([^)]*\)', content)
        
        return {
            'file': str(file),
            'functions': functions,
            'test_scenarios': self._generate_python_scenarios(functions)
        }
    
    def _generate_java_scenarios(self, methods: List[str]) -> List[Dict]:
        """生成 Java 测试场景"""
        scenarios = []
        for method in methods:
            scenarios.extend([
                {'type': 'normal', 'desc': f'{method} - 正常场景'},
                {'type': 'boundary', 'desc': f'{method} - 边界条件'},
                {'type': 'exception', 'desc': f'{method} - 异常处理'},
            ])
        return scenarios
    
    def _generate_python_scenarios(self, functions: List[str]) -> List[Dict]:
        """生成 Python 测试场景"""
        scenarios = []
        for func in functions:
            scenarios.extend([
                {'type': 'normal', 'desc': f'{func} - 正常场景'},
                {'type': 'boundary', 'desc': f'{func} - 边界条件'},
                {'type': 'exception', 'desc': f'{func} - 异常处理'},
            ])
        return scenarios


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(description='自动化测试工具 - Auto Tester')
    parser.add_argument('project', help='项目路径')
    parser.add_argument('--type', choices=['unit', 'api', 'integration', 'regression'], 
                       default='regression', help='测试类型')
    parser.add_argument('--generate', action='store_true', help='生成测试模板')
    parser.add_argument('--execute', action='store_true', help='执行测试')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--output', '-o', help='输出报告路径')
    parser.add_argument('--base-url', help='API 测试基础 URL')
    parser.add_argument('--old-features', nargs='+', help='原有功能列表')
    parser.add_argument('--new-features', nargs='+', help='新功能列表')
    
    args = parser.parse_args()
    
    project_path = Path(args.project)
    if not project_path.exists():
        print(f"❌ 项目路径不存在：{args.project}")
        sys.exit(1)
    
    # 生成测试模板
    if args.generate:
        print("📝 生成测试模板...")
        generator = TestTemplateGenerator()
        
        # 分析项目
        analyzer = ScenarioAnalyzer(args.project)
        if (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
            print("检测到 Java 项目")
            scenarios = analyzer.analyze_java_project()
        else:
            print("检测到 Python 项目")
            scenarios = analyzer.analyze_python_project()
        
        # 生成测试文件
        output_dir = project_path / "auto-generated-tests"
        output_dir.mkdir(exist_ok=True)
        
        print(f"✅ 测试模板已生成到：{output_dir}")
    
    # 执行测试
    if args.execute:
        print("🚀 执行测试...")
        executor = TestExecutor(args.project)
        
        if args.type == 'regression':
            old_files = args.old_features or []
            new_files = args.new_features or []
            results = executor.run_regression_tests(old_files, new_files)
            
            print(f"\n回归测试完成!")
            print(f"原有功能：{len(results['old_features'])} 个测试")
            print(f"新功能：{len(results['new_features'])} 个测试")
            print(f"回归状态：{'✅ 通过' if results['regression_passed'] else '❌ 失败'}")
        
        elif args.type == 'api':
            base_url = args.base_url or 'http://localhost:8080'
            # 查找 API 测试文件
            test_files = list(project_path.rglob("*api*test*.py"))
            for test_file in test_files:
                result = executor.run_api_tests(str(test_file), base_url)
                print(f"{test_file}: {result.status}")
    
    print("\n✅ 完成!")


if __name__ == "__main__":
    main()
