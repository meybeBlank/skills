---
paths:
  - "backend/tests/integration/**"
---
# 集成测试规则

> 本文件规定 `tests/integration/` 下集成测试的专属约束。公共规则见 [common.md](common.md)。

## 1. 定位

集成测试验证 Repository 实现与真实数据库的交互（CRUD、事务、关联查询、排序等）。具体测哪些 Repository 由基础设施演进决定，不在本文件枚举。

## 2. 数据库策略（强制）

- **必须**使用内存 SQLite：`sqlite+aiosqlite:///:memory:`
- **必须**配合 `StaticPool` 保证同一连接共享（否则 `:memory:` 每连接一个新库）
- **必须**通过 `conftest.py` 的 `test_engine` / `test_session` fixture 获取会话
- **禁止**连接真实文件数据库（`./family.db` 等）
- **禁止**在测试内手动 `create_async_engine`

```python
# ✅ 正确：使用 conftest fixture
class TestSomeRepository:
    async def test_add_and_get(self, test_session):
        repo = SomeRepository(test_session)
        # ...

# ❌ 错误：自建引擎/会话
engine = create_async_engine("sqlite+aiosqlite:///./test.db")
```

## 3. 隔离原则

- 每个测试函数独立 engine（`test_engine` 为 function 作用域）
- 测试后引擎自动 `dispose()`，表结构随之销毁
- **禁止**跨用例共享数据（即便同 `Test*` 类内）
- **禁止**依赖测试执行顺序

## 4. 种子数据

- `test_session` fixture 已自动调用 `seed_categories(session)`，预置默认分类
- 需要分类时直接 `cat_repo.list_all()` 取用，**禁止**手动构造不存在的分类 ID
- 需要其他业务数据时在 `Arrange` 段显式构造并持久化，**禁止**依赖前一用例的残留

## 5. Mock 策略

| 场景 | 是否 Mock |
|:---|:---|
| 数据库操作 | ❌ **不 Mock**（验证 Repository 与数据库真实交互） |
| 外部 API | ✅ Mock（用 `respx`，避免消耗真实额度） |
| JWT 签发 | ❌ 不 Mock（如涉及真实 token 校验） |

## 6. 覆盖要求

- 每个 Repository 公共方法至少 1 个用例
- 必须覆盖正向路径与异常/边界路径（空结果、不存在、过滤、排序等）
- 涉及关联查询的方法必须验证关联正确性
- 涉及用户/租户隔离的方法必须验证隔离生效
- **数据库约束须覆盖违规行为**：每条 UNIQUE/Foreign Key/CHECK 等约束须有至少一个用例验证违反约束时的异常行为
- **边界数据须系统化覆盖**：空结果集、极限偏移量、重复插入冲突、最大长度字符串、零值与负值等边界场景须有对应用例

## 7. 命名与组织

- 类命名：`Test{RepositoryClassName}`
- 方法命名：`test_{method}_{scenario}`
- 一个 Repository 实现对应一个 `test_*.py` 文件

## 8. 禁止事项

- **禁止**用 Mock 替代真实数据库操作（那就成了单元测试，应放 `tests/unit/`）
- **禁止**断言 SQL 字符串本身（脆弱，应断言查询结果的语义）
- **禁止**在集成测试中调用 HTTP 接口（那是 E2E 的职责，应放 `tests/e2e/`）
- **禁止**修改 `src/` 下的源码以适配测试


## 9. 断言规范（强制）

集成测试的每个断言须验证数据库交互的**语义正确性**，不可依赖 SQL 文本或脆弱字符串匹配。

- **查询结果须从语义层面断言**：验证返回内容的业务含义（字段值、排序顺序、关联实体、分页偏移量），不可断言 SQL 字符串本身
- **格式化字段须验证格式合法性**：UUID/时间戳/哈希值等字段须验证其格式符合预期（正则匹配、解析不抛异常），不可仅验证非空
- **集合结果须验证结构完整性**：列表结果须同时验证长度与每个元素的字段内容；分页场景须验证 `total` 与 `items` 一致性
- **恒真断言须排除**：直接返回常量值的方法调用不可作为唯一断言（如 `assert repo.method() is not None` 而 `method` 永远返回非空），须改为语义级验证

## 10. 模板

```python
"""{Repository名} 集成测试（真实内存SQLite，含种子分类）。"""

from src.infrastructure.database.repositories.some_repository import SomeRepository


class TestSomeRepository:
    async def test_add_and_get(self, test_session):
        # Arrange
        repo = SomeRepository(test_session)
        # Act
        await repo.add(some_entity)
        # Assert
        found = await repo.get_by_id(some_entity.id)
        assert found is not None
```
