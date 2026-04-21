# 技术方案测试文档（合格）

**版本**: v1.0  
**创建时间**: 2026-04-18

---

### 1.1 技能列表查询接口 🆕新增

**任务类型**: 🆕新增接口  
**工作量**: 2 人天（开发 1 天 + 测试 0.5 天 + 联调 0.5 天）  
**优先级**: P0  
**依赖**: 无

#### 业务背景

用户在技能管理页面需要查看已安装和可安装的技能列表，支持分页和搜索。

#### 接口定义

**URL**: `POST /api/openclaw/skill/list`

**请求参数**:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | number | 是 | 1 | 页码 |
| size | number | 是 | 20 | 每页数量 |
| keyword | string | 否 | - | 搜索关键词 |

**返回数据**:

```json
{
  "code": 200,
  "data": {
    "total": 100,
    "list": [{"skillId": "sk_001", "name": "OCR"}]
  }
}
```

**错误码**:

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 500 | 服务器错误 |

#### 实现说明

1. ✅ 新建 `SkillController.java`
   - 路径：`yun-ai-api-openclaw/src/main/java/com/xxx/controller/SkillController.java`
   - 方法：`list(@RequestBody SkillListRequest request)`

2. ✅ 新建 `SkillService.java`
   - 路径：`yun-ai-api-openclaw/src/main/java/com/xxx/service/SkillService.java`

3. ✅ 新建 `SkillMapper.xml`
   - 路径：`yun-ai-api-openclaw/src/main/resources/mapper/SkillMapper.xml`

#### 数据库变更

```sql
CREATE TABLE `skill` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `skill_id` varchar(64) NOT NULL,
  `name` varchar(128) NOT NULL,
  PRIMARY KEY (`id`)
);
```

#### 验收标准

- [ ] 接口可正常调用，返回 HTTP 200
- [ ] 必填参数缺失时返回 HTTP 400
- [ ] 分页参数生效
- [ ] 响应时间 < 200ms（P95）
- [ ] 无技能时返回空列表
