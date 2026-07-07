---
paths:
  - "**/tests/**"
---
# 测试公共规则

> 本文件规定所有层级测试（unit / integration / e2e）必须遵循的公共约束

## 1. 测试金字塔与隔离

- **金字塔占比**：单元 60-70% / 集成 20-30% / E2E 5-10%（最低门槛；SRE 理想态参考：单元 70-85% / 集成 10-25% / E2E 5-10%）
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

## 12. 断言规范（强制）

断言必须验证**业务行为**，不可验证框架/平台/编译器的内置行为。每个断言都应具备独立的回归保护价值。

- **验证行为而非实现细节**：断言须对准被测单元的业务输出（返回值、状态变更、对外部依赖的调用参数），不可断言编译期常量、字段默认值或框架平台返回值
- **断言须与测名一致**：测名中声明的动词（invoked/called/triggered/returns）必须在断言中体现对应验证
- **优先字段级精确断言**：对结构化输出优先使用字段级 `==` 断言，序列化格式的 `contains` 断言仅用于非结构性检查
- **Mock 验证后须补状态断言**：仅 `verify(mock).x()` 不够，必须同时 `assert` 实际状态或返回值发生了变化
- **"不抛异常"不等于通过**：方法正常返回仅证明显式异常未抛出，必须额外验证方法产生了预期副作用或返回值
- **格式化字段须验证格式合法性**：UUID/时间戳/邮箱等字段须用正则或解析器验证格式，不可仅验证非空

## 13. 时间与稳定性（强制）

时间相关测试须保证在任何 CI 环境、任意负载下均可稳定重复通过，不依赖真实时钟或线程调度时序。

- **涉及时间的测试须用虚拟时间**：使用框架提供的可控时钟机制，通过推进虚拟时间来触发超时/定时行为，不可用固定 `sleep` 等待真实时间流逝
- **异步协调须用确定性同步原语**：协程/线程间协调使用 `Future`/`Deferred`/`CountDownLatch` 等门控机制，保证被测代码到达预期状态后再断言
- **阻塞等待上限 100ms**：单测内任何显式阻塞等待不可超过 100 毫秒，超长等待场景改用虚拟时间推进或反射断言内部状态
- **时间/时区/路径/网络依赖须通过注入获取**：生产代码应提供 Clock/Path/HTTP 等边界的注入点，测试中注入可控实现

## 14. 覆盖完整性（强制）

每个被测单元的所有决策路径与输入分类均须有对应用例覆盖，空洞意味着回归保护缺失。

- **每个布尔分支须双边覆盖**：被测函数中的 `if`/`when`/`switch` 等分支条件的 true/false 路径均须各至少一个用例
- **每个可抛异常的外部调用点须覆盖异常传播路径**：被测代码调用的外部依赖可抛异常时，须有至少一个用例验证该异常被正确处理（重新抛出/降级/转换）
- **边界输入须系统化覆盖**：
  - `null` / `None` / 空字符串 / 空集合
  - 数值边界：0、-1、MAX、MIN
  - 非法格式输入：截断数据、类型不匹配、非法编码
  - 特殊字符：Unicode、emoji、SQL/HTML 元字符
- **编排层须有独立用例**：组合多个子系统的编排逻辑/Service 生命周期/public API 链路须在 mock 子系统边界后有独立测试，不可仅依赖各子系统单元测试覆盖
