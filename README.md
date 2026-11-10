# wangbax.github.io

[GitHub 仓库](https://github.com/wangbax/wangbax.github.io) · 默认分支：`main`

这是 Hexo / NexT 生成的静态网站，可直接部署到 ECS + Nginx。运行时不需要 Node.js、数据库或 GitHub Pages。文章生成器和原始配置在 [BlogHexo](https://github.com/Tobyyyyyyyyyy/BlogHexo)；本仓库负责发布已生成的页面。

## 当前部署

- 访问地址：http://101.132.127.138
- ECS：`i-uf6ftbyx1ay9g2noxktv`，地域：`cn-shanghai`
- 网站目录：`/var/www/iwyatt/current`
- 历史版本：`/var/www/iwyatt/releases/`
- Nginx 配置：`/etc/nginx/nginx.conf`
- 日志：`/var/log/nginx/access.log`、`/var/log/nginx/error.log`
- 健康检查：`/healthz`
- 安全组：`sg-uf63sbojynwjh1yc5z9g`，已放行公网 TCP 80

已验证公网首页、文章页、CSS、图片、搜索索引和健康检查；不存在的页面返回站点 404，隐藏目录访问返回 403。Nginx 已设置开机自启。

目前使用 IP + HTTP。绑定域名和 HTTPS 时，需要准备域名解析与证书，并用新的访问地址重新打包。

## 本地打包

要求 Python 3.9+、Git。

```sh
python3 scripts/package_site.py --site-url http://101.132.127.138
```

输出为 `.release/site.tar.gz` 和 `.release/site.tar.json`。打包时会将页面与搜索索引中的旧地址 `iwyatt.cc` 替换为 `--site-url` 指定的地址，源页面保持原样。网站使用根路径，`--site-url` 只接受 `http(s)://主机[:端口]`。

发布包只包含站点文件和现有静态资源目录，不包含 `.git`、凭据、部署脚本、README 或 GitHub Pages 的 `CNAME`。新增页面请先加入 Git 跟踪；新增顶层资源目录时，更新 `scripts/package_site.py` 中的目录清单。字体和 Gitalk 评论仍使用原网站的外部服务。

## 凭据

安装官方 Workbench CLI，使用本机 `~/.workbench/config.json` 中的凭据，文件权限必须为 `0600`。密钥不要写入仓库、发布包或命令行参数。所需 RAM 权限见 `alibabacloud-workbench-cli` Skill。

```sh
workbench version
workbench exec --instance-id i-uf6ftbyx1ay9g2noxktv --command 'id'
```

## 发布新版本

### 合并 main 后自动发布

GitHub Actions 工作流 `.github/workflows/deploy.yml` 会在 PR 中校验站点；推送或合并到 `main` 后，校验通过即自动部署到阿里云 ECS。也可在仓库 Actions 页面通过 **Run workflow** 手动重新发布 `main`。

流水线会固定使用 Workbench CLI `v1.0.4` 并验证官方 SHA256，打包站点、上传独立版本、原子切换 `current`，最后检查公网首页内容、静态资源、健康检查及错误状态。并发发布会按顺序执行，旧版本保留用于回退。

阿里云凭据通过 GitHub OIDC 换取有效期 30 分钟的 STS 凭据。信任策略限制到本仓库的不可变身份和 `main` 分支，PR 无法取得发布角色。权限策略和信任策略分别保存在 `deploy/ram-policy.json`、`deploy/ram-trust-policy.json`。

以下 GitHub Repository Variables 已配置，均为非密钥配置：

| 变量 | 用途 |
| --- | --- |
| `ALIBABA_CLOUD_OIDC_PROVIDER_ARN` | 阿里云 GitHub OIDC 身份提供商 |
| `ALIBABA_CLOUD_ROLE_ARN` | 发布专用 RAM 角色 |
| `ECS_INSTANCE_ID` | 目标 ECS 实例 |
| `ECS_REGION` | 目标地域 |
| `SITE_URL` | 网站公网地址 |

发布结果和健康检查见 [Actions](https://github.com/wangbax/wangbax.github.io/actions/workflows/deploy.yml)。迁移服务器或改域名后，需同步调整变量、RAM 权限和 Nginx 配置。

### 本机手动发布

服务器首次安装已完成。以下命令会上传独立版本并切换 `current` 软链接，不需要重启 Nginx。旧版本保留在 `releases/`，`previous` 指向发布前的版本。

```sh
INSTANCE_ID=i-uf6ftbyx1ay9g2noxktv
RELEASE_ID=$(date -u +%Y%m%dT%H%M%SZ)
python3 scripts/package_site.py --site-url http://101.132.127.138
ARCHIVE_SHA256=$(shasum -a 256 .release/site.tar.gz | awk '{print $1}')

workbench exec --instance-id "$INSTANCE_ID" --command "test ! -e /var/tmp/iwyatt-${RELEASE_ID}.tar.gz && test ! -e /var/tmp/iwyatt-${RELEASE_ID}-publish.sh"
workbench upload .release/site.tar.gz "/var/tmp/iwyatt-${RELEASE_ID}.tar.gz" --instance-id "$INSTANCE_ID"
workbench upload deploy/publish.sh "/var/tmp/iwyatt-${RELEASE_ID}-publish.sh" --instance-id "$INSTANCE_ID"
workbench exec --instance-id "$INSTANCE_ID" --command "bash /var/tmp/iwyatt-${RELEASE_ID}-publish.sh ${RELEASE_ID} ${ARCHIVE_SHA256}"
curl --fail http://101.132.127.138/healthz
```

每条命令成功后再执行下一条。`publish.sh` 会先验证压缩包 SHA256、Nginx 配置和必要文件，再切换版本；发布目录已存在时会拒绝覆盖。

## 另一台服务器的首次配置

`deploy/nginx.conf` 是独立站点的完整 Nginx 配置，仅适合专用服务器；已有网站的服务器应将相应 `server` 配置合并到现有配置中。

在 Alibaba Cloud Linux 3 上安装 `nginx`，保存原配置备份后，将 `deploy/nginx.conf` 安装到 `/etc/nginx/nginx.conf`，运行 `nginx -t`。按上面的发布流程上传首个版本后，执行 `systemctl enable --now nginx`。ECS 安全组需要允许 TCP 80；配置 HTTPS 后再开放 TCP 443。

## 回退与检查

回退前先用 Workbench 查看 `readlink /var/www/iwyatt/previous`，确认要恢复的版本；将 `current` 软链接切到该版本即可，文件和历史版本无需删除。

```sh
workbench exec --instance-id i-uf6ftbyx1ay9g2noxktv --command 'systemctl is-active nginx; nginx -t; readlink /var/www/iwyatt/current; tail -n 20 /var/log/nginx/error.log'
curl --fail http://101.132.127.138/
curl --fail http://101.132.127.138/2017/08/17/wt-alpha/
```

## 鸣谢

- [原博客源码](https://github.com/Tobyyyyyyyyyy/Tobyyyyyyyyyy.github.io)
- [Hexo](https://hexo.io/)
- [NexT](https://github.com/theme-next/hexo-theme-next)
- [Cloudflare](https://www.cloudflare.com)
