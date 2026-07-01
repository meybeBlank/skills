---
paths:
  - "backend/tests/**"
---
# 测试公共规则

> 本文件规定所有层级测试（unit / integration / e2e）必须遵循的公共约束

## 1. 测试金字塔与隔离

- **金字塔占比**：单元 60-70% / 集成 20-30% / E2E 5-10%
- **测试隔离**：测试间互不依赖，可独立运行，顺序无关
  - 单元测试：每个用例独立创建 Mock/Fake 对象，**禁止**共享可变状态
  - 集成 / E2E：每个用例独立建表/销毁，使用 `:memory:` SQLite + `StaticPool`
- **禁止**：跨用例共享数据库会话、依赖测试执行顺序、依赖前一用例的副作用

## 2. AAA 模式（强制）

每个测试方法严格三段式：

```
Arrange（准备） → Act（执行） → Assert（断言）
```

- `Arrange` 段准备数据、Mock 返回值
- `Act` 段只调用一次被测方法
- `Assert` 段验证结果与副作用，**禁止**夹杂新的 Act 操作
- 三段之间用空行分隔，必要时加 `# Arrange` / `# Act` / `# Assert` 注释

## 3. FIRST 原则

| 字母 | 要求 | 落地 |
|:---|:---|:---|
| Fast | 单元毫秒级 | 使用内存库 / Mock，**禁止**真实文件 IO、网络 |
| Independent | 用例独立 | 每用例独立准备数据，**禁止**共享状态 |
| Repeatable | 可重复 | 使用固定种子数据，避免依赖时间戳随机（必须用时间时显式构造） |
| Self-validating | 自验证 | 用 `assert`，**禁止**靠人工检查或 `print` |
| Timely | 及时编写 | 新增功能代码必须同步生成测试 |

## 4. 命名规范（强制）

| 测试类型 | 类命名 | 方法命名 |
|:---|:---|:---|
| 单元 | `Test{ClassName}` | `test_{scenario}_{expected}` |
| 集成 | `Test{ClassName}` | `test_{method}_{scenario}` |
| E2E | `Test{FlowName}` | `test_{flow}_{outcome}` |

- 文件名一律 `test_*.py`
- 类名一律 `Test*` 且**不继承** `unittest.TestCase`（用 pytest 原生风格）
- 方法名必须能独立表达「场景 + 期望」，禁止 `test_1`、`test_ok` 之类无意义命名

## 5. 异步测试约束

- 异步测试方法用 `async def test_...`
- `pytest-asyncio` 模式为 `auto`（见 `backend/pytest.ini`），**禁止**手动加 `@pytest.mark.asyncio`
- 异步依赖必须用 `AsyncMock` 或自实现 `Fake*` 类，**禁止**用同步 `Mock`/`MagicMock` 模拟 `async` 方法
- **禁止**在异步测试中使用 `time.sleep()`，改用 `asyncio.sleep()`

## 6. 异常断言

- 必须用 `pytest.raises(ExpectedException)` 验证异常抛出
- 必须断言**具体的异常类型**，**禁止**用 `Exception` 兜底

```python
# ✅ 正确
with pytest.raises(InvalidAmountError):
    Money(-1)

# ❌ 错误
with pytest.raises(Exception):
    Money(-1)
```

## 7. 目录镜像与文件归属

- `tests/` 目录必须与 `src/` 镜像：
  - `src/domain/entities/user.py` → `tests/unit/domain/test_user.py`
  - `src/application/use_cases/auth_use_cases.py` → `tests/unit/application/test_auth_use_cases.py`
- 一个源文件对应一个 `test_*.py`，**禁止**单文件塞多个不相关被测类
- 不确定归属时按被测对象类型判断：
  - 纯内存业务规则 / use case Mock → `tests/unit/`
  - Repository 真实 CRUD → `tests/integration/`
  - HTTP API 全链路 → `tests/e2e/`

## 8. 全局 Fixture 使用

测试应优先复用 `tests/conftest.py` 提供的全局 fixture，**禁止**在测试文件内重复定义同名 fixture。具体可用 fixture 及其行为以 `conftest.py` 为权威来源，下表仅作速查：

| Fixture | 适用层级 | 用途 |
|:---|:---|:---|
| `event_loop` | 全部 | session 级事件循环 |
| `test_engine` | 集成 / E2E | 内存 SQLite 引擎 |
| `test_session` | 集成 | 已 seed 分类的 `AsyncSession` |
| `client` | E2E | 已覆盖 `get_db` 的 `httpx.AsyncClient` |

- **禁止**单元测试使用 `test_session` / `client`（违反隔离原则）

## 9. 覆盖率目标

| 层级 | 目标 |
|:---|:---|
| `domain/` | ≥ 95% |
| `application/` | ≥ 90% |
| `infrastructure/` | ≥ 80% |
| `interfaces/` | ≥ 70% |

PR 合并前必须通过全量测试，覆盖率低于目标值标记失败。

## 10. AI 编码强制要求

新增代码必须同步生成对应测试：

| 新增类型 | 必须生成的测试 | 归属目录 |
|:---|:---|:---|
| 领域实体 / 值对象 | 单元测试（业务规则 + 异常路径） | `tests/unit/domain/` |
| Use Case | 单元测试（Fake Repository） | `tests/unit/application/` |
| Repository 实现 | 集成测试（真实数据库） | `tests/integration/` |
| API 路由 | E2E 测试（全链路） | `tests/e2e/` |
| 业务异常 | 单元测试（触发条件） | `tests/unit/domain/` |

## 11. 质量检查清单

每个测试用例提交前自检：

- [ ] 遵循 AAA 三段式
- [ ] 命名清晰表达「场景 + 期望」
- [ ] 异常路径已覆盖（用 `pytest.raises`）
- [ ] 异步依赖用 `AsyncMock` / `Fake*`，未用同步 `Mock`
- [ ] 不依赖其他用例的执行顺序或副作用
- [ ] 不依赖时间戳等随机因素（必须时显式构造）
- [ ] 无 `print`、无人工检查、无 `time.sleep`
