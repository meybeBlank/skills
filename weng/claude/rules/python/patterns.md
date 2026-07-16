---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python 模式

## Protocol（鸭子类型）

```python
from typing import Protocol

class Repository(Protocol):
    def find_by_id(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> dict: ...
```

## Dataclass 作为 DTO

```python
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int | None = None
```

## 上下文管理器和生成器

- 使用上下文管理器（`with` 语句）进行资源管理
- 使用生成器进行惰性求值和内存高效迭代

## 参考

参见 skill: `python-patterns` 获取装饰器、并发和包组织等全面模式。