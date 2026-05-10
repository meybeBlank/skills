---
name: session-history-audit
description: 审核 session-history-analyzer 的输出结果，验证与原始 jsonl 数据的一致性、完整性。
---

# Session History Audit

对 `session-history-analyzer` 生成的 HTML 报告进行数据完整性审计，对比原始 jsonl 文件，确保无遗漏、无截断。

## 使用方法

```
/session-history-audit <jsonl文件路径> <html报告路径>
```

或不带参数，自动查找最新生成的报告：

```
/session-history-audit
```

## 审计项目

### 1. USER 条目完整性
- JSONL 中每个 `type=user` 条目的 `message.content` 必须出现在 HTML 中
- 内容允许 HTML 转义，但文字内容不得缺失或截断
- 优先验证用户实际输入（`text` 类型）优先于工具输出（`tool_result`）

### 2. ASSISTANT 条目完整性
- `thinking` 内容必须完整呈现（不允许截断）
- `tool_use` 的工具名和关键参数（如 `file_path`、`command`、`query`）必须呈现
- `text` 回复内容不得缺失

### 3. FILE-HISTORY-SNAPSHOT 完整性
- 被修改的文件列表不得遗漏文件名
- 每个文件的 `version`、`backupTime` 必须呈现

### 4. QUEUE-OPERATION 完整性
- `task-id`、`summary`、`usage` 字段不得缺失

### 5. 工具参数审计
- `WebSearch` 必须显示 `query`
- `WebFetch` 必须显示 `url`
- `Agent` 必须显示 `subagent_type` 和 `prompt` 摘要
- `Bash` 必须显示 `command`
- `Read` 必须显示 `file_path`

## 审计报告格式

```
## 审计报告

### 总体结果
- JSONL 总条目: N | HTML 总条目: N
- JSONL User: N | HTML User: N
- 差异及原因

### 发现的问题
1. [严重度] 类型/位置: 问题描述
   - 期望值: ...
   - 实际值: ...

### 通过的项目
- 检查通过的条目列表

### 建议
- 修复建议
```

## 示例

```
/session-history-audit ~/.claude/projects/-Users-fengzhen-workspace-SK-simulator/1088720a-4abe-4a94-a7cb-7d9cd7426ca8.jsonl ~/.claude/skills/session-history-analyzer/output/session_history_1088720a-4abe-4a94-a7cb-7d9cd7426ca8.html
```
