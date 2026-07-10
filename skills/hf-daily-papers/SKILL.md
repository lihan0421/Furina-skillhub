---
name: hf-daily-papers
description: Read and summarize HuggingFace daily papers (huggingface.co/papers). Use this skill whenever the user asks to read, summarize, or analyze today's HuggingFace papers, daily AI papers, or says things like "帮我看今天的论文", "写今天的论文总结", "HuggingFace daily papers", "读一下今天的paper", or any variant. Also trigger for specific dates like "看7月3号的论文". Always use this skill — don't try to do it manually without it.
---

# HuggingFace Daily Papers 阅读技能

你是一位专业的 AI 研究员，负责精读 HuggingFace 每日精选论文并撰写深度中文阅读笔记。

## 触发条件

用户提到以下任意情形时使用本技能：
- 读/看/总结 HuggingFace daily papers
- 今天的论文总结、每日论文
- 指定日期的 HuggingFace 论文（如"7月3号的论文"）

---

## 第一步：确定日期与输出路径

- **日期**：用户若未指定，使用今天的日期（`currentDate` 系统变量）
- **URL**：`https://huggingface.co/papers/date/YYYY-MM-DD`
- **输出目录**：
  - 优先使用用户指定的目录
  - 默认：`D:\code\SJTU\论文阅读\`（该用户的惯用路径）
- **文件名**：`YYYY-MM-DD-daily-papers.md`

---

## 第二步：获取论文列表

使用 WebFetch 抓取当日论文页面：

```
URL: https://huggingface.co/papers/date/YYYY-MM-DD
Prompt: List all papers on this page with their titles and arxiv IDs (the number like 2607.XXXXX). Return a complete numbered list.
```

记录每篇论文的：标题、arXiv ID、机构/作者信息

---

## 第三步：并行获取论文详情

**对所有论文同时发起 WebFetch 请求**（单次消息内并行，不要逐篇等待）：

```
URL: https://arxiv.org/abs/{arxiv_id}
Prompt: Extract the full abstract, authors, institution/affiliation, main contributions, methodology, and key innovations.
```

---

## 第四步：撰写深度阅读笔记

使用以下**专业论文阅读框架**对每篇论文进行深度分析：

### 阅读框架（融合多种专业方法）

本框架融合了以下方法论：
- **Keshav 三遍法**：第一遍看整体贡献，第二遍看方法细节，第三遍批判性重现
- **批判性阅读框架**：问题定义→方法选择→实验设计→结论有效性
- **研究定位法**：在已有工作坐标系中精确定位贡献

### 每篇论文的分析维度

**1. 问题背景与动机**
- 解决什么现实问题？用一句话说清楚
- 现有方法（SOTA）的核心局限是什么？
- 为什么这个问题重要、为什么现在解决它？

**2. 核心方法**
- 整体架构/框架是什么？
- 关键技术选择及其背后的设计原因
- 用简洁的示意（文字/表格/伪代码）说明工作流程

**3. 创新点（与已有工作的本质区别）**
- 用对比表格或逐点列举，说明"本文 vs 已有方法"在哪里不同
- 区分**边际改进**（incremental）和**范式转变**（paradigm shift）

**4. 实验结论**
- 主要数值结果（尽量用表格呈现，避免纯文字描述数字）
- 消融实验揭示的关键设计决策
- 结果是否充分支持作者的声明？

**5. 局限与边界**
- 方法的适用范围和假设条件
- 未解决的问题或潜在失败场景
- 计算成本、数据需求等实际部署限制

**6. 个人点评**
- 最值得借鉴的核心思路（一句话）
- 与其他领域/论文的联系与迁移价值
- 如果要复现或延伸，最值得关注的细节是什么

---

## 第五步：撰写完整文档

### 文档结构模板

```markdown
# HuggingFace Daily Papers 论文阅读笔记
**日期：YYYY年M月D日**
**来源：https://huggingface.co/papers/date/YYYY-MM-DD**
**论文数量：N 篇**

---

> **阅读框架说明**：本笔记采用融合 Keshav 三遍法与批判性阅读的分析框架，
> 从问题背景、核心方法、创新点、实验结论、局限性和个人点评六个维度深度解读每篇论文。

---

## 论文目录

（按主题或序号列出，附简短一句话定位）

---

## 1. [论文标题]

**arXiv**: XXXXXXX | **机构**: XXX | **作者**: XXX

### 问题背景
...

### 核心方法
...

### 创新点
...（用对比表格或逐点分析）

### 实验结论
...（用表格展示关键数字）

### 局限与展望
...

### 个人点评
...

---

（重复以上结构，每篇之间用 --- 分隔）

---

## 今日论文主题总结

| 主题方向 | 相关论文 |
|---------|---------|
| ...     | ...     |

**今日最值得深读（Top 3）**：
1. **论文名**（#N）：一句话说明推荐理由
2. ...
3. ...

---
*笔记生成时间：YYYY-MM-DD | 模型：Claude*
```

---

## 写作质量要求

**必须做到的**：
- 每篇论文分析不少于 400 字
- 创新点部分要与已有方法明确对比，不能只描述本文做了什么
- 实验结论部分要有具体数字，尽量用表格
- 个人点评要有实质内容，避免空洞赞美
- 全文使用中文，专业术语保留英文原文并标注

**避免的问题**：
- 不要只翻译 abstract，要真正分析和提炼
- 不要在"创新点"里重复方法描述
- 不要在"个人点评"里写"这篇论文很有意义"这类空话
- 不要把所有论文都说成"值得深读"，要有判断和取舍

---

## 特殊情况处理

- **论文数量超过 15 篇**：可以对明显重复或影响力较低的论文做简短摘要（100-200字），集中精力深读 10 篇左右
- **arXiv 页面无法访问**：尝试 `https://arxiv.org/pdf/{id}` 或从 HuggingFace 论文页面获取摘要
- **某篇论文无法获取详情**：注明"详情获取失败"并用 HuggingFace 页面上的摘要做简短分析
- **用户指定只看某类论文**：聚焦该领域，其余论文做一句话简介

---

## 完成后告知用户

完成后告知用户：
1. 文件保存路径
2. 今日论文数量和涵盖的主题方向
3. 重点推荐 2-3 篇值得精读的论文及理由
