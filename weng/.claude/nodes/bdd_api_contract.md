流程节点：BDD 契约约定
描述: 以需求理解结果包与验证矩阵结果包为输入，产出 OpenAPI 3.0 契约，经自检达标后写入项目契约文件，供后续测试用例开发节点读取。契约中每个接口都可追溯到需求场景。

# API 契约约定阶段

## 系统指令

你现处于 **API 契约约定阶段**，以自动流程节点身份独立完成契约产出，不涉及任何人工协作、评审或发布环节。

输入：

1. **需求理解结果包**（场景详细描述、Gherkin 文件）
2. **验证矩阵结果包**（分层验证分配，特别是集成测试层的验证内容）
3. **架构基线结果包**（项目现有接口风格、命名约定、错误响应结构、契约文件既有位置）

## 前置条件与适用范围

本节点仅在**验证矩阵集成测试层存在非空场景**（即本功能确有对外接口交互）时执行。

- 若集成测试层全空（纯业务逻辑、无对外接口的功能），本节点应被编排层跳过，不强制产出契约。
- 接口形态以架构基线为准：项目为 HTTP/REST 风格时产出 OpenAPI 契约；若项目采用其他接口形态（如 RPC、消息、内部服务接口），则以项目既有的契约/接口定义方式为准，本节点的 OpenAPI 模板仅作为"接口契约应包含哪些要素"的结构参照，不强制套用 HTTP 语义。

任务：为验证矩阵中集成测试层覆盖的场景，产出与项目现有接口风格一致的接口契约；经自检达标后写入项目契约文件，作为后续测试用例开发节点的输入。

## 核心原则

1. **契约即真理源**：契约文件是接口的唯一定义来源，落盘为项目内的 YAML 文件。
2. **场景驱动设计**：每个接口都能在需求场景和验证矩阵中找到来源，无凭空设计的接口。
3. **自检达标**：契约产出后必须通过全部自检项，任一不达标必须修复后重检。
4. **分歧上报**：接口设计存在多种合理方案且无法自我裁定时，向用户确认，不擅自决定。

## 落盘位置

契约写入项目契约文件，路径约定：

```
docs/api/{功能模块名}.yaml
```

- 首次产出：创建该文件
- 已存在：读取原文件，在其基础上增量更新，并在步骤 5 做兼容性自检

## 步骤 1：接口识别与抽取

从验证矩阵中集成测试列非空的场景，结合场景详细描述，识别所需 API 接口。

### 1.1 识别规则

- **触发动作** → 推断 HTTP Method 和 Path
- **预期结果** → 推断 Response 状态码和结构
- **前置条件中的输入数据** → 推断 Request Body 或 Query Parameters

### 1.2 提取模板

对每个集成测试覆盖的场景填写接口提取表：

```
场景ID：{场景ID}
场景名称：{场景名称}
触发动作：{原场景中的触发动作描述}
预期结果：{原场景中涉及接口交互的预期结果}

提取的接口：
- Method: {GET / POST / PUT / DELETE / PATCH}
- Path: {/api/xxx/xxx}
- 简要描述: {接口用途一句话}
- Request Body 字段（如适用）：
    - {字段名}: {类型} - {描述} - {是否必填}
- Response 状态码: {如 200, 201, 202, 400, 401, 404 等}
- Response Body 结构（如适用）：
    - {字段名}: {类型} - {描述}
```

### 1.3 去重与合并

按 `Method + Path` 组合去重，同一接口被多个场景使用时合并字段要求。

```
接口清单：
1. POST /api/password-reset/request - 请求密码重置
   关联场景：PW-RESET-01, PW-RESET-02, PW-RESET-03
2. GET /api/password-reset/validate - 验证重置链接有效性
   关联场景：PW-CLICK-01, PW-CLICK-02, PW-CLICK-03
3. PUT /api/password-reset/confirm - 执行密码重置
   关联场景：PW-SET-01, PW-SET-02
```

**自我检查：**

- [ ] 所有集成测试标记的场景都被处理
- [ ] 每个接口都有至少一个关联场景
- [ ] Method 和 Path 命名符合 RESTful 惯例
- [ ] 无重复接口定义

## 步骤 2：数据结构定义

定义契约中使用的数据结构（Schemas）。

### 2.1 Schema 识别

- 同一结构出现在多个接口的 Request/Response 中 → 提取为可复用 Schema
- 结构包含多个字段且有明确业务含义 → 命名 Schema

### 2.2 命名规范

```
Schema 命名：{业务实体}{用途}，如 PasswordResetRequest, PasswordResetResponse, TokenValidationResult

字段命名：
- 使用 camelCase
- 布尔字段用 is/has/should 前缀
- 时间字段用 *At 后缀（createdAt, expiresAt）
- 枚举字段附上所有可能值
```

### 2.3 Schema 定义模板

```yaml
components:
  schemas:
    SchemaName:
      type: object
      required:
        - field1
        - field2
      properties:
        field1:
          type: string
          description: "字段描述"
          example: "示例值"
        field2:
          type: integer
          description: "字段描述"
          example: 123
          minimum: 0
        field3:
          type: string
          format: date-time
          description: "时间字段"
          example: "2024-01-01T00:00:00Z"
```

### 2.4 字段约束要求

| 字段类型 | 必须指定的约束 |
|---------|-------------|
| string | 最小/最大长度，或枚举值列表 |
| integer/number | 最小值、最大值（根据业务规则） |
| string(date-time) | format: date-time |
| string(email) | format: email |
| 枚举字段 | enum 列表，包含所有可能值 |
| 可选字段 | 不在 required 列表中，并注明默认值 |

**自我检查：**

- [ ] 所有接口的 Request/Response 结构都已定义对应 Schema
- [ ] 每个 Schema 包含完整的字段描述和示例值
- [ ] 必填字段标记在 required 数组中
- [ ] 字段约束符合业务规则
- [ ] 所有枚举字段列出完整的可能值列表
- [ ] 无重复或冗余 Schema

## 步骤 3：接口详细定义

为每个接口编写完整的 OpenAPI Path 定义。

### 3.1 接口定义模板

```yaml
paths:
  /api/password-reset/request:
    post:
      summary: "请求密码重置"
      description: "用户提交邮箱以请求密码重置链接。无论邮箱是否注册，统一返回202以避免信息泄露。覆盖场景: PW-RESET-01, PW-RESET-02"
      operationId: requestPasswordReset
      tags:
        - Password Reset
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PasswordResetRequest'
      responses:
        '202':
          description: "已接受请求（统一响应，不区分邮箱是否存在）"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PasswordResetResponse'
        '429':
          description: "请求频率超过限制"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ApiError'
      security:
        - {}  # 无需认证
```

### 3.2 定义要素完整性

每个接口定义必须包含：

- [ ] `summary`：简短的一句话描述
- [ ] `description`：详细描述，含业务规则说明（安全考虑、幂等性等）及覆盖场景ID
- [ ] `operationId`：唯一操作ID，格式 `{动词}{资源}`
- [ ] `tags`：接口分组标签
- [ ] 完整的请求定义（如适用）
- [ ] 所有可能的响应状态码（2xx + 4xx + 5xx）
- [ ] 每个响应都有 schema 引用

### 3.3 错误响应规范

必须定义统一错误响应格式，所有 4xx/5xx 响应使用此格式：

```yaml
components:
  schemas:
    ApiError:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          description: "机器可读的错误码"
          example: "RATE_LIMIT_EXCEEDED"
        message:
          type: string
          description: "人类可读的错误描述"
          example: "请求过于频繁，请稍后再试"
        details:
          type: object
          description: "附加错误详情（可选）"
```

**自我检查：**

- [ ] 每个接口都有完整的 summary、description、operationId
- [ ] 每个接口的请求和响应都有 Schema 引用
- [ ] 所有可能的响应状态码都被列出（正常 + 异常）
- [ ] 错误响应使用统一的 ApiError 格式
- [ ] operationId 唯一，符合命名规范
- [ ] tags 合理分组

## 步骤 4：契约-场景追溯

建立契约接口与需求场景的双向追溯。

### 4.1 追溯表

| 接口 (Method + Path) | 覆盖场景ID | 场景验证内容 |
|----------------------|-----------|------------|
| POST /api/password-reset/request | PW-RESET-01, PW-RESET-02, PW-RESET-04 | 202统一响应、异常提示、频率限制 |
| GET /api/password-reset/validate | PW-CLICK-01, PW-CLICK-02, PW-CLICK-03 | 有效token、过期token、无效token |
| PUT /api/password-reset/confirm | PW-SET-01, PW-SET-02, PW-SET-03 | 成功设置、重复密码、弱密码 |

### 4.2 覆盖率检查

```
契约覆盖检查：
- 集成测试覆盖的场景总数：{N}
- 有对应接口定义的场景数：{M}
- 未覆盖场景：{场景ID}：{原因说明}
- 契约覆盖率：{M/N * 100}%
```

**自我检查：**

- [ ] 契约覆盖率 = 100%（所有集成测试场景都有对应接口）
- [ ] 每个接口的 response 覆盖了场景中所有可能的预期结果
- [ ] 追溯表完整，可正向和反向查询

## 步骤 5：契约自检

契约写入文件前，逐项完成以下自检；任一不达标必须修复后重检。

### 5.1 OpenAPI 格式自检

- 文件符合 OpenAPI 3.0 结构：`openapi`、`info`、`paths`、`components` 齐全
- 所有 `$ref` 引用都能在 `components/schemas` 中找到对应定义，无悬空引用
- YAML 缩进正确，无语法错误

### 5.2 场景覆盖自检

验证矩阵中标记"集成测试"覆盖的每个场景ID，都能在契约某个接口的 `description` 的 `覆盖场景:` 列表中找到。

```
覆盖自检报告：
- 集成测试场景总数：{N}
- 已关联到接口：{M}
- 未关联场景：[列表]
```

达标标准：100% 场景关联。

### 5.3 Schema 完备性自检

- 每个 property 都有 `description` 和 `example`
- 每个枚举类型都有 `enum` 列表
- 无未被任何接口引用的 Schema

### 5.4 兼容性自检（增量更新时）

若在已存在契约上更新，与原文件逐项对比，识别变更类型：

- **Breaking**：删除接口/字段、改类型、加必填字段、改路径或状态码语义
- **Non-Breaking**：新增接口、新增可选字段、补充描述或示例

```
变更报告：
- Breaking 变更：[列表，若有]
- Non-Breaking 变更：[列表]
```

存在 Breaking 变更时，在结果包"待确认事项"中显式列出，并向用户确认后再落盘。

**自我检查：**

- [ ] OpenAPI 格式自检通过，无悬空 $ref
- [ ] 场景覆盖率达到 100%
- [ ] 所有 Schema 通过完备性自检
- [ ] 兼容性变更已识别（如适用），Breaking 变更已上报用户

## 步骤 6：写入契约文件

自检全部达标后，将完整 OpenAPI 内容写入落盘位置的契约文件。

- 首次产出：创建 `docs/api/{功能模块名}.yaml`
- 增量更新：在原文件基础上合并，保留未变更的既有接口

写入后确认文件内容与结果包中的 OpenAPI 一致。

**自我检查：**

- [ ] 契约已写入约定路径
- [ ] 文件内容与自检通过的版本一致
- [ ] 增量更新时既有接口未被误删

## 最终输出：API 契约约定结果包

完成所有步骤后，汇总为一份完整输出：

````markdown
# API 契约约定结果包

## 1. 接口清单
| 序号 | Method | Path | 描述 | 关联场景 |
|-----|--------|------|------|---------|
| ... | ... | ... | ... | ... |

## 2. Schema 定义
[所有 Schema 的完整定义]

## 3. OpenAPI 完整文件 (YAML)
落盘路径：docs/api/{功能模块名}.yaml
```yaml
openapi: "3.0.3"
...
```

## 4. 契约-场景追溯表
| 接口 | 覆盖场景ID | 场景验证内容 |
|------|-----------|------------|
| ... | ... | ... |

## 5. 自检报告
| 自检项 | 结果 | 备注 |
|--------|------|------|
| OpenAPI 格式 | ✅ | - |
| 场景覆盖率 | ✅ 100% | - |
| Schema 完备性 | ✅ | - |
| 兼容性 | ✅ | Non-Breaking / 无既有契约 |

## 6. 待确认事项
{汇总 Breaking 变更、无法自我裁定的接口设计分歧，供用户确认}
````

## 质量门禁

| 检查项 | 通过标准 |
|--------|---------|
| 接口完整性 | 所有集成测试标记的场景都有对应接口 |
| Schema 规范 | 所有 Schema 有字段描述、示例值和约束 |
| 错误处理 | 所有 4xx/5xx 使用统一 ApiError 格式 |
| 自检达标 | OpenAPI 格式、场景覆盖率、Schema 完备性、兼容性自检全部通过 |
| 追溯性 | 每个接口可追溯到需求场景 |
| 落盘 | 契约已写入约定路径，内容与自检版本一致 |

**最终判断信号：**

1. 全部自检项达标了吗？
2. 契约已写入约定的项目文件了吗？
3. 存在的 Breaking 变更或设计分歧都已向用户确认了吗？

三个条件都满足，则本阶段完成，可进入下一阶段：测试用例开发（红）。
