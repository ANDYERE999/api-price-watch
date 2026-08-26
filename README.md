# API Price Watch

自动采集多个第三方 AI API 网站的模型价格，统一模型名称，并通过 GitHub Pages 展示跨站比价和历史价格变化。

## 数据源

- SoruxGPT、RTOC、便携 AI：New API 公开价格接口。
- API Hub Asia：Sub2API 公开模型广场；配置 `API_HUB_TOKEN` 后可包含账号可见的专属分组。
- x5m5x：公开报价页 HTML。
- 硅基流动：公开定价页中的 Next.js 服务端数据。

单个数据源失败不会阻止其他网站更新，页面顶部会显示失败状态。采集结果保留网站原始币种，不进行隐式汇率换算。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\update_prices.py
python -m http.server 8000 --directory site
```

本地预览前先将 `web` 和 `data` 复制到 `site`，或直接使用工作流中的 `Assemble static site` 命令。

只采集指定站点：

```powershell
python scripts\update_prices.py --provider api_hub --provider x5m5x
```

## 扩展数据源

1. 在 `src/pricewatch/collectors/` 新建一个返回 `list[PriceRecord]` 的采集器。
2. 在 `src/pricewatch/collectors/__init__.py` 注册采集器类型。
3. 在 `config/providers.json` 增加站点配置。
4. 在 `config/model_aliases.json` 增加同模型的别名。

## GitHub 部署

1. 创建公开 GitHub 仓库并推送到 `main`。
2. 在仓库 `Settings → Pages → Build and deployment` 中选择 `GitHub Actions`。
3. 如需 API Hub 登录后专属分组，在 `Settings → Secrets and variables → Actions` 添加 `API_HUB_TOKEN`。
4. 手动运行一次 `Update prices and deploy Pages`，之后每 6 小时自动更新。

GitHub Actions 的定时任务可能延迟执行，因此页面展示的是最近一次采集时间，不代表秒级实时价格。
