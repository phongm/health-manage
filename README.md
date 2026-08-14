# 健康管理 · 今日吃什么

面向减脂人群的饮食决策助手。设计文档见 [`docs/`](./docs/README.md)。

## 功能对齐（对照 `docs/01`）

### P0

- 基础信息与目标设定（BMR / TDEE / 安全下限）
- 偏好与忌口（过敏原、忌口、不吃的肉、辣度、就餐场景，可按餐覆盖）
- 文字录入（搜索 + 份量档位 + 一句话解析）
- 每日能量收支看板（目标 / 摄入 / 运动 70% / 剩余，含蛋白、碳水、脂肪、纤维、钠）
- 餐次推荐、换一换、今日避雷、一键记入
- 体重记录与 7 日均线
- 运动录入（MET）

排除人群（慢病含肾病、孕产、未成年、低 BMI、进食障碍史）只保留记录，推荐返回 `3001`。

### P1

- 语音录入（微信同声传译插件，未开通时回退文字）
- 图片录入（当前按备注文字解析，条目必须确认份量；每日 3 次）
- 周报（达成率、饮食结构、体重）
- 食物库 UGC（扫码 + 拍营养成分表，待审）
- 多日参考食谱（免费最多 3 天）

### P2 已落地部分

- 膳食纤维与微量元素统计：有数据才展示，缺失不当成 0
- 数据导出（复制 JSON）
- 会员与配额查询；**虚拟支付尚未接入，不会收费**
- 多端原生应用不在本仓库；`miniprogram/core/` 为纯 TS，后端为 HTTPS API，便于以后复用

明确不做：社区、社交、打卡、直播、人工营养师、智能硬件。

## 本地启动

### 后端

```bash
cd server
cp .env.example .env   # 按本机 PostgreSQL 用户名修改 DATABASE_URL
createdb health_manage
uv run alembic upgrade head
uv run python -m app.tools.seed_foods
uv run uvicorn app.main:app --reload --port 8100
uv run pytest
```

开发阶段 `.env` 中 `WECHAT_MOCK_LOGIN=true`，任意 `code` 都会登录到同一个 mock openid。

### 小程序

1. 用微信开发者工具打开 `miniprogram/` 目录
2. 把 `appid` 换成你的小程序 AppID（`project.config.json`）
3. 开发阶段关闭「不校验合法域名」，或把 `http://127.0.0.1:8100` 配进合法域名
4. 语音功能需在小程序后台添加「同声传译」插件（`wx069ba97219f66c71`）；未添加时会提示改用文字
5. `miniprogram/services/api.ts` 里的 `BASE_URL` 上线前改为已备案域名

```bash
cd miniprogram
npm install
npm test
```
