# Git 仓库配置指南

> 快速配置并推送 OpenClaw Skills 到 Git 平台

---

## 📋 步骤 1：选择 Git 平台

推荐优先级：**GitLab > Gitee > GitHub**

| 平台 | 优势 | 适用场景 |
|------|------|---------|
| **GitLab** | 私有仓库免费、功能强大 | 企业团队首选 |
| **Gitee** | 国内访问快、中文界面 | 国内团队 |
| **GitHub** | 生态丰富、国际通用 | 开源项目 |

---

## 📋 步骤 2：创建仓库

### GitLab
1. 登录 https://gitlab.com
2. 点击右上角 **+** → **New project**
3. 选择 **Create blank project**
4. 填写：
   - **Project name:** `openclaw-skills`
   - **Project slug:** `openclaw-skills`（自动生成）
   - **Visibility:** **Private**（私有）
5. 点击 **Create project**

### Gitee
1. 登录 https://gitee.com
2. 点击右上角 **+** → **新建仓库**
3. 填写：
   - **仓库名称:** `openclaw-skills`
   - **仓库介绍:** OpenClaw 团队开发技能包
   - **开源协议:** 不选择
   - **是否开源:** 私有
4. 点击 **创建**

### GitHub
1. 登录 https://github.com
2. 点击右上角 **+** → **New repository**
3. 填写：
   - **Repository name:** `openclaw-skills`
   - **Description:** OpenClaw Team Skills
   - **Visibility:** **Private**
4. 点击 **Create repository**

---

## 📋 步骤 3：获取仓库地址

创建完成后，复制仓库的 **HTTPS 克隆地址**：

- **GitLab:** `https://gitlab.com/your-username/openclaw-skills.git`
- **Gitee:** `https://gitee.com/your-username/openclaw-skills.git`
- **GitHub:** `https://github.com/your-username/openclaw-skills.git`

---

## 📋 步骤 4：本地配置（待执行）

```bash
# 进入工作目录
cd /home/admin/.openclaw/workspace

# 配置 Git 用户信息（首次使用需要）
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"

# 初始化 Git 仓库
git init

# 添加文件（只添加团队分发相关文件）
git add setup-team-env.sh skills/ docs/ TEAM-SETUP-README.md .gitignore-distribution

# 创建初始提交
git commit -m "Initial release: v1.0.0

- Code Reviewer: 自动化代码审查工具
- Auto Tester: 自动化测试生成工具
- 团队分发配置脚本
- 完整使用文档"

# 创建版本标签
git tag -a v1.0.0 -m "初始版本"

# 添加远程仓库（替换为您的仓库地址）
git remote add origin https://gitlab.com/your-username/openclaw-skills.git

# 推送到远程
git push -u origin main

# 推送标签
git push origin v1.0.0
```

---

## 📋 步骤 5：验证推送

推送成功后，在 Git 平台页面应看到：
- ✅ 文件列表（setup-team-env.sh, skills/, docs/ 等）
- ✅ 提交记录（Initial release: v1.0.0）
- ✅ 标签（v1.0.0）

---

## 🔐 认证方式

### HTTPS + 密码
- 推送时需要输入用户名和密码
- **GitLab:** 使用 Access Token（设置 → Access Tokens）
- **Gitee:** 使用私人令牌（设置 → 安全设置 → 私人令牌）
- **GitHub:** 使用 Personal Access Token（设置 → Developer settings）

### SSH（推荐）
```bash
# 生成 SSH 密钥（如无）
ssh-keygen -t ed25519 -C "your-email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到 Git 平台：
# GitLab: 设置 → SSH Keys
# Gitee: 设置 → SSH 公钥
# GitHub: 设置 → SSH and GPG keys

# 使用 SSH 地址
git remote add origin git@gitlab.com:your-username/openclaw-skills.git
```

---

## 📞 下一步

配置完成后，请告诉我：
1. **仓库地址** - 我帮您执行推送命令
2. **认证方式** - HTTPS 还是 SSH

或者直接执行上述步骤 4 的命令（替换仓库地址）即可！
