# VPN 配置指南

知行支持两种 VPN：**深信服 aTrust** 和 **FortiGate**。

## 快速配置

```bash
# 编辑配置文件
vim ~/.zhixing/config.yaml
```

在 `proxy` 段添加：

```yaml
proxy:
  enabled: true               # 开启 VPN
  vpn_type: atrust             # 或 fortinet
  http: http://127.0.0.1:7890
  https: http://127.0.0.1:7890
  socks: ""
  no_proxy: localhost,127.0.0.1,.local
  vpn_host: vpn.example.com    # VPN 服务器地址
  vpn_port: 443                 # VPN 端口
```

## 深信服 aTrust

### 前置条件

- 深信服 aTrust 客户端已安装
- 浏览器登录 aTrust Web 门户

### 使用方法

```bash
# 查看 VPN 状态
zhi vpn_status action=status

# 启用 VPN（开启代理）
zhi vpn_status action=enable

# 关闭 VPN（关闭代理）
zhi vpn_status action=disable

# 登录 aTrust（通过浏览器打开登录页面）
zhi vpn_status action=login

# 连接检测（检查网络连通性）
zhi vpn_status action=connect
```

### 登录流程

1. `zhi vpn_status action=login` — 在默认浏览器中打开登录页
2. 输入 VPN 账号密码完成登录
3. `zhi vpn_status action=enable` — 开启代理
4. `zhi vpn_status action=status` — 确认连接成功

### 完整诊断

```bash
zhi vpn_status action=connect
```

输出示例：
```
🔍 连通性诊断:
  ✅ DNS 解析成功
  ✅ TCP 连接成功 (xx ms)
  ✅ TLS 握手成功
  ✅ HTTP 响应正常
  🌐 代理: 已启用 (http://127.0.0.1:7890)
  📍 当前 IP: x.x.x.x
```

---

## FortiGate VPN

### 前置条件

- `openfortivpn` 已安装：`brew install openfortivpn`
- 已有 FortiGate VPN 账号

### 配置

```yaml
proxy:
  enabled: true
  vpn_type: fortinet
  fortinet:
    host: vpn.fortigate.com      # FortiGate 服务器地址
    port: 10443                   # 端口（默认 10443）
    username: ""                  # VPN 用户名
    password: ""                  # VPN 密码（建议用 Keychain 存储）
    trusted_cert: ""              # 证书指纹（首次连接时获取）
```

**安全提示：** 用户名密码建议通过 Keychain 存储，不要写在配置文件中：

```bash
zhi credential set name=vpn_username password=your_username
zhi credential set name=vpn_password password=your_password
```

### 使用方法

```bash
# 连接 FortiGate VPN
zhi vpn_status action=fortinet_connect

# 断开 FortiGate VPN
zhi vpn_status action=fortinet_disconnect

# 查看 VPN 状态
zhi vpn_status action=status
```

### 首次连接

```bash
zhi vpn_status action=fortinet_connect
```

首次连接时会提示证书验证，需要确认证书指纹。后续会自动信任。

---

## 代理设置

VPN 启用后，自动设置 HTTP/HTTPS 代理：

- HTTP 代理：`http://127.0.0.1:7890`
- HTTPS 代理：`http://127.0.0.1:7890`
- 排除：`localhost`, `127.0.0.1`, `.local`

可通过 `zhi config set proxy.http=...` 自定义。

## 常见问题

### VPN 已启用但无法访问内网

```bash
# 检查代理是否生效
zhi config get proxy.enabled

# 手动测试代理
curl -x http://127.0.0.1:7890 https://内网地址
```

### 证书错误

```bash
# 更新 trusted_cert
zhi vpn_status action=fortinet_connect
# 复制输出的证书指纹
zhi config set proxy.fortinet.trusted_cert=新指纹
```

### 端口被占用

```bash
lsof -i :7890             # 查看谁占用了端口
pkill -f "ssh\|openfortivpn"  # 杀掉旧进程
```
