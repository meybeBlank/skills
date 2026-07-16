# Web模式

## 组件组合

### 复合组件

当相关UI共享状态和交互语义时，使用复合组件：

```tsx
<Tabs defaultValue="overview">
  <Tabs.List>
    <Tabs.Trigger value="overview">概览</Tabs.Trigger>
    <Tabs.Trigger value="settings">设置</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="overview">...</Tabs.Content>
  <Tabs.Content value="settings">...</Tabs.Content>
</Tabs>
```

- 父组件拥有状态
- 子组件通过context消费
- 相比prop drilling，优先使用这种方式处理复杂小部件

### 渲染属性/插槽

- 当行为共享但标记必须变化时，使用渲染属性或插槽模式
- 将键盘处理、ARIA和焦点逻辑保留在headless层

### 容器/展示分离

- 容器组件负责数据加载和副作用
- 展示组件接收props并渲染UI
- 展示组件应保持纯函数

## 状态管理

分开处理这些关注点：

| 关注点 | 工具 |
|--------|------|
| 服务端状态 | TanStack Query, SWR, tRPC |
| 客户端状态 | Zustand, Jotai, signals |
| URL状态 | search params, route segments |
| 表单状态 | React Hook Form或等效方案 |

- 不要将服务端状态复制到客户端stores
- 派生值而非存储冗余的计算状态

## URL作为状态

在URL中持久化可共享的状态：
- 筛选条件
- 排序顺序
- 分页
- 活动标签
- 搜索查询

## 数据获取

### Stale-While-Revalidate

- 立即返回缓存数据
- 后台重新验证
- 优先使用现有库而非自己实现

### 乐观更新

- 快照当前状态
- 应用乐观更新
- 失败时回滚
- 回滚时发出可见的错误反馈

### 并行加载

- 并行获取独立数据
- 避免父子请求瀑布
- 在合理的情况下预取可能的下一个路由或状态