---
name: "git_commit_push"
description: "规范化 git 提交信息。触发场景：用户说提交代码/commit/push/提交代码，或完成任何功能/修复/重构后需要保存git仓库"
---

# Git 提交与推送

**本 skill 在涉及 git 提交的场景下被调用**，用于规范化提交信息格式，并在提交成功后询问是否推送到远程仓库。

## 提交前检查

提交前必须先了解当前状态，以下命令**并行执行**：

```bash
git status          # 查看工作区变更（禁止用 -uall）
git diff            # 查看未暂存的改动
git diff --staged   # 查看已暂存的改动
git log -n 5 --oneline  # 查看最近提交风格
```

## 提交信息格式（Conventional Commits）

提交信息**必须**遵循 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### type（必填，小写）

| 类型 | 说明 | 使用场景 |
|:---|:---|:---|
| feat | 新功能 | 新增功能、接口、页面 |
| fix | 修复 | 修复 bug |
| docs | 文档 | 仅文档变更（README、CLAUDE.md 等） |
| style | 格式 | 不影响代码逻辑（空格、分号、格式化） |
| refactor | 重构 | 既非新增功能也非修复 bug |
| perf | 性能 | 提升性能的改动 |
| test | 测试 | 新增/修改测试 |
| chore | 杂务 | 构建工具、依赖、配置等 |
| build | 构建 | 影响构建系统或外部依赖 |
| ci | CI | CI 配置文件变更 |
| revert | 回退 | 回退某次提交 |

### scope（可选，本项目常用值）

- `backend` — 后端相关
- `frontend` — 前端相关
- `api` — 接口相关
- `db` — 数据库相关
- `auth` — 认证相关
- `records` — 记账相关
- `domain` — 领域层相关

### subject（必填）

- 简短描述，**不超过 50 字符**
- 使用祈使句（"新增"而非"新增了"）
- 不用句号结尾

### body（可选）

- 解释"为什么"做这个改动（diff 已说明"做了什么"）
- 每行不超过 72 字符
- 列举关键改动点

### footer（可选）

- `BREAKING CHANGE: <描述>` 标注破坏性变更
- `Closes #123` 关闭 issue

## 提交流程

### 步骤 1：分析变更

根据 `git status` 和 `git diff` 的输出，判断：
- 改动的性质 → 决定 `type`
- 改动的范围 → 决定 `scope`
- 改动的内容 → 撰写 `subject` 和 `body`

### 步骤 2：暂存文件

**按文件名逐个暂存**，禁止使用 `git add -A` 或 `git add .`：

```bash
git add path/to/file1 path/to/file2
```

### 步骤 3：生成提交信息并提交

使用 HEREDOC 传递多行提交信息（避免换行问题）：

```bash
git commit -m "$(cat <<'EOF'
feat(records): 新增按分类筛选记账列表接口

- RecordRepository 增加 filter_by_category 方法
- 补充对应集成测试
EOF
)"
```

### 步骤 4：验证提交

```bash
git status   # 确认提交成功，工作区干净
```

### 步骤 5：询问是否推送（必须执行）

提交成功后，**必须**使用 `AskUserQuestion` 工具询问用户是否推送到远程仓库。

问题设置：
- **question**: "提交成功。是否推送到远程仓库？"
- **header**: "Git Push"
- **options**:
  - "是，推送" — 执行 `git push`（无上游时用 `git push -u origin <branch>`）
  - "否，仅本地提交" — 不推送，结束流程

根据用户选择执行：
- **选择"是，推送"**：
  - 先 `git branch -vv` 检查是否有上游分支
  - 有上游：`git push`
  - 无上游：`git push -u origin <当前分支名>`
  - 推送失败（远程有新提交）：建议 `git pull --rebase` 后重试，**禁止** force push
- **选择"否"**：告知用户提交已完成，不执行推送

## 提交信息示例

### 示例 1：新增功能

```
feat(records): 新增按分类筛选记账列表接口

- GET /api/v1/records 支持 category_id 查询参数
- RecordRepository 增加 filter_by_category 方法
- 补充对应集成测试
```

### 示例 2：修复 bug

```
fix(auth): 修复登录时用户不存在导致 500 错误

密码校验前未检查用户是否存在，抛出未捕获异常。
现在用户不存在时返回 401。
```

### 示例 3：文档变更

```
docs: 新增前后端 CLAUDE.md 项目说明文件
```

### 示例 4：杂务

```
chore(backend): 升级 fastapi 至 0.115.0
```

### 示例 5：含破坏性变更

```
feat(api): 统一接口返回结构为 {code, data, message}

BREAKING CHANGE: 所有接口返回结构变更，前端需同步调整
```

## 禁止事项

- **禁止**使用 `git push --force` 或 `--force-with-lease`，除非用户明确要求
- **禁止**推送到 main/master 分支，除非用户明确要求（需先警告）
- **禁止**使用 `git add -A` 或 `git add .`，必须按文件名暂存
- **禁止**提交敏感文件，详见 [rules.md](rules.md)
- **禁止**在未询问用户的情况下自动 push
- **禁止**使用 `git commit -i` 等交互式命令（不支持交互输入）
- **禁止**使用 `git rebase -i`（交互式）
- **禁止**修改 git config
- **禁止**在 commit message 末尾加句号
- **禁止**提交信息使用过去时（用祈使句："新增"而非"新增了"）
