---
paths:
  - "**/*.py"
---

# 编码规范

## 异步一致性

- 全链路使用 `async def` + `await`
- **禁止**在异步函数中使用 `time.sleep()`（改用 `asyncio.sleep`）

## 依赖注入

- 所有 Use Case 和 Repository 通过构造函数 `__init__` 注入
- **禁止**内部直接实例化依赖
