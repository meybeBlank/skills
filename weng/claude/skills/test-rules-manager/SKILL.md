---
name: "test-rules-manager"
description: "管理后端测试规则体系：编辑 CLAUDE.md 测试章节、创建/更新 .claude/rules/test/ 规则文件、校验测试用例层级归属。当用户要求搭建/审查/重构测试规则，或在 unit/integration/e2e 间迁移测试时调用。"
---

# 测试规则文件管理

本 skill 沉淀了「家庭记账」项目测试规则体系搭建与维护的完整方法论。处理任何测试规则相关任务时，按本文件执行。

## 1. 触发场景

- 初始化/搭建后端测试 rules 体系
- 审查现有测试 rules 是否合规
- 修改 `backend/CLAUDE.md` 的测试章节
- 测试用例在 unit/integration/e2e 之间迁移或归属校验
- 新增测试层级或调整 rules 文件结构

## 2. 文件职责分层

测试规则分散在多处，各司其职，**禁止重复**：

| 文件 | 职责 | 内容边界 |
|:---|:---|:---|
| `backend/CLAUDE.md`「测试架构」章节 | 项目级总览 | 分层目录、执行命令、Fixture 契约速查、规则导航 |
| `.claude/rules/backend/tests.md` | 测试目录概览入口 | 指向各分层 rules，不写具体约束 |
| `.claude/rules/test/common.md` | 所有层级公共约束 | AAA、FIRST、命名、异步、异常断言、目录镜像、覆盖率目标、AI 强制要求、质量清单 |
| `.claude/rules/test/unit.md` | 单元测试专属 | 隔离原则、Mock/Fake 策略、禁止事项 |
| `.claude/rules/test/integration.md` | 集成测试专属 | 数据库策略、种子数据、覆盖要求、禁止事项 |
| `.claude/rules/test/e2e.md` | E2E 测试专属 | 客户端策略、鉴权使用、断言要求、禁止事项 |

### 去重原则

- CLAUDE.md **不重复** rules 中的细节（AAA/FIRST、Mock 策略、命名、覆盖率、AI 要求）
- common.md **不重复** 各分层专属内容
- 各分层 rules **不重复** common.md 内容（仅写"公共规则见 common.md"）

## 3. rules 编写核心原则（关键）

### 3.1 只写结构性/方法论约束

rules 是**长期稳定**的工程规范，不是项目现状快照。

### 3.2 禁止枚举"会随项目变动"的清单

以下内容**禁止**写进 rules，因为新增/重构时会被迫频繁改 rules：

| 禁止内容 | 原因 | 替代写法 |
|:---|:---|:---|
| 测试对象清单（如"测 User/Record/Category"） | 新增实体会让清单过时 | 写"定位"段说明层级职责边界 |
| 必测场景清单（如"P0 主流程、401、404"） | 业务演进会让场景过时 | 写"覆盖要求"段（每方法≥1用例、覆盖异常/边界） |
| 现有 Fake/fixture 实现位置（指向具体文件类名） | 重构会让位置失效 | 写 Fake 复用原则（同目录复用、跨文件提取 fakes.py） |
| 具体业务绑定（如"P0 必须有单一串联用例"） | 业务阶段变化 | 写通用组织原则 |

### 3.3 模板/示例用通用占位符

- ✅ `TestSomeFlow` / `test_some_flow_success` / `{业务流名称}`
- ❌ `TestP0Flow` / `test_register_login_create_list` / `TestSqlAlchemyUserRepository`

### 3.4 配置/fixture 类速查表注明权威来源

代码会演进，rules 中的速查表可能与代码不同步。必须注明：

> 具体行为以 `conftest.py` 为权威来源，下表仅作速查

## 4. CLAUDE.md 测试章节内容边界

### 保留（项目级全局）

- 分层与目录总览（项目组织）
- 全局 Fixture 速查（项目级 conftest 契约，注明以 conftest.py 为准）
- 执行命令（编译/运行，项目级）
- 测试规则文件导航（指向 rules）
- 顶部一句说明"具体规范见 rules，本节只放项目级总览"

### 删除（已在 rules 中规定）

- 核心原则（AAA/FIRST）→ common.md
- Mock 策略表 → 各分层 rules
- 命名规范表 → common.md
- 覆盖率目标表 → common.md
- AI 编码强制要求表 → common.md
- fixture 实现细节（如 event_loop 作用域等）

## 5. 测试目录划分标准

| 层级 | 目录 | 判定依据 |
|:---|:---|:---|
| 单元 | `tests/unit/` | 纯内存，Mock/Fake 所有外部依赖，零 IO |
| 集成 | `tests/integration/` | 真实 SQLite 内存库的 Repository CRUD |
| E2E | `tests/e2e/` | HTTP API 全链路（httpx + ASGITransport） |

### 常见错位

- HTTP 全链路测试（用 `client` fixture + `client.post`）放在 `integration/` → 应迁到 `e2e/`
- Repository 真实 CRUD 放在 `unit/` → 应迁到 `integration/`
- use case 用 Fake Repository 测试放在 `integration/` → 应迁到 `unit/application/`

### 目录镜像规则

`tests/` 与 `src/` 镜像：

- `src/domain/entities/user.py` → `tests/unit/domain/test_user.py`
- `src/application/use_cases/auth_use_cases.py` → `tests/unit/application/test_auth_use_cases.py`

## 6. 标准处理流程

### 步骤 1：读现状

- 读 `backend/CLAUDE.md` 测试章节
- 读 `.claude/rules/test/` 下所有 rules 文件
- 读 `.claude/rules/backend/tests.md`
- 读 `backend/tests/conftest.py`、`backend/pytest.ini`
- LS `backend/tests/` 查看实际用例分布

### 步骤 2：校验归属

对每个 `test_*.py`，按第 5 节标准判断归属目录是否正确。错位的列出迁移清单。

### 步骤 3：编辑文件

按第 2、3、4 节的职责分层和编写原则编辑：

- CLAUDE.md：删重复、留总览
- rules：删清单式内容、保留结构性约束
- 错位用例：迁移到正确目录，补充 `__init__.py`

### 步骤 4：运行 pytest 验证

```bash
cd /Users/fengzhen/workspace/HunDun/backend
VIRTUAL_ENV="$PWD/.venv" .venv/bin/python -m pytest -v
```

迁移/修改后必须全量通过，否则回滚排查。

## 7. rules 文件 frontmatter

每个 rules 文件必须有 `paths` frontmatter，自动作用于对应目录：

```yaml
---
paths:
  - "backend/tests/unit/**"   # 按层级填
---
```

- `common.md`：`backend/tests/**`
- `unit.md`：`backend/tests/unit/**`
- `integration.md`：`backend/tests/integration/**`
- `e2e.md`：`backend/tests/e2e/**`

## 8. 质量检查清单

完成任务前自检：

**rules 文件**

- [ ] 无"测试对象"清单（具体类名枚举）
- [ ] 无"必测场景"清单（具体业务流程枚举）
- [ ] 无"现有实现位置"清单（指向具体文件类名）
- [ ] 模板/示例用通用占位符，未绑定具体业务
- [ ] fixture/配置速查表注明"以代码为权威来源"
- [ ] frontmatter `paths` 正确

**CLAUDE.md 测试章节**

- [ ] 无与 rules 重复的细节（AAA/FIRST/Mock策略/命名/覆盖率/AI要求）
- [ ] 保留分层目录、执行命令、Fixture 契约、规则导航
- [ ] 顶部有"具体规范见 rules"的说明

**测试目录**

- [ ] 每个用例归属正确（unit/integration/e2e）
- [ ] 迁移后 `__init__.py` 齐全
- [ ] pytest 全量通过
