---
paths:
  - "backend/tests/e2e/**"
---
# E2E 测试规则

> 本文件规定 `tests/e2e/` 下端到端测试的专属约束。公共规则见 [common.md](common.md)。

## 1. 定位

E2E 测试验证完整 HTTP API 链路：`routes → use_cases → repositories → SQLite`，不 Mock 任何内部层。具体测哪些流程由业务演进决定，不在本文件枚举。

## 2. 客户端策略（强制）

- **必须**使用 `httpx.AsyncClient` + `ASGITransport` 模拟真实 HTTP 调用
- **必须**通过 `conftest.py` 的 `client` fixture 获取客户端
- `client` fixture 已覆盖 `get_db` 依赖，使用内存 SQLite + `StaticPool`，并 seed 默认分类
- **禁止**启动真实 uvicorn 进程（用 ASGI transport 直连 app）
- **禁止**连接真实文件数据库

```python
# ✅ 正确：使用 conftest client fixture
class TestSomeFlow:
    async def test_some_flow(self, client):
        resp = await client.post("/api/v1/...", json={...})
        assert resp.status_code == 201

# ❌ 错误：启动真实服务或用 requests
import requests
requests.post("http://localhost:8000/...")
```

## 3. 隔离原则

- 每个测试函数独立 engine + 独立 client（均为 function 作用域）
- **禁止**跨用例共享用户凭证或业务数据
- 每个用例在 `Arrange` 段自行准备所需数据（注册用户、获取 token 等）
- **禁止**依赖前一用例的副作用

## 4. Mock 策略

| 场景 | 是否 Mock |
|:---|:---|
| 数据库操作 | ❌ **不 Mock**（全链路真实） |
| HTTP 调用 | ❌ 不 Mock（用 ASGITransport 直连 app，不消耗网络） |
| 外部 API（如 LLM） | ✅ Mock（用 `respx`） |
| JWT 签发/校验 | ❌ 不 Mock（验证真实鉴权生效） |

## 5. 鉴权使用

- 注册/登录成功后从响应体取 `access_token`
- 后续请求统一加 `headers = {"Authorization": f"Bearer {token}"}`
- **禁止**在测试内手动构造或伪造 JWT（无法验证真实签发链路）

## 6. 命名与组织

- 类命名：`Test{FlowName}`
- 方法命名：`test_{flow}_{outcome}`
- 一个完整业务流可拆为多个方法，也可用单一串联用例覆盖整条链路

## 7. 断言要求

- 必须断言 HTTP 状态码（具体值，**禁止**只断言 `< 400`）
- 必须断言响应体的关键字段语义，**禁止**只断言 `status_code == 200` 而忽略响应体
- 列表接口必须断言 `total` 与 `items` 长度一致

## 8. 禁止事项

- **禁止**用 Mock 替换 routes / use_cases / repositories（那就成了单元或集成测试）
- **禁止**在 E2E 测试中直接调用 use case 或 repository（必须走 HTTP）
- **禁止**连接真实 `family.db` 或启动真实 uvicorn
- **禁止**用 `requests` / `aiohttp` 等非 `httpx.AsyncClient` 客户端

## 9. 模板

```python
"""{业务流名称} 端到端接口测试。"""


class TestSomeFlow:
    async def test_some_flow_success(self, client):
        # Arrange & Act
        resp = await client.post("/api/v1/...", json={...})
        # Assert
        assert resp.status_code == 201
        assert resp.json()["..."]
```
