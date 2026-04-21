# 验证规则说明

## 必填项规则（70 分）

### 1. 任务类型标记（14 分）

**要求**: 必须包含任务类型标记

**有效标记**:
- 🆕 新增
- 🔄 优化
- ♻️ 复用
- 🗑️ 删除
- 🔗 对接

**示例**:
```markdown
### 1.1 技能列表查询接口 🆕新增
```

---

### 2. 依赖关系（14 分）

**要求**: 必须说明依赖关系

**示例**:
```markdown
**依赖**: 无
**依赖**: 1.1 技能列表查询接口
```

---

### 3. 接口定义完整性（14 分）

**要求**: 必须包含以下 4 项：
- URL（接口地址）
- 请求参数
- 返回数据
- 错误码

**示例**:
```markdown
**URL**: `POST /api/test`

**请求参数**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | number | 是 | 页码 |

**返回数据**:
```json
{"code": 200, "data": {...}}
```

**错误码**:
| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
```

---

### 4. 实现说明具体性（14 分）

**要求**: 必须精确到文件和方法

**示例**:
```markdown
1. ✅ 新建 `SkillController.java`
   - 路径：`yun-ai-api-openclaw/src/main/java/com/xxx/controller/SkillController.java`
   - 方法：`list(@RequestBody SkillListRequest request)`

2. ✅ 新建 `SkillService.java`
   - 路径：`yun-ai-api-openclaw/src/main/java/com/xxx/service/SkillService.java`
```

---

### 5. 验收标准可执行性（14 分）

**要求**: 必须包含可执行的检查项和指标

**示例**:
```markdown
#### 验收标准

- [ ] 接口可正常调用，返回 HTTP 200
- [ ] 必填参数缺失时返回 HTTP 400
- [ ] 分页参数生效
- [ ] 响应时间 < 200ms（P95）
- [ ] 无技能时返回空列表
```

---

## 加分项规则（30 分）

### 1. 工作量评估（10 分）

**示例**:
```markdown
**工作量**: 2 人天（开发 1 天 + 测试 0.5 天 + 联调 0.5 天）
```

---

### 2. 优先级标注（10 分）

**示例**:
```markdown
**优先级**: P0
```

---

### 3. 业务背景（10 分）

**示例**:
```markdown
#### 业务背景

用户在技能管理页面需要查看技能列表...
```

---

## 模糊词规则

### 常见模糊词

| 模糊词 | 建议修改为 |
|--------|-----------|
| 优化一下 | 添加索引，查询时间从 2s 降低到 200ms |
| 大概 | 删除或给出具体数字 |
| 左右 | 删除或给出具体范围 |
| 很快 | <100ms 或 实时 |
| 大量 | >1000 条 或 QPS>100 |
| 考虑扩展性 | 预留 2 个扩展字段，支持... |
| 处理异常 | 捕获 TimeoutException，返回 503 |

---

## JAVA 特定规则

### 文件路径规范

```
项目名/src/main/java/com/xxx/controller/XxxController.java
项目名/src/main/java/com/xxx/service/XxxService.java
项目名/src/main/resources/mapper/XxxMapper.xml
```

### 类命名规范

- Controller: `XxxController`
- Service: `XxxService`
- Mapper: `XxxMapper`
- Request: `XxxRequest`
- Response: `XxxResponse`
- DO: `XxxDO`
- DTO: `XxxDTO`
