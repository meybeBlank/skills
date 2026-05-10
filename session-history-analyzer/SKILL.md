---
name: session-history-analyzer
description: 解析 Claude Code 的 jsonl 会话记录，输出可折叠的 HTML 操作历史。
license: MIT
---

# Session History Analyzer

解析 Claude Code 会话记录，生成可折叠的 HTML 操作历史报告。

## 使用方法

```
/session-history-analyzer <jsonl文件路径>
```

## 功能

- 时间线顺序展示操作步骤
- 工具调用、子 agent、思考过程分层缩进
- 颜色编码区分不同操作类型
- 长内容可折叠/展开

## 操作类型

| 前缀 | 颜色 | 内容 |
|------|------|------|
| `[USER]` | 灰色 | 用户输入 |
| `[THINK]` | 蓝色 | 思考过程 |
| `[TEXT]` | 绿色 | 文字回复 |
| `[CALL]` | 橙色 | 工具调用 |
| `[AGENT]` | 紫色 | 启动子 Agent |
| `[ASYNC]` | 紫色边框 | Agent 完成通知 |
| `[FILE]` | 青色 | 文件变更 |

## 审核工具

使用 `/session-history-audit` 对生成的报告进行数据完整性审计，验证输出与原始 jsonl 的一致性。

详细说明见 [SKILL_AUDIT.md](./SKILL_AUDIT.md)

## 输出

解析结果保存到 skill 目录下，文件名格式：
`session_history_<原始文件名>.html`
