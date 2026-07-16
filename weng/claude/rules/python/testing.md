---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python 测试

## 框架

使用 **pytest** 作为测试框架。

## 覆盖率

```bash
pytest --cov=src --cov-report=term-missing
```

## 测试组织

使用 `pytest.mark` 进行测试分类：

```python
import pytest

@pytest.mark.unit
def test_calculate_total():
    ...

@pytest.mark.integration
def test_database_connection():
    ...
```

## 参考

参见 skill: `python-testing` 获取详细的 pytest 模式和 fixtures。