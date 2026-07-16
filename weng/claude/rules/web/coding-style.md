# Web编码规范

## 文件组织

按功能或界面区域组织，而非按文件类型：

```text
src/
├── components/
│   ├── hero/
│   │   ├── Hero.tsx
│   │   ├── HeroVisual.tsx
│   │   └── hero.css
│   ├── scrolly-section/
│   │   ├── ScrollySection.tsx
│   │   ├── StickyVisual.tsx
│   │   └── scrolly.css
│   └── ui/
│       ├── Button.tsx
│       ├── SurfaceCard.tsx
│       └── AnimatedText.tsx
├── hooks/
│   ├── useReducedMotion.ts
│   └── useScrollProgress.ts
├── lib/
│   ├── animation.ts
│   └── color.ts
└── styles/
    ├── tokens.css
    ├── typography.css
    └── global.css
```

## CSS自定义属性

将设计令牌定义为变量。不要重复硬编码调色板、排版或间距：

```css
:root {
  --color-surface: oklch(98% 0 0);
  --color-text: oklch(18% 0 0);
  --color-accent: oklch(68% 0.21 250);

  --text-base: clamp(1rem, 0.92rem + 0.4vw, 1.125rem);
  --text-hero: clamp(3rem, 1rem + 7vw, 8rem);

  --space-section: clamp(4rem, 3rem + 5vw, 10rem);

  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
}
```

## 仅动画属性

优先使用对合成器友好的动画：
- `transform`
- `opacity`
- `clip-path`
- `filter`（谨慎使用）

避免动画布局相关属性：
- `width`
- `height`
- `top`
- `left`
- `margin`
- `padding`
- `border`
- `font-size`

## 语义化HTML优先

```html
<header>
  <nav aria-label="主导航">...</nav>
</header>
<main>
  <section aria-labelledby="hero-heading">
    <h1 id="hero-heading">...</h1>
  </section>
</main>
<footer>...</footer>
```

当语义元素存在时，不要使用通用的包装`div`堆叠。

## 命名规范

- 组件：PascalCase（`ScrollySection`、`SurfaceCard`）
- Hooks：`use`前缀（`useReducedMotion`）
- CSS类：kebab-case或工具类
- 动画时间线：camelCase + 意图描述（`heroRevealTl`）