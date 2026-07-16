---
paths:
  - "backend/src/interfaces/**"
---
# 接口适配层（Interfaces）编码规范

> 本文件规定后端接口适配层的编码约束。该层只做转发和校验，不含业务逻辑。

## 职责边界

- **不编写业务逻辑**，只做请求转发和参数校验
- 业务逻辑必须委托给 `application` 层的 use case 处理
- Pydantic Schema 仅用于请求/响应校验，不包含业务规则

## 参考

有关接口层与用例层的交互模式，请参阅：`backend/src/application/use_cases/`
