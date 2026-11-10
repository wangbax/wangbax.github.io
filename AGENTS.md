# 项目约定

- 文章写在 `content/posts/*.md`，站点信息在 `content/site.json`。
- 页面布局改 `scripts/render_site.py`，样式和交互改 `css/`、`js/`。
- HTML、`css/app.css`、`search.json` 由 CI 生成并提交回 `main`；保留版本控制，勿手改。
- 保持暖色星球、手机适配和默认跟随系统的外观切换。
- README 只保留项目介绍和必要链接，详细说明放 `docs/`。
- 使用 `.venv/bin/python`；本地生成运行 `scripts/render_site.py`，检查命令见 `.github/workflows/deploy.yml`。
- 合并到 `main` 后自动发布 ECS；继续修改前先同步 CI 的产物提交。
