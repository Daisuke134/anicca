# 工作流模板库

## 1. 客服自动回复（Customer Service Auto-Reply）

**触发器**：关键词匹配
**动作**：自动回复价格/FAQ/联系信息
**适用场景**：电商、咨询服务、SaaS 产品

```json
{
  "name": "customer_service_auto_reply",
  "triggers": [
    {"type": "keyword", "keywords": ["价格", "多少钱", "收费"]}
  ],
  "actions": [
    {"type": "reply", "template": "price_list"}
  ]
}
```

## 2. 数据处理流水线（Data Processing Pipeline）

**触发器**：定时任务（每小时/每天）
**动作**：抓取 → 清洗 → 分析 → 存储
**适用场景**：市场调研、竞品监控、数据仪表盘

```json
{
  "name": "data_pipeline",
  "triggers": [
    {"type": "schedule", "cron": "0 * * * *"}
  ],
  "actions": [
    {"type": "fetch", "source": "api"},
    {"type": "transform", "rules": ["clean", "normalize"]},
    {"type": "analyze", "metrics": ["count", "avg", "trend"]},
    {"type": "store", "target": "database"}
  ]
}
```

## 3. 内容生成系统（Content Generation）

**触发器**：关键词/主题输入
**动作**：生成内容 → 优化 → 发布
**适用场景**：博客、社交媒体、新闻发布

```json
{
  "name": "content_generation",
  "triggers": [
    {"type": "input", "field": "topic"}
  ],
  "actions": [
    {"type": "generate", "model": "deepseek-chat"},
    {"type": "optimize", "rules": ["seo", "readability"]},
    {"type": "publish", "platform": "juejin"}
  ]
}
```

## 4. 智能提醒（Smart Alerts）

**触发器**：条件检测（价格/事件/异常）
**动作**：发送通知（微信/邮件/Telegram）
**适用场景**：价格监控、系统告警、任务提醒

```json
{
  "name": "smart_alerts",
  "triggers": [
    {"type": "condition", "field": "price", "operator": "<", "value": 100}
  ],
  "actions": [
    {"type": "notify", "channel": "wechat", "message": "价格低于 100！"}
  ]
}
```

## 5. 任务编排（Task Orchestration）

**触发器**：手动启动/定时启动
**动作**：多步骤任务按顺序执行
**适用场景**：复杂业务流程、数据处理链

```json
{
  "name": "task_orchestration",
  "triggers": [
    {"type": "manual"}
  ],
  "actions": [
    {"type": "step", "name": "validate_input", "depends_on": []},
    {"type": "step", "name": "process_data", "depends_on": ["validate_input"]},
    {"type": "step", "name": "generate_report", "depends_on": ["process_data"]},
    {"type": "step", "name": "send_notification", "depends_on": ["generate_report"]}
  ]
}
```

## 6. 社交媒体管理（Social Media Management）

**触发器**：定时/关键词监控
**动作**：发布内容/回复评论/分析数据
**适用场景**：品牌运营、社区管理

```json
{
  "name": "social_media",
  "triggers": [
    {"type": "schedule", "cron": "0 9 * * *"}
  ],
  "actions": [
    {"type": "post", "platform": "twitter", "content": "daily_tip"},
    {"type": "monitor", "keywords": ["openclaw", "AI"]},
    {"type": "reply", "template": "engagement"}
  ]
}
```

## 7. 邮件自动化（Email Automation）

**触发器**：新邮件/定时
**动作**：分类/回复/转发/存档
**适用场景**：客户支持、销售线索、订阅管理

```json
{
  "name": "{{profile.lateness.stakeholders.channel}}_automation",
  "triggers": [
    {"type": "{{profile.lateness.stakeholders.channel}}_received", "folder": "inbox"}
  ],
  "actions": [
    {"type": "classify", "categories": ["support", "sales", "spam"]},
    {"type": "auto_reply", "category": "support"},
    {"type": "forward", "category": "sales", "to": "sales@company.com"}
  ]
}
```

## 8. 文档处理（Document Processing）

**触发器**：文件上传/定时扫描
**动作**：解析/提取/转换/存档
**适用场景**：合同管理、发票处理、报告生成

```json
{
  "name": "document_processing",
  "triggers": [
    {"type": "file_uploaded", "extensions": [".pdf", ".docx"]}
  ],
  "actions": [
    {"type": "parse", "engine": "pdf_parser"},
    {"type": "extract", "fields": ["amount", "date", "vendor"]},
    {"type": "store", "target": "database"},
    {"type": "archive", "path": "/documents/processed/"}
  ]
}
```

---

## 定制服务

需要定制工作流？联系我们：
- 微信：[你的微信号]
- Telegram：[你的 Telegram]
- 邮箱：[你的邮箱]

**基础定制**：¥99（单个工作流）
**高级定制**：¥299（多工作流 + 监控）
**企业方案**：¥999（完整解决方案 + 技术支持）
