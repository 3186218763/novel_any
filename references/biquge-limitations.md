# 笔趣阁镜像站抓取局限

> 记录于 2026-05-26，基于对 15+ 个笔趣阁镜像站的实测。

## 核心发现

**所有笔趣阁盗版站统一返回 ~1000 字符的预览片段，而非完整章节。**

## 测试站点列表

| 站点 | 内容长度 | 反爬措施 | 状态 |
|------|---------|---------|------|
| bqglll.cc (m) | Cloudflare JS | 仅首页可访问 | ❌ |
| bqglll.cc (www) | 985-1079 字 | `?get=content` trick | ⚠️ 预览 |
| bqglll.cc (www, 无参数) | 6 字 | Cloudflare JS | ❌ |
| biquhe.com | 539-1183 字 | cloudscraper 可过 | ⚠️ 预览 |
| biquge.com.cn | — | SSL 证书问题 | ❌ |
| biquge.info | — | Cloudflare EOF | ❌ |
| biquge.tv | — | 无书链接 | ❌ |
| biqukan.com | — | 403 | ❌ |
| bqg5200.com | — | Cloudflare EOF | ❌ |
| xbiquge.la | — | Cloudflare EOF | ❌ |
| xbiquge.com | 5486 字 | SSL + 代理问题 | ⚠️ 不可达 |
| 23qb.com | 3534 字 | 章节 403 | ⚠️ 不可达 |
| biqugeu.net | 3617 字 | JS 渲染书单 | ⚠️ 无法遍历 |
| trxs.cc | 2300-4400 字 | Playwright 可抓 | ✅ 唯一可用 |

## 可行方案

1. **bqglll.cc `?get=content`**：最稳定，但只有 1000 字预览。适合快速测试。
2. **trxs.cc + Playwright**：完整章节（2300-4400 字），但是同人小说，豆瓣无条目，评论难以匹配。
3. **paywalled 源**：起点/Qidian 等正版站需要付费/登录，不在考虑范围。

## 技术细节

### bqglll.cc `?get=content` trick
- 仅 www 版有效，mobile 版为 Cloudflare JS
- 请求格式: `https://www.bqglll.cc/look/{book_id}/{chapter}.html?get=content`
- 内容在 `id="chaptercontent"` 容器中
- 章节列表在 `<div class="listmain"> > <dl> > <dd>` 中（www 版）
- 正则: `<dd>\s*<a\s+href\s*=\s*"((?:/look/\d+/)?(\d+)\.html)"\s*>\s*([^<]+?)\s*</a>\s*</dd>`

### trxs.cc Playwright 抓取
- 需要 Chromium headless shell
- WSL 环境需手动安装 libnspr4/libnss3（见 `references/playwright-wsl-setup.md`）
- 小说列表页 JS 渲染，需 `wait_until='networkidle'` + `time.sleep(2)`
- 章节 URL 格式: `/tongren/{book_id}/{chapter}.html`
- 编码为 GB18030（非 UTF-8）
- 书名包含评分/作者信息，需清洗

### Cloudflare 绕过
- `cloudscraper.create_scraper()` 对 bqglll.cc 书页有效（455KB 响应）
- 对章节页无效（1731 字节 JS Challenge）
- `?get=content` 参数触发服务端渲染，绕过 JS Challenge
- 9 站规则引擎从 owllook 移植，但多数站点已失效
