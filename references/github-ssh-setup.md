# GitHub SSH 配置速查

## 从零配置 SSH + 推送

```bash
# 1. 生成 ED25519 密钥（无密码）
ssh-keygen -t ed25519 -C "you@example.com" -f ~/.ssh/id_ed25519 -N ""

# 2. 查看公钥（复制到 GitHub Settings → SSH Keys）
cat ~/.ssh/id_ed25519.pub

# 3. 信任 GitHub host key（解决 Host key verification failed）
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts

# 4. 切换 remote 为 SSH
git remote set-url origin git@github.com:user/repo.git

# 5. 推送
git push -u origin master
```

## 常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| `Host key verification failed` | 未信任 GitHub host | `ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts` |
| `Permission denied (publickey)` | 公钥未添加到 GitHub | 去 Settings → SSH Keys 添加 |
| `could not read Username` | HTTPS 在非交互终端无法输入密码 | 改用 SSH 或 Token URL |
