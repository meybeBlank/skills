---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python 编码风格

## 标准

- 遵循 **PEP 8** 约定
- 所有函数签名使用 **类型注解**

## 不可变性

优先使用不可变数据结构：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    email: str

from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

## 格式化

- 使用 **black** 进行代码格式化
- 使用 **isort** 进行 import 排序
- 使用 **ruff** 进行 linting
