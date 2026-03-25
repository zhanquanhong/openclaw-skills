# 自动化测试策略

## 测试分层策略

### 测试金字塔

```
           /\
          /  \
         /    \        E2E 测试 (5-10%)
        /------\       - 完整用户流程
       /        \      - 关键业务场景
      /          \     
     /------------\    集成测试 (20-30%)
    /              \   - 模块间交互
   /                \  - API 集成
  /------------------\  单元测试 (60-70%)
 /                    \ - 函数/方法级别
/                      \- 逻辑验证
```

### 各层级测试重点

#### 单元测试 (Unit Tests)

**目标:** 验证最小可测试单元

**测试内容:**
- 函数/方法的输入输出
- 边界条件
- 异常处理
- 逻辑分支覆盖

**示例:**
```python
def test_calculate_discount():
    # 正常场景
    assert calculate_discount(100, 10) == 90
    
    # 边界场景
    assert calculate_discount(100, 0) == 100
    assert calculate_discount(100, 100) == 0
    
    # 异常场景
    with pytest.raises(ValueError):
        calculate_discount(100, 101)  # 折扣超过 100%
```

#### 集成测试 (Integration Tests)

**目标:** 验证模块间交互

**测试内容:**
- 数据库交互
- API 调用
- 消息队列
- 缓存操作

**示例:**
```python
def test_order_creation_flow():
    # 创建订单
    order = order_service.create(user_id=1, items=[...])
    
    # 验证库存扣减
    inventory = db.query(Inventory).get(item_id)
    assert inventory.stock == original_stock - 1
    
    # 验证订单记录
    saved_order = db.query(Order).get(order.id)
    assert saved_order.status == 'PENDING'
```

#### E2E 测试 (End-to-End Tests)

**目标:** 验证完整用户流程

**测试内容:**
- 用户登录 → 浏览 → 下单 → 支付
- 关键业务闭环
- 跨系统集成

**示例:**
```python
def test_complete_purchase_flow():
    # 1. 用户登录
    login_page.open()
    login_page.login('user', 'password')
    
    # 2. 添加商品
    product_page.search('iPhone')
    product_page.add_to_cart(1)
    
    # 3. 结算
    cart_page.checkout()
    checkout_page.fill_address(...)
    
    # 4. 支付
    payment_page.pay()
    
    # 5. 验证
    assert confirmation_page.is_success()
```

---

## 回归测试策略

### 回归测试选择

| 变更类型 | 测试范围 | 执行频率 |
|---------|---------|---------|
| 修复 Bug | 相关功能 + 周边功能 | 每次提交 |
| 小功能 | 新功能 + 核心流程 | 每天 |
| 大功能 | 全量回归 | 每周/发布前 |
| 重构 | 全量回归 + 性能测试 | 发布前 |

### 回归测试优先级

```
P0: 核心业务流程 (必须 100% 通过)
    ↓
P1: 重要功能 (允许 <5% 失败)
    ↓
P2: 次要功能 (允许 <10% 失败)
    ↓
P3: 边缘功能 (参考用)
```

### 智能回归测试

```python
# 基于代码变更选择测试
def select_regression_tests(changed_files):
    test_mapping = {
        'user_service.py': ['test_user_*.py'],
        'order_service.py': ['test_order_*.py', 'test_payment_*.py'],
        'coupon_service.py': ['test_coupon_*.py', 'test_order_*.py'],
    }
    
    tests_to_run = set()
    for file in changed_files:
        for pattern, tests in test_mapping.items():
            if pattern in file:
                tests_to_run.update(tests)
    
    return list(tests_to_run)
```

---

## 场景覆盖策略

### 场景分类

#### 1. 正常场景 (Happy Path)

**定义:** 符合预期的标准流程

**覆盖要点:**
- 标准输入
- 预期输出
- 流程完整

**示例:**
```python
def test_normal_login():
    """用户正常登录"""
    user = create_user()
    result = login(user.username, user.password)
    assert result.success
    assert result.token is not None
```

#### 2. 边界场景 (Boundary Cases)

**定义:** 临界值测试

**覆盖要点:**
- 最小值/最大值
- 空值/null
- 长度限制
- 数量限制

**示例:**
```python
def test_password_boundary():
    """密码长度边界测试"""
    # 最小长度
    assert login('user', 'a' * 6).success  # 6 字符
    
    # 最大长度
    assert login('user', 'a' * 100).success  # 100 字符
    
    # 低于最小
    assert not login('user', 'a' * 5).success  # 5 字符
    
    # 超过最大
    assert not login('user', 'a' * 101).success  # 101 字符
```

#### 3. 异常场景 (Exception Cases)

**定义:** 错误处理和异常情况

**覆盖要点:**
- 无效输入
- 系统异常
- 网络异常
- 数据异常

**示例:**
```python
def test_exception_scenarios():
    """异常场景测试"""
    # 空密码
    with pytest.raises(ValidationError):
        login('user', '')
    
    # 不存在的用户
    with pytest.raises(UserNotFoundError):
        login('nonexistent', 'password')
    
    # 数据库异常
    mock_db.side_effect = DatabaseError()
    with pytest.raises(ServiceUnavailableError):
        login('user', 'password')
```

#### 4. 并发场景 (Concurrency Cases)

**定义:** 多线程/多用户场景

**覆盖要点:**
- 并发写入
- 资源竞争
- 死锁检测
- 数据一致性

**示例:**
```python
def test_concurrent_order_creation():
    """并发下单测试"""
    def place_order():
        return order_service.create(user_id=1, item_id=100)
    
    # 10 个并发请求
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(place_order) for _ in range(10)]
        results = [f.result() for f in futures]
    
    # 验证库存正确扣减
    inventory = db.query(Inventory).get(100)
    assert inventory.stock == original_stock - 10
```

---

## 测试数据管理

### 测试数据分类

| 类型 | 说明 | 示例 |
|------|------|------|
| 固定数据 | 不变的测试数据 | 配置常量 |
| 动态数据 | 每次测试生成 | 唯一 ID |
| 共享数据 | 多个测试共用 | 测试用户 |
| 隔离数据 | 单个测试专用 | 临时订单 |

### 数据工厂模式

```python
class TestDataFactory:
    """测试数据工厂"""
    
    _counter = 0
    
    @classmethod
    def create_user(cls, **kwargs):
        """创建用户数据"""
        cls._counter += 1
        defaults = {
            'id': cls._counter,
            'username': f'testuser_{cls._counter}',
            'email': f'test{cls._counter}@example.com',
            'password': 'TestPass123!',
            'status': 'active'
        }
        defaults.update(kwargs)
        return User(**defaults)
    
    @classmethod
    def create_order(cls, **kwargs):
        """创建订单数据"""
        defaults = {
            'user': kwargs.get('user') or cls.create_user(),
            'items': kwargs.get('items') or [],
            'status': 'pending',
            'created_at': datetime.now()
        }
        defaults.update(kwargs)
        return Order(**defaults)
```

### 数据清理策略

```python
class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self):
        self.created_records = []
    
    def create(self, model, **kwargs):
        """创建记录并追踪"""
        record = model.create(**kwargs)
        self.created_records.append((model, record.id))
        return record
    
    def cleanup(self):
        """清理所有创建的记录"""
        # 反向删除（避免外键约束）
        for model, record_id in reversed(self.created_records):
            try:
                model.delete(record_id)
            except Exception as e:
                print(f"清理失败：{model.__name__}.{record_id} - {e}")
        self.created_records.clear()


# 使用
def test_order_flow():
    manager = TestDataManager()
    try:
        user = manager.create(User, username='test')
        order = manager.create(Order, user=user)
        # ... 测试逻辑
    finally:
        manager.cleanup()
```

---

## 测试质量评估

### 覆盖率指标

| 指标 | 目标 | 说明 |
|------|------|------|
| 行覆盖率 | >80% | 代码行执行比例 |
| 分支覆盖率 | >70% | 条件分支覆盖比例 |
| 函数覆盖率 | >90% | 函数调用覆盖比例 |
| 场景覆盖率 | 100% | 所有场景都有测试 |

### 测试质量检查

```python
def check_test_quality(test_file):
    """检查测试质量"""
    issues = []
    
    with open(test_file) as f:
        content = f.read()
    
    # 检查断言
    if 'assert' not in content:
        issues.append("缺少断言")
    
    # 检查测试数据
    if not re.search(r'(input|expected|data|fixture)', content, re.I):
        issues.append("缺少测试数据定义")
    
    # 检查注释
    if not re.search(r'#|"""|'''', content):
        issues.append("缺少注释说明")
    
    # 检查命名
    if not re.search(r'def test_\w+_', content):
        issues.append("测试命名不规范")
    
    return issues
```

---

*最后更新：2026-03-18*
