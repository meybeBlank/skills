# Web / 微服务项目范式 Profile

定义 **Web / 微服务类项目**在 BDD 流程中受项目结构影响的四处形态。流程骨架由节点文件承载，与项目类型无关；本文件只定形态。

由`架构勘察`选定并写入架构基线，下游节点按需读取对应章节。本文件给"选项集合与默认"，具体框架版本/目录/命令/标注符号由架构勘察从真实代码探测；形态冲突以本文件为准。

## 适用判定

命中任一即选本 profile：Web/服务框架依赖（Spring Boot/Express/Django/Gin 等）或对外 HTTP/RPC 端点；存在或应产出 OpenAPI/Protobuf 契约；测试栈以 HTTP 集成 + BDD/E2E 框架为主。

## 一、契约产出形态

Web 跨边界接口以**网络接口**为主，契约用标准 IDL。

| 交互形态 | 契约形式 | 落盘 |
|:---|:---|:---|
| HTTP/REST | OpenAPI 3.0 yaml | `<doc>_契约.yaml` |
| RPC/消息 | Protobuf/IDL 或既有契约文件 | 既有契约位置 |

**OpenAPI 内容**：每接口含 `summary`、`description`（业务规则 + 覆盖场景 ID）、`operationId`（`{动词}{资源}`）、`tags`、完整请求定义、所有响应码（2xx+4xx+5xx）各带 Schema 引用。Schema 命名 `{实体}{用途}`，字段 camelCase、布尔用 is/has 前缀、时间用 `*At`、枚举列全量、string 限长度/枚举、数值限 min/max、可选字段不入 required。所有 4xx/5xx 用统一 `ApiError`（`code`/`message`/可选 `details`）。集成测试断言状态码与响应体 Schema。

**自检**：OpenAPI 结构齐全（`openapi`/`info`/`paths`/`components`）、`$ref` 无悬空、YAML 无错；每 property 有 `description`+`example`、枚举有 `enum`、无未引用 Schema；每接口可追溯至少一个场景；增量更新既有接口未误删，Breaking 变更（删接口/字段、改类型、加必填、改路径/状态码语义）列入待确认。

**契约跳过**：集成层非空但仅消费既有接口（未改签名/语义）时跳过契约与契约审查，集成测试直接针对既有接口编写。

## 二、测试分层形态

| 层 | 选项 | 默认 | 隔离 |
|:---|:---|:---|:---|
| 功能层（E2E/BDD） | Cucumber/Behave/SpecFlow 步骤定义 + Gherkin / Playwright/Cypress | Gherkin + 步骤定义 | 测试专用存储或 Mock 准备前置数据，不依赖生产库 |
| 集成层 | 基于契约构造 HTTP/RPC 请求断言响应 | HTTP 集成测试 | Mock 隔离未完成依赖方 |
| 单元层 | 单元框架 + Mock + 断言库 | 单元测试 | Mock 隔离一切外部依赖 |

**功能层承载**：有 BDD/E2E 框架 → 产出可执行步骤定义，每 Gherkin 步骤对应一个（Given 备数据、When 触发、Then 断言副作用），服务未实现时失败 → 红灯。无框架 → Gherkin 降级为需求载体，端到端验证下沉集成层，功能层标注"无 E2E 框架，下沉集成/单元层"。

### 全栈项目前端测试分层

当项目含前端时，须额外覆盖：

| 层 | 选项 | 默认 |
|:---|:---|:---|
| 功能层（E2E） | Playwright/Cypress | Playwright |
| 单元层 | Vitest + @vue/test-utils / Jest + Testing Library | Vitest |

**强制双覆盖**：验证矩阵"前端测试"列非空的场景，前端对应测试层必须有对应用例，任一列空白即为阻断。前后端测试须分别运行、分别统计覆盖率。

## 三、审查探测方式

**场景 ID 标注**：以架构勘察探测的既有惯例为准，常见 `@Tag`（JUnit5）、注解、命名约定。

```bash
grep -rn "@Tag" src/test/ | grep -oE '"[A-Z]+-[A-Z]+-[0-9]+"' | sort -u
```

**契约核对**：核对 `<doc>_契约.yaml`——OpenAPI 结构齐全、`$ref` 无悬空、每接口可追溯场景、4xx/5xx 用统一 ApiError。

**绿灯真实性**：以架构勘察提取的实际命令验证（如 `mvn test`/`npm test`/`pytest`）。

## 四、覆盖率工具落地

工具以架构勘察探测为准，常见 Jacoco/nyc/coverage.py/go test -cover。

**改动覆盖率提取**：从覆盖率报告按 git diff 改动文件清单与 `+` 行过滤，优先用按路径过滤或 diff 覆盖插件（如 `diff-cover`）精确到 diff 行。门禁：改动文件/模块行覆盖率 ≥ 80%、改动代码无未测分支；全量行覆盖率仅作回归参考。无工具时标注"覆盖率无法量化"交用户决策。

## 兜底

探测到的子形态不在本 profile 选项集内时，标注"无先例"，给建议形态经用户确认后采用并记入架构基线。
