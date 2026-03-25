# 团队分发与反馈闭环方案

> 完整解决：在线分发 → 使用反馈 → 版本更新 → 自动通知

---

## 🎯 方案总览

| 环节 | 方案 | 工具 |
|------|------|------|
| **代码托管** | Git 仓库 | GitLab / Gitee / GitHub |
| **分发渠道** | 云文档 + 群公告 | 飞书云文档 |
| **反馈收集** | 表单 + Issue | 飞书表单 + Git Issue |
| **版本管理** | 语义化版本 | Git Tag |
| **更新通知** | 机器人消息 | 飞书机器人 |
| **更新检查** | 自动脚本 | check-update.sh |

---

## 📦 一、在线分发方案

### 方案 A：Git 仓库（推荐）⭐

**优点：**
- ✅ 版本管理清晰
- ✅ 更新方便（git pull）
- ✅ 可追溯变更历史
- ✅ 支持 Issue 跟踪

**配置步骤：**

```bash
# 1. 创建仓库（GitLab/Gitee/GitHub）
# 2. 推送代码
cd /home/admin/.openclaw/workspace
git init
git add .
git commit -m "Initial release: v1.0.0"
git remote add origin https://gitlab.com/your-team/openclaw-skills.git
git push -u origin main

# 3. 创建版本标签
git tag -a v1.0.0 -m "初始版本"
git push origin v1.0.0
```

**团队成员安装：**

```bash
# 方式 1：Git 克隆
git clone https://gitlab.com/your-team/openclaw-skills.git
cd openclaw-skills
./setup-team-env.sh

# 方式 2：ZIP 下载
# 仓库 → 下载 ZIP → 解压 → 运行 setup-team-env.sh
```

---

### 方案 B：飞书云盘

**优点：**
- ✅ 无需 Git 账号
- ✅ 下载速度快
- ✅ 权限可控

**配置步骤：**

1. 打包技能目录：
```bash
cd /home/admin/.openclaw/workspace
tar -czf openclaw-skills-v1.0.0.tar.gz \
    setup-team-env.sh skills/ docs/ TEAM-SETUP-README.md
```

2. 上传到飞书云盘 → 创建分享链接

3. 设置权限：团队内可见/指定人可见

**缺点：**
- ❌ 版本管理不便
- ❌ 更新需重新下载

---

### 方案 C：内部服务器

**适用场景：** 有内网服务器的团队

```bash
# 在服务器上配置 HTTP 下载
sudo mkdir -p /var/www/html/openclaw-skills
sudo cp -r /home/admin/.openclaw/workspace/* /var/www/html/openclaw-skills/

# 团队成员下载
wget http://your-server/openclaw-skills/openclaw-skills-v1.0.0.tar.gz
```

---

## 📢 二、分发渠道

### 飞书云文档（推荐）

创建《OpenClaw 开发工具包使用指南》云文档：

**文档结构：**

```markdown
# 🦞 OpenClaw 开发工具包

## 📥 下载安装

### 方式 1：Git 克隆（推荐）
[安装步骤]

### 方式 2：ZIP 下载
[下载链接]

## 📋 版本信息

| 版本 | 日期 | 更新内容 | 状态 |
|------|------|---------|------|
| v1.0.0 | 2026-03-25 | 初始版本 | ✅ 稳定 |

## 🔄 更新方法

[更新步骤]

## 📞 问题反馈

[反馈表单二维码]
[Issue 链接]

## 📖 使用文档

- [IDEA 配置指南](docs/idea-plugin-setup.md)
- [Code Reviewer 文档](skills/code-reviewer/SKILL.md)
- [Auto Tester 文档](skills/auto-tester/SKILL.md)
```

**发布到团队群：**
- 群公告置顶
- @所有人 通知

---

## 📝 三、反馈收集

### 方式 A：飞书表单（推荐）⭐

**创建步骤：**

1. 飞书 → 云文档 → 新建 → 表单

2. 按模板添加问题（见 `docs/feedback-form-template.md`）

3. 配置通知：
   - 设置 → 通知设置 → 飞书机器人
   - 选择管理群 → 提交后自动通知

4. 生成分享链接和二维码

**表单问题设计：**

| 问题 | 类型 | 必填 |
|------|------|------|
| 姓名 | 填空 | ✅ |
| 部门 | 单选 | ✅ |
| 问题类型 | 多选 | ✅ |
| 版本号 | 填空 | ✅ |
| IDEA 版本 | 填空 | ✅ |
| 问题描述 | 多行 | ✅ |
| 截图 | 上传 | ❌ |
| 紧急程度 | 单选 | ✅ |

---

### 方式 B：Git Issue

**适用场景：** 技术团队，熟悉 Git 流程

**配置步骤：**

1. 启用仓库 Issue 功能

2. 创建 Issue 模板（已创建）：
   - `.github/ISSUE_TEMPLATE/bug-report.md`
   - `.github/ISSUE_TEMPLATE/feature-request.md`

3. 设置标签：
   - `bug` - 缺陷
   - `enhancement` - 功能建议
   - `help wanted` - 需要帮助
   - `wontfix` - 暂不修复

---

### 方式 C：飞书群机器人

**配置步骤：**

1. 飞书群 → 群设置 → 机器人 → 添加机器人

2. 选择"自定义机器人"

3. 获取 Webhook URL

4. 配置反馈接收：

```python
# 示例：接收反馈并转发到管理群
@app.route('/feedback', methods=['POST'])
def receive_feedback():
    data = request.json
    # 处理反馈内容
    # 发送到管理群
    requests.post(MANAGEMENT_WEBHOOK, json={
        "msg_type": "text",
        "content": {
            "text": f"新反馈：{data['description']}"
        }
    })
```

---

## 🔄 四、版本更新流程

### 发布新版本

**使用发布脚本：**

```bash
cd /home/admin/.openclaw/workspace/skills
chmod +x release.sh
./release.sh
```

**交互式发布：**
```
🦞 OpenClaw Skills 版本发布工具
================================

📦 当前版本：v1.0.0

请输入新版本号 (例如：v1.1.0): v1.1.0

请输入更新说明（多行，空行结束）：
- 新增 XX 规则检测
- 修复 YY 误报问题
- 优化扫描性能

📋 发布确认：
  新版本：v1.1.0
  更新说明：- 新增 XX 规则检测

确认发布？[y/N] y

✅ 发布成功！
```

**自动完成：**
- ✅ 创建 Git Tag
- ✅ 推送远程
- ✅ 生成发布说明
- ✅ 输出通知模板

---

### 通知团队更新

**飞书群消息模板：**

```
🦞 OpenClaw Skills 更新通知

新版本：v1.1.0
发布日期：2026-04-01

更新内容：
• 新增 XX 规则检测
• 修复 YY 误报问题
• 优化扫描性能

更新方法：
```bash
cd openclaw-skills
git pull origin main
./setup-team-env.sh
```

然后重启 IDEA

详细发布说明：[链接]

遇到问题请反馈：[表单链接]
```

---

### 团队成员更新

**方式 1：自动检查**

```bash
cd openclaw-skills
chmod +x check-update.sh
./check-update.sh
```

**输出示例：**
```
🦞 检查更新...

📦 当前版本：v1.0.0 (a1b2c3d)
📦 最新版本：v1.1.0

🆕 发现新版本！

📋 更新内容：
- 新增 XX 规则检测
- 修复 YY 误报问题

是否立即更新？[y/N] y

🔄 正在更新...
✅ 更新完成！

请重新运行配置脚本：
  ./setup-team-env.sh

然后重启 IDEA
```

**方式 2：手动更新**

```bash
cd openclaw-skills
git pull origin main
./setup-team-env.sh
```

---

## 📊 五、反馈处理流程

```
┌─────────────────┐
│  用户提交反馈   │
│  (表单/Issue)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  飞书机器人通知 │
│  (管理群)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  管理员分类处理 │
├─────────────────┤
│ • Bug → Issue   │
│ • 建议 → 需求池 │
│ • 咨询 → 回复   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  开发修复       │
│  创建新版本     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  发布并通知     │
│  @反馈用户      │
└─────────────────┘
```

---

## 🛠️ 六、自动化增强

### 飞书机器人自动通知

**配置步骤：**

1. 飞书开放平台 → 创建应用 → 添加机器人能力

2. 获取 App ID 和 App Secret

3. 配置事件订阅：
   - 表单提交事件
   - Issue 创建事件

4. 编写处理逻辑：

```python
# 示例：表单提交后自动创建 Issue
def on_form_submit(data):
    title = f"[BUG] {data['issue_type']} - {data['name']}"
    body = f"""
## 反馈信息
- **姓名:** {data['name']}
- **部门:** {data['department']}
- **版本:** {data['version']}
- **问题:** {data['description']}
"""
    # 调用 GitLab API 创建 Issue
    create_issue(title, body, labels=['bug'])
```

---

### 版本统计看板

**使用飞书多维表格：**

1. 创建表格《问题反馈跟踪》

2. 字段设计：
   - 反馈 ID（自动编号）
   - 提交人（文本）
   - 问题类型（单选）
   - 紧急程度（单选）
   - 状态（单选：待处理/处理中/已解决/已关闭）
   - 关联 Issue（链接）
   - 解决版本（文本）
   - 提交时间（日期）

3. 配置自动化：
   - 表单提交 → 自动新增记录
   - 状态变更 → 通知提交人

---

## 📋 七、完整实施清单

### 管理员配置

- [ ] 创建 Git 仓库
- [ ] 推送初始代码
- [ ] 创建 v1.0.0 标签
- [ ] 创建飞书云文档（使用指南）
- [ ] 创建飞书反馈表单
- [ ] 配置飞书机器人通知
- [ ] 发布到团队群

### 团队成员

- [ ] 阅读云文档
- [ ] 克隆/下载技能包
- [ ] 运行 `setup-team-env.sh`
- [ ] 重启 IDEA 验证
- [ ] 加入反馈群（可选）

---

## 🎯 推荐方案组合

| 团队规模 | 推荐方案 |
|---------|---------|
| **< 10 人** | Git 仓库 + 飞书表单 + 群通知 |
| **10-50 人** | Git 仓库 + 飞书表单 + 机器人通知 + 多维表格 |
| **> 50 人** | Git 仓库 + Issue 系统 + 自动化看板 + 专职维护 |

---

## 📞 技术支持

- 配置问题：`docs/idea-plugin-setup.md`
- 反馈模板：`docs/feedback-form-template.md`
- 发布脚本：`skills/release.sh`
- 更新检查：`skills/check-update.sh`

---

*最后更新：2026-03-25*
