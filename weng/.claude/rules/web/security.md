> 此文件继承 [common/security.md](../common/security.md)，包含Web特定的安全内容。

# Web安全规则

## 内容安全策略

始终配置生产CSP。

### 基于Nonce的CSP

使用每个请求的nonce而不是`'unsafe-inline'`来加载脚本。

```text
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{RANDOM}' https://cdn.jsdelivr.net;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  img-src 'self' data: https:;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://*.example.com;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
```

根据项目调整来源。不要不加修改地照搬此块。

## XSS防护

- 永远不要注入未经过滤的HTML
- 除非先进行过滤，避免使用`innerHTML`/`dangerouslySetInnerHTML`
- 转义动态模板值
- 绝对必要时，使用经过验证的本地 sanitizer 来过滤用户HTML

## 第三方脚本

- 异步加载
- 从CDN提供时使用SRI
- 每季度审计
- 在实际可行的情况下，优先自托管关键依赖

## HTTPS和响应头

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## 表单

- 对状态变更表单进行CSRF防护
- 对提交端点进行速率限制
- 客户端和服务端双重验证
- 优先使用蜜罐或轻量级反滥用控制，而非粗暴的默认CAPTCHA