# Web钩子

## 推荐的PostToolUse钩子

优先使用项目本地的工具。不要将钩子绑定到远程一次性包执行。

### 保存时格式化

在编辑后使用项目现有的格式化入口：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "pnpm prettier --write \"$FILE_PATH\"",
        "description": "格式化编辑的前端文件"
      }
    ]
  }
}
```

使用 `yarn prettier` 或 `npm exec prettier --` 的等效本地命令也可以，只要它们使用仓库拥有的依赖。

### Lint检查

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "pnpm eslint --fix \"$FILE_PATH\"",
        "description": "对编辑的前端文件运行ESLint"
      }
    ]
  }
}
```

### 类型检查

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "pnpm tsc --noEmit --pretty false",
        "description": "前端编辑后进行类型检查"
      }
    ]
  }
}
```

### CSS Lint

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "pnpm stylelint --fix \"$FILE_PATH\"",
        "description": "Lint编辑的样式表"
      }
    ]
  }
}
```

## PreToolUse钩子

### 限制文件大小

根据工具输入内容而非可能尚不存在的文件来阻止超大写入：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const c=i.tool_input?.content||'';const lines=c.split('\\n').length;if(lines>800){console.error('[Hook] BLOCKED: File exceeds 800 lines ('+lines+' lines)');console.error('[Hook] Split into smaller modules');process.exit(2)}console.log(d)})\"",
        "description": "阻止超过800行的写入"
      }
    ]
  }
}
```

## Stop钩子

### 最终构建验证

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "pnpm build",
        "description": "在会话结束时验证生产构建"
      }
    ]
  }
}
```

## 执行顺序

推荐顺序：
1. 格式化
2. Lint
3. 类型检查
4. 构建验证