---
paths:
  - "backend/src/infrastructure/config/**"
  - "backend/.env*"
---
# 配置管理编码规范

> 本文件规定后端配置管理的约束。所有敏感配置必须外部化。

## 配置外部化

- `SECRET_KEY` 和数据库路径必须从 `settings.py` 读取
- `settings.py` 从 `.env` 加载（使用 `pydantic-settings`）
- **禁止**硬编码任何敏感配置（密钥、连接串等）

## 环境变量管理

- 提交 `.env.example` 作为模板
- **禁止**提交真实 `.env` 文件

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    SECRET_KEY: str
    DATABASE_URL: str
```
