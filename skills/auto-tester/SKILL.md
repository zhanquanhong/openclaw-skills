---
name: auto-tester
description: 自动化测试工具。支持回归测试、场景覆盖、API 测试、单元测试生成。自动分析代码生成测试用例，确保新功能不影响原有功能。适用于 Java/Python 项目，跨平台支持 Windows/Mac/Linux。
---

# 自动化测试工具 - Auto Tester

> 确保每个需求都有完整的自动化测试覆盖，新功能不影响旧功能

**支持语言:** Java (JUnit 5), Python (pytest/unittest)  
**构建工具:** Maven, Gradle, pip  
**测试框架:** JUnit 5, pytest, unittest, TestNG

---

## 🎯 核心能力

| 能力 | Java 支持 | Python 支持 | 适用场景 |
|------|---------|-----------|---------|
| 📝 测试生成 | ✅ JUnit 5 | ✅ pytest | 新需求开发 |
| 🔄 回归测试 | ✅ Maven/Gradle | ✅ pytest | 功能优化/重构 |
| 🎭 场景覆盖 | ✅ 正常/边界/异常 | ✅ 正常/边界/异常 | 完整测试 |
| 🔌 API 测试 | ✅ RestAssured | ✅ requests | 后端服务 |
| 📊 测试报告 | ✅ HTML/XML | ✅ HTML/XML | 测试总结 |
| 📈 覆盖率 | ✅ JaCoCo | ✅ coverage | 质量评估 |

---

## 🚀 快速开始

### 方式 1：生成测试模板

```bash
# 分析项目并生成测试模板
python scripts/auto-tester.py /path/to/project --generate

# 生成特定类型的测试
python scripts/auto-tester.py /path/to/project --generate --type regression
```

### 方式 2：执行回归测试

```bash
# 执行回归测试
python scripts/auto-tester.py /path/to/project \
  --execute \
  --type regression \
  --old-features test_existing_*.py \
  --new-features test_new_*.py
```

### 方式 3：执行 API 测试

```bash
# 执行 API 测试
python scripts/auto-tester.py /path/to/project \
  --execute \
  --type api \
  --base-url http://localhost:8080
```

### 方式 4：生成测试报告

```bash
# 执行测试并生成报告
python scripts/auto-tester.py /path/to/project \
  --execute \
  --coverage \
  --output report.html
```

---

## 📋 完整工作流

### 新需求开发测试流程

```
1. 需求分析 → 2. 生成测试 → 3. 编写实现 → 4. 执行测试 → 5. 生成报告
```

#### 步骤 1：需求分析

```bash
# 分析项目结构
python scripts/auto-tester.py /path/to/project --analyze
```

输出：
```
📊 项目分析结果

原有功能点：
- 用户登录
- 订单创建
- 支付处理

新增功能点：
- 优惠券系统
- 积分奖励
```

#### 步骤 2：生成测试模板

```bash
# 生成回归测试模板
python scripts/auto-tester.py /path/to/project \
  --generate \
  --old-features "用户登录，订单创建，支付处理" \
  --new-features "优惠券系统，积分奖励"
```

生成文件：
```
auto-generated-tests/
├── test_regression.py          # 回归测试
├── test_new_features.py        # 新功能测试
├── test_api.py                 # API 测试
└── test_scenarios.py           # 场景测试
```

#### 步骤 3：完善测试用例

编辑生成的测试文件，填充具体测试数据：

```python
# test_new_features.py

def test_coupon_creation_normal(self):
    """测试优惠券创建 - 正常场景"""
    # Arrange
    coupon_data = {
        "code": "SAVE20",
        "discount": 20,
        "valid_days": 30
    }
    
    # Act
    result = self.coupon_service.create(coupon_data)
    
    # Assert
    self.assertIsNotNone(result.id)
    self.assertEqual(result.code, "SAVE20")
```

#### 步骤 4：执行测试

```bash
# 执行所有测试
python scripts/auto-tester.py /path/to/project \
  --execute \
  --type regression \
  --coverage
```

#### 步骤 5：查看报告

```bash
# 生成 HTML 报告
python scripts/auto-tester.py /path/to/project \
  --execute \
  --output report.html

# 打开报告
open report.html  # macOS
xdg-open report.html  # Linux
start report.html  # Windows
```

---

## 🎭 测试场景覆盖

### 场景分类

| 场景类型 | 说明 | 示例 |
|---------|------|------|
| 正常场景 | 符合预期的输入 | 有效用户登录 |
| 边界场景 | 临界值测试 | 密码长度限制 |
| 异常场景 | 错误处理 | 无效 token |
| 集成场景 | 多模块协作 | 下单 + 支付 |
| 回归场景 | 原有功能验证 | 登录功能不受影响 |

### 自动生成场景

```bash
# 分析代码自动生成测试场景
python scripts/auto-tester.py /path/to/project --analyze-scenarios
```

输出示例：
```
📋 测试场景分析

UserService 类:
  ✅ login - 正常场景
  ✅ login - 边界条件 (空密码/超长密码)
  ✅ login - 异常处理 (无效用户)
  ✅ createUser - 正常场景
  ✅ createUser - 边界条件
  ✅ createUser - 异常处理

OrderService 类:
  ✅ createOrder - 正常场景
  ✅ createOrder - 边界条件 (库存不足)
  ✅ createOrder - 异常处理 (支付失败)
```

---

## 🔄 回归测试策略

### 回归测试层级

```
Level 1: 单元测试回归 (最快)
    ↓
Level 2: 集成测试回归
    ↓
Level 3: API 测试回归
    ↓
Level 4: E2E 测试回归 (最慢)
```

### 回归测试配置

```bash
# 创建回归测试配置文件
cat > regression-config.json << 'EOF'
{
  "project": "your-project",
  "old_features": [
    "test_user_login.py",
    "test_order_create.py",
    "test_payment.py"
  ],
  "new_features": [
    "test_coupon.py",
    "test_points.py"
  ],
  "integration_tests": [
    "test_order_flow.py",
    "test_payment_flow.py"
  ],
  "execution_order": [
    "old_features",
    "new_features",
    "integration_tests"
  ]
}
EOF

# 执行回归测试
python scripts/auto-tester.py /path/to/project \
  --execute \
  --config regression-config.json
```

### 回归测试报告

```markdown
# 🔄 回归测试报告

## 测试结果

| 类别 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| 原有功能 | 50 | 50 | 0 | 100% |
| 新功能 | 20 | 18 | 2 | 90% |
| 集成测试 | 10 | 10 | 0 | 100% |

## 失败用例

1. test_coupon_invalid_code - 优惠券码验证逻辑错误
2. test_points_calculation - 积分计算精度问题

## 建议

1. 修复失败用例后再部署
2. 原有功能 100% 通过，可以安全发布
```

---

## 🔌 API 测试

### 生成 API 测试

```bash
# 从 OpenAPI/Swagger 生成测试
python scripts/auto-tester.py /path/to/project \
  --generate-api-tests \
  --spec api-spec.yaml
```

### API 测试模板

```python
# test_api.py

class UserAPITest(unittest.TestCase):
    
    def test_login_success(self):
        """登录 API - 成功"""
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "test", "password": "123456"}
        )
        assert response.status_code == 200
        assert "token" in response.json()
    
    def test_login_invalid_password(self):
        """登录 API - 密码错误"""
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "test", "password": "wrong"}
        )
        assert response.status_code == 401
    
    def test_login_rate_limit(self):
        """登录 API - 频率限制"""
        for i in range(10):
            response = requests.post(
                f"{BASE_URL}/api/login",
                json={"username": "test", "password": "wrong"}
            )
        assert response.status_code == 429
```

### 执行 API 测试

```bash
# 执行 API 测试
python scripts/auto-tester.py /path/to/project \
  --execute \
  --type api \
  --base-url http://localhost:8080 \
  --output api-report.html
```

---

## 📊 测试报告

### 报告类型

| 类型 | 格式 | 用途 |
|------|------|------|
| HTML 报告 | .html | 可视化查看 |
| Markdown 报告 | .md | 文档记录 |
| JSON 报告 | .json | 机器处理 |
| JUnit 报告 | .xml | CI/CD 集成 |

### 报告内容

```markdown
# 📊 自动化测试报告

**项目:** your-project  
**测试时间:** 2026-03-18 14:44:00  
**总耗时:** 125.5 秒  
**代码覆盖率:** 85.3%

## 测试概览

| 总计 | ✅ 通过 | ❌ 失败 | ⚪ 跳过 |
|------|--------|--------|--------|
| 150 | 145 | 3 | 2 |

**通过率:** 96.7%

## 问题汇总

### 失败用例

1. test_coupon_calculation - 优惠券计算精度错误
2. test_points_expiry - 积分过期逻辑问题
3. test_api_timeout - API 超时处理不当

### 改进建议

1. 修复优惠券计算的浮点数精度问题
2. 添加积分过期的边界测试
3. 增加 API 超时重试机制
```

---

## 🔧 CI/CD 集成

### GitHub Actions

```yaml
name: Automated Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r test-requirements.txt
      
      - name: Generate tests
        run: |
          python scripts/auto-tester.py . --generate
      
      - name: Run regression tests
        run: |
          python scripts/auto-tester.py . \
            --execute \
            --type regression \
            --coverage \
            --output test-report.html
      
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: test-report.html
      
      - name: Check regression
        run: |
          if [ $(grep -c "❌ 失败" test-report.html) -gt 0 ]; then
            echo "回归测试失败，存在功能回退"
            exit 1
          fi
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Generate Tests') {
            steps {
                sh 'python scripts/auto-tester.py . --generate'
            }
        }
        
        stage('Run Tests') {
            steps {
                sh '''
                    python scripts/auto-tester.py . \\
                        --execute \\
                        --type regression \\
                        --output test-report.html
                '''
            }
            post {
                always {
                    junit 'test-results/*.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'test-report.html',
                        reportName: 'Test Report'
                    ])
                }
            }
        }
        
        stage('Quality Gate') {
            steps {
                script {
                    def report = readFile 'test-report.html'
                    if (report.contains('❌ 失败')) {
                        error '回归测试失败!'
                    }
                }
            }
        }
    }
}
```

---

## 💡 最佳实践

### 1. 测试金字塔

```
        /\
       /  \
      / E2E \      少量 (10%)
     /--------\
    /Integration\   适量 (30%)
   /--------------\
  /    Unit Tests  \ 大量 (60%)
 /------------------\
```

### 2. 测试命名规范

```python
# 好：清晰描述测试内容
def test_login_with_valid_credentials_returns_token()
def test_login_with_invalid_password_returns_401()
def test_create_order_when_inventory_insufficient_raises_error()

# 不好：过于简单
def test_login()
def test_order()
```

### 3. 测试数据管理

```python
# 使用工厂模式创建测试数据
class TestDataFactory:
    @staticmethod
    def create_user(**kwargs):
        defaults = {
            'username': 'testuser',
            'password': 'SecurePass123',
            'email': 'test@example.com'
        }
        defaults.update(kwargs)
        return User(**defaults)

# 测试中使用
def test_user_login(self):
    user = TestDataFactory.create_user(password='Test123')
```

### 4. 测试隔离

```python
# 每个测试独立，不依赖其他测试
def test_create_user(self):
    user = self.create_user()
    # 测试创建逻辑

def test_delete_user(self):
    user = self.create_user()
    # 测试删除逻辑，不依赖 test_create_user
```

---

## 📖 参考文档

| 文档 | 说明 |
|------|------|
| `references/test-strategies.md` | 测试策略详解 |
| `references/ci-cd-integration.md` | CI/CD 集成指南 |
| `references/best-practices.md` | 最佳实践 |
| `test-templates/` | 测试模板示例 |

---

## ⚠️ 注意事项

1. **不要过度测试** - 关注核心业务逻辑
2. **定期维护** - 删除过时的测试用例
3. **快速反馈** - 测试执行时间控制在 10 分钟内
4. **稳定优先** - 避免 flaky tests（不稳定测试）
5. **文档同步** - 测试即文档，保持更新

---

*适用于 Windows/Mac/Linux 全平台*
