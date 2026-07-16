---
paths:
  - "backend/src/infrastructure/security/**"
  - "backend/src/interfaces/api/dependencies/auth_deps.py"
---
# 安全层编码规范

> 本文件规定后端安全相关代码的约束，包括密码哈希、JWT 令牌、鉴权依赖。

## 技术选型

- JWT 库使用 **PyJWT**，禁止换回 `python-jose`（已停止维护）
- 密码哈希直接使用 **bcrypt** 包，禁止引入 `passlib`（与 bcrypt 4.x 不兼容）

## JWT 配置

- 密钥必须从 `.env` 的 `SECRET_KEY` 读取，禁止硬编码
- 算法使用 `HS256`（对称加密，PyJWT 纯 Python 实现，无需 cryptography 原生依赖）
- Access Token 有效期 2 小时（从 `settings.ACCESS_TOKEN_EXPIRE_HOURS` 读取）

## 密码哈希

- bcrypt 限制：哈希时按 72 字节截断

```python
import bcrypt

def hash_password(password: str) -> str:
    # 截断到 72 字节（bcrypt 限制）
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")
```

## 参考

有关 JWT 令牌的完整实现，请参阅：`backend/src/infrastructure/security/token_service.py`
