---
paths:
  - "backend/tests/unit/**"
---
# 单元测试规则

> 本文件规定 `tests/unit/` 下单元测试的专属约束。公共规则见 [common.md](common.md)。

## 1. 定位

单元测试验证领域层业务规则（实体、值对象、异常）与应用层用例编排，完全在内存中运行，不触碰任何外部依赖。具体测哪些对象由领域/应用层演进决定，不在本文件枚举。

## 2. 隔离原则（强制）

- **完全隔离**：使用 `unittest.mock` / `pytest-mock` / 自实现 `Fake*` 替换所有外部依赖
- **零 IO**：**禁止**访问文件系统、数据库、网络
- **禁止**使用 `conftest.py` 中的 `test_session` / `test_engine` / `client` fixture
- **禁止**导入 `src.infrastructure.*` 下的具体实现（只能导入 ports 抽象接口）
- **每个用例独立构造被测对象与依赖**：`setUp`/`beforeEach` 仅用于不可变配置，每个用例独立创建 Mock/Fake 对象
- **涉及全局状态时须在 `tearDown`/`afterEach` 中恢复**：`monkeypatch`/`mockStatic` 等修改全局状态的操作必须在用例结束后还原
- **外部依赖替换须通过 DI 或接口抽象**：生产代码应提供构造函数注入/工厂接口等可注入点，测试通过公开注入点替换依赖，不可通过反射/私有字段 hack 重置状态

## 3. Mock 策略

### 3.1 异步 Repository / Service

- **优先**自实现 `Fake*` 类（继承自 `src.application.ports.*` 抽象基类），用内存字典模拟
- 简单场景可用 `mocker.AsyncMock()`，但**禁止**用同步 `Mock`/`MagicMock` 模拟 `async` 方法

```python
# ✅ 推荐：Fake Repository（可读、可复用、断言明确）
class FakeUserRepository(UserRepository):
    def __init__(self):
        self._users: dict[str, User] = {}
    async def get_by_username(self, username: str) -> User | None:
        return self._users.get(username)
    async def add(self, user: User) -> User:
        self._users[user.username] = user
        return user
    # ...

# ✅ 也允许：AsyncMock（一次性场景）
mock_repo = mocker.AsyncMock()
mock_repo.get_by_username = mocker.AsyncMock(return_value=None)

# ❌ 错误：同步 Mock 模拟异步方法
mock_repo.get_by_username = Mock(return_value=None)  # await 会失败
```

### 3.2 Fake 复用

- 同一被测 use case 的 Fake 实现应在同目录的测试文件内定义，供该文件内多个用例复用
- 如需跨文件复用，提取到对应测试目录的公共模块（如 `tests/unit/application/fakes.py`）
- **禁止**为追求复用而把 Fake 放到 `src/` 下（Fake 属于测试设施，不属于生产代码）

## 4. 测试结构

- 类组织：每个被测类一个 `Test{ClassName}`，每个被测方法一个 `test_{scenario}_{expected}`
- 每个用例独立构造被测对象与依赖，**禁止** `setUp` 共享可变状态（`setUp` 仅用于不可变配置）
- 异常路径必须覆盖：每个会抛异常的业务规则至少 1 个异常用例

## 5. 覆盖率要求

- 核心业务逻辑覆盖率 **≥ 90%**（领域层 ≥ 95%）
- 每个业务规则至少 1 个正向用例 + 1 个异常用例

## 6. 禁止事项

- **禁止**真实数据库操作（即便是 `:memory:`，那是集成测试的职责）
- **禁止**真实 HTTP 调用
- **禁止**导入 `fastapi` / `sqlalchemy` / `httpx`（除 `pytest` / `unittest.mock` 外不引入第三方）
- **禁止**使用 `@pytest.mark.asyncio` 装饰器（`asyncio_mode = auto` 自动收集）
- **禁止**用 `print` 调试，必须用 `assert` 自验证
- **禁止隐式断言**不允许"方法正常返回即未抛异常"作为唯一验证。必须显式断言副作用（状态变化 / mock 调用 / 返回值）。

## 7. 模板

```python
"""{被测对象} 单元测试（纯内存，无IO）。"""

import pytest

from src.domain.exceptions.business_errors import SomeError
from src.domain.value_objects.money import Money


class TestMoney:
    def test_create_valid_amount(self):
        # Arrange & Act
        money = Money(10.5)
        # Assert
        assert money.amount == 10.5

    def test_negative_amount_rejected(self):
        # Arrange & Act & Assert
        with pytest.raises(SomeError):
            Money(-1)
```
