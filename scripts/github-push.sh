# Mac Agent Personal — GitHub 推送指南
# 在 macOS Terminal 中逐行执行

# ============================================
# 第一步：设置代理（如果 GitHub 连不上）
# ============================================

# 查看当前代理
git config --global --get http.proxy

# 设置代理（ClashX 默认端口，根据你的代理软件调整）
# git config --global http.proxy http://127.0.0.1:7890
# git config --global https.proxy http://127.0.0.1:7890

# 取消代理
# git config --global --unset http.proxy
# git config --global --unset https.proxy

# ============================================
# 第二步：使用 SSH（推荐，无需代理配置）
# ============================================

# 生成 SSH key（如果还没有）
# ssh-keygen -t ed25519 -C "your_email@example.com"

# 添加到 ssh-agent
# eval "$(agent -s)"
# ssh-add ~/.ssh/id_ed25519

# 复制公钥，打开 https://github.com/settings/keys 添加
# cat ~/.ssh/id_ed25519.pub

# 改用 SSH 地址
# cd ~/workspace/knowagent-personal
# git remote set-url origin git@github.com:moaliangliang/knowagent-personal.git

# ============================================
# 第三步：推送到 GitHub
# ============================================

cd ~/workspace/knowagent-personal

# 查看推送目标
git remote -v

# 推送到 GitHub
git push -u origin main

# ============================================
# 第四步：验证
# ============================================

# 打开浏览器访问
# https://github.com/moaliangliang/knowagent-personal
