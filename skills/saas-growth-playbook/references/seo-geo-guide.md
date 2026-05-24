# B2B SaaS 的 SEO & GEO 增长指南

> 通过搜索引擎和 AI 搜索获取高质量 B2B 线索

## 为什么 B2B SaaS 需要 SEO/GEO？

B2B 买家的决策路径：
1. **问题意识**: 搜索 "how to [解决问题]"
2. **方案研究**: 搜索 "best [品类] software"
3. **对比评估**: 搜索 "[产品A] vs [产品B]"
4. **购买决策**: 搜索 "[产品] pricing/reviews"

**每个阶段都有搜索行为**，SEO/GEO 让你在整个漏斗中都能被发现。

---

## 🎯 B2B 关键词策略

### 关键词矩阵

| 漏斗阶段 | 关键词类型 | 示例 | 内容类型 |
|----------|-----------|------|----------|
| **TOFU** | 问题型 | how to improve team collaboration | 博客、指南 |
| **TOFU** | 教育型 | what is [概念] | 术语解释 |
| **MOFU** | 品类型 | best [品类] software | 榜单文章 |
| **MOFU** | 对比型 | [产品A] vs [产品B] | 对比页面 |
| **BOFU** | 品牌型 | [产品名] pricing | 定价页 |
| **BOFU** | 评价型 | [产品名] reviews | 评价聚合页 |

### 高意向关键词优先

**优先级排序**
```
1. [产品名] + pricing/demo/trial  ← 最高意向
2. [产品名] vs [竞品]            ← 决策期
3. best [品类] for [场景]        ← 方案研究
4. how to [任务]                  ← 问题意识
```

---

## 📄 核心页面 SEO

### 首页

**Title 公式**
```
[产品名] - [一句话价值主张] | [品类] Software
例: HeyGen - AI Video Generator for Enterprise | Video Creation Platform
```

**Meta Description**
```
[产品名] helps [目标用户] [核心价值]. [关键功能]. Start free trial today.
例: HeyGen helps marketers create professional videos in minutes with AI avatars. No filming required. Start your free trial.
```

**Schema**
```json
{
  "@type": "SoftwareApplication",
  "name": "产品名",
  "applicationCategory": "BusinessApplication",
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": "0",
    "highPrice": "999",
    "priceCurrency": "USD"
  }
}
```

### 产品/功能页

每个核心功能单独页面：
- `/features/[功能名]`
- 独立的 Title + Meta
- 功能专属 Schema

### 定价页

**SEO 优化**
- Title: `[产品名] Pricing - Plans & Features | Start Free`
- 清晰的价格表格
- FAQ Section (用 FAQPage Schema)

**FAQ Schema 示例**
```json
{
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How much does [产品] cost?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "[产品] starts at $X/month for [基础版]. Enterprise plans available."
      }
    },
    {
      "@type": "Question", 
      "name": "Is there a free trial?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, [产品] offers a 14-day free trial with no credit card required."
      }
    }
  ]
}
```

### 对比页 (vs 竞品)

**页面结构**
```
/compare/[竞品名]

H1: [产品] vs [竞品]: Which is Better in 2026?
H2: Quick Comparison
   - 功能对比表格
H2: [产品] Overview
H2: [竞品] Overview  
H2: Feature Comparison
H2: Pricing Comparison
H2: Who Should Use [产品]
H2: Who Should Use [竞品]
H2: Final Verdict
```

**必做竞品页**
- 直接竞品 (同品类)
- 间接竞品 (可替代方案)
- 知名度高的品牌 (蹭流量)

---

## 📚 内容营销 SEO

### Topic Cluster 结构

```
支柱页面: The Complete Guide to [品类]
  ├── 集群: How to [任务1] with [品类]
  ├── 集群: [品类] Best Practices
  ├── 集群: [品类] for [行业]
  └── 集群: [品类] ROI Calculator
```

### 博客文章 SEO

**Title 公式**
```
How to [任务] in 2026: [数字] [形容词] [方法/技巧]
例: How to Create Marketing Videos in 2026: 7 AI-Powered Methods
```

**内容结构**
1. **开头**: 直接回答搜索意图 (AI 引用友好)
2. **目录**: 清晰的 H2/H3 层级
3. **正文**: 每个 H2 包含可操作的信息
4. **总结**: Key takeaways 列表
5. **CTA**: 相关产品功能链接

### 案例研究

**SEO 价值**
- 长尾关键词: "[产品] case study [行业]"
- E-A-T 信号: 证明产品有效
- 反向链接: 客户可能分享

**页面结构**
```
/customers/[公司名]

Title: How [公司] [成果] with [产品] | Case Study
H1: [公司] [成果] with [产品]
H2: The Challenge
H2: The Solution
H2: The Results (数据!)
H2: Key Takeaways
```

---

## 🤖 GEO: B2B 场景

### 为什么 B2B 更需要 GEO

B2B 买家用 AI 做研究：
- "Recommend a video generation tool for enterprise"
- "Compare HeyGen and Synthesia for marketing"
- "What's the best AI avatar tool with API?"

AI 会从你的**内容、评价、文档**中提取答案。

### IndexNow 策略

**高优先级页面**
```bash
# 每次更新立即推送
curl -X POST https://www.bing.com/indexnow \
  -d '{
    "urlList": [
      "/pricing",           # 定价更新
      "/features/new",      # 新功能
      "/customers/latest",  # 新案例
      "/blog/latest"        # 新博客
    ]
  }'
```

### AI 引用优化

**结构化比较表**
AI 喜欢引用表格形式的对比：

```markdown
| Feature | 产品A | 产品B | 产品C |
|---------|-------|-------|-------|
| AI Avatars | ✓ | ✓ | ✗ |
| API Access | ✓ | ✗ | ✓ |
| Price/mo | $30 | $50 | $25 |
```

**直接回答问题**
在页面开头用一句话回答核心问题：

```markdown
## What is [产品]?

[产品] is an enterprise [品类] platform that [核心价值]. 
It's used by [目标用户] to [核心用例].
```

---

## 📈 B2B SEO 指标

### 监测指标

| 指标 | 工具 | 目标 |
|------|------|------|
| 自然搜索流量 | GA4 | 月增 10%+ |
| 关键词排名 | Ahrefs | 核心词进前10 |
| 转化率 | GA4 | 搜索流量 → Demo 请求 |
| 反向链接 | Ahrefs | 月增 10+ 高质量链接 |
| AI 引用 | 手动检查 | 品牌在 AI 回答中出现 |

### 归因追踪

```
UTM 参数标准化:
- utm_source=google
- utm_medium=organic
- utm_campaign=seo-[页面类型]
- utm_content=[关键词]
```

---

## ⚡ B2B SEO 行动清单

### 基础建设

- [ ] 首页 Title/Meta 优化
- [ ] 产品功能页单独优化
- [ ] 定价页 + FAQ Schema
- [ ] SoftwareApplication Schema
- [ ] IndexNow 配置

### 内容建设

- [ ] 创建 vs 竞品对比页 (≥5个)
- [ ] 发布 Topic Cluster 内容
- [ ] 发布客户案例 (≥10个)
- [ ] 创建 Glossary 术语页

### 持续优化

- [ ] 每周发布 1-2 篇博客
- [ ] 每月更新对比页
- [ ] 每季度刷新案例数据
- [ ] 追踪 AI 搜索引用

---

## 🔗 反向链接策略

### B2B 高价值链接来源

| 来源类型 | 获取方式 | 难度 |
|----------|---------|------|
| G2/Capterra | 产品提交 | 低 |
| 行业媒体 | PR/Guest Post | 中 |
| 合作伙伴 | 生态页面 | 中 |
| 客户官网 | 案例引用 | 中 |
| 技术博客 | 评测邀请 | 高 |

### 行动步骤

1. **提交评测平台**: G2, Capterra, TrustRadius
2. **申请集成生态**: Zapier, Make, 框架官网
3. **邀请客户背书**: Logo 授权 + 案例链接
4. **Guest Post**: 行业媒体投稿

---

*基于 SEO & GEO 行动手册 v1.0*
