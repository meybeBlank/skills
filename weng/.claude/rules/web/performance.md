# Web性能规则

## 核心Web Vitals指标目标

| 指标 | 目标 |
|------|------|
| LCP | < 2.5秒 |
| INP | < 200毫秒 |
| CLS | < 0.1 |
| FCP | < 1.5秒 |
| TBT | < 200毫秒 |

## 包体积预算

| 页面类型 | JS预算(gzip) | CSS预算 |
|----------|--------------|---------|
| 着陆页 | < 150kb | < 30kb |
| 应用页 | < 300kb | < 50kb |
| 微站 | < 80kb | < 15kb |

## 加载策略

1. 在合理的情况下内联关键首屏CSS
2. 仅预加载英雄图和主要字体
3. 延迟加载非关键CSS或JS
4. 动态导入重型库

```js
const gsapModule = await import('gsap');
const { ScrollTrigger } = await import('gsap/ScrollTrigger');
```

## 图片优化

- 显式指定`width`和`height`
- 仅对英雄媒体使用`loading="eager"`加上`fetchpriority="high"`
- 对首屏以下资产使用`loading="lazy"`
- 优先使用AVIF或WebP，并提供回退方案
- 永远不要交付远超渲染尺寸的源图

## 字体加载

- 除非有明确例外，最多两个字体家族
- `font-display: swap`
- 在可能的情况下进行子集化
- 仅预加载真正关键的重/样式

## 动画性能

- 仅动画对合成器友好的属性
- 狭隘地使用`will-change`，用完后移除
- 简单的过渡优先使用CSS
- JS动画使用`requestAnimationFrame`或成熟的动画库
- 避免滚动处理器频繁触发；使用IntersectionObserver或行为良好的库

## 性能检查清单

- [ ] 所有图片都有显式尺寸
- [ ] 无意外渲染阻塞资源
- [ ] 动态内容无布局偏移
- [ ] 动画保持在对合成器友好的属性上
- [ ] 第三方脚本仅在需要时以async/defer方式加载