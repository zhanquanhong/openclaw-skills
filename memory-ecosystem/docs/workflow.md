# 记忆生态系统 - 执行工作流

## 📋 完整流程

### 第一阶段：风格定义 (30 分钟)

```bash
# 1. 使用 Prompt 01 生成 4 张变体
/imagine prompt: [01-concept.md 内容] --ar 16:9 --v 6.0 --q 2

# 2. 选择最佳结果
# 标准：最像"发光水母 + 电路板"

# 3. 保存风格
# 点击 U1/U2/U3/U4 → 点击 "Set as Style"
# 记录风格链接（用于后续 --sref 参数）
```

**输出**: 风格参考链接 `--sref [URL]`

---

### 第二阶段：素材生成 (1 小时)

```bash
# 1. 生成卡片图 x2
/imagine prompt: [02-detail.md 内容] --ar 4:5 --v 6.0 --sref [风格链接] --q 2

# 2. 生成信息图
/imagine prompt: [03-infographic.md 内容] --ar 16:9 --v 6.0 --sref [风格链接] --q 2

# 3. 选择最佳结果，下载高清版本
```

**输出**: 卡片图 x2, 信息图 x1

---

### 第三阶段：主视觉生成 (30 分钟)

```bash
# 1. 生成主视觉
/imagine prompt: [04-workstation.md 内容] --ar 16:9 --v 6.0 --sref [风格链接] --q 2 --style raw

# 2. 选择最佳结果，下载高清版本
```

**输出**: 主视觉大图 x1

---

### 第四阶段：后期处理 (1 小时)

**工具**: Figma / Canva

1. **导入所有图片**
2. **添加文字**
   - 卡片图：`The Reach: Memories that seek you.` → 翻译成中文
   - 信息图：左右标签翻译成中文
   - 主视觉：`MNEMONIC GROWTH SYSTEM // VER 2.0`
3. **调整色彩**（如需要）
4. **导出最终版本**

---

## ✅ 质量检查清单

- [ ] 所有图片风格一致（使用同一 `--sref`）
- [ ] 色彩符合规范（背景 `#121212`，霓虹橙/电青渐变）
- [ ] 文字区域留白充足
- [ ] 主视觉突出"主动牵引"隐喻
- [ ] 分辨率满足使用场景（8k 原始，导出按需）

---

## 📁 文件组织

```
assets/
├── 01-concept-variations/    # 4 张变体
├── 02-detail-cards/          # 2 张卡片图
├── 03-infographic/           # 1 张信息图
├── 04-workstation-master/    # 主视觉
└── final-export/             # Figma 后期导出
```

---

## 🛠️ 常见问题

**Q: 风格不一致怎么办？**  
A: 确保所有后续生成使用同一 `--sref [风格链接]`

**Q: 文字区域不够？**  
A: 重新生成时在 prompt 强调 `Leave more negative space for text`

**Q: 色彩太暗/太亮？**  
A: 调整 `--q` 参数或后期 Figma 调整

---

**文档版本**: v1.0  
**更新日期**: 2026-04-12
