---
paths:
  - "backend/src/infrastructure/database/**"
---
# 数据库层编码规范

> 本文件规定后端数据库相关代码的约束，包括 ORM 模型、种子数据、仓储实现。

## 主键策略

- 所有表主键必须使用 **UUID 字符串**（`uuid.uuid4()`）
- 禁止使用自增整数主键

```python
id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
```

## 时间字段

- 统一使用数据库服务器时间 `func.now()`
- 不要使用 Python 时间作为默认值

## 外键关联

- `records` 表必须通过 `category_id` 外键关联 `categories` 表
- **禁止**直接存储分类名字符串

## 金额字段

- 使用 `DECIMAL(10,2)` 保证精度
- 非负校验由领域层 `Money` 值对象负责

## 查询排序

- 查询记账列表时按 `created_at` 倒序排列

## 参考

有关仓储模式与领域实体的转换，请参阅：`backend/src/application/ports/`
