# Playwright WSL 无 Sudo 安装

> 适用: WSL 环境，无 root 权限，Python 3.13+
> 目标: 运行 Headless Chromium 抓取 JS 渲染的页面

## 安装步骤

```bash
# 1. 安装 playwright Python 包
pip install playwright -q

# 2. 下载 Chromium 浏览器（~150MB，需几分钟）
python3 -m playwright install chromium

# 3. 检查缺失的系统库
ldd ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \
  | grep "not found"
# 典型输出: libnspr4.so, libnss3.so, libnssutil3.so

# 4. 用 apt download 获取缺失的 so 文件（无需 sudo）
apt download libnspr4 libnss3
dpkg-deb -x libnspr4_*.deb /tmp/nspr
dpkg-deb -x libnss3_*.deb /tmp/nss
find /tmp/nspr /tmp/nss -name "*.so*" -exec cp {} ~/miniconda3/lib/ \;

# 5. 设置 LD_LIBRARY_PATH (每次启动新 shell 需执行)
export LD_LIBRARY_PATH=~/miniconda3/lib:$LD_LIBRARY_PATH
```

## 验证

```python
import os
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/miniconda3/lib') + ':' + os.environ.get('LD_LIBRARY_PATH', '')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox'])
    print(f'OK: {b.version}')  # 预期: 148.0.7778.96
    b.close()
```

## 已知问题

- 必须设置 `LD_LIBRARY_PATH`，否则报 `error while loading shared libraries: libnspr4.so`
- `--no-sandbox` 在无 root 环境必须
- playwright 1.60 使用 `chromium_headless_shell` 而非完整 Chrome，依赖更少
- 完整 Chrome 需要 121 个系统依赖，WSL 无 sudo 下不可行
- trxs.cc（同人小说站）用此方案可抓取到完整章节（3000-17000 汉字）
