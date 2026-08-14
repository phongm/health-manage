# 05 · API 设计

Base URL：`https://<已备案域名>/api/health/v1`

## 1. 通用约定

### 1.1 鉴权

除登录接口外，所有请求携带 `Authorization: Bearer <jwt>`。JWT 由后端签发，载荷含 `user_id` 与过期时间。

**服务端强制约束**：所有数据访问在 repository 层从 JWT 解析 `user_id` 并注入查询条件，**绝不接受客户端传入的 user_id**。

### 1.2 统一响应格式

```json
{ "code": 0, "message": "ok", "data": { } }
```

`code` 为 0 表示成功，非 0 为业务错误码。HTTP 状态码同时正确设置（不用 200 表示错误）。

错误码分段：`1xxx` 参数错误，`2xxx` 鉴权，`3xxx` 业务规则，`4xxx` 配额限制，`5xxx` 外部服务（AI 等），`9xxx` 内部错误。

### 1.3 时间与时区

所有时间字段用 ISO 8601 带时区格式。`log_date` 类字段用 `YYYY-MM-DD`，以**用户本地日期**为准（由客户端传入，避免跨时区把凌晨的记录归到前一天）。

## 2. 认证

### POST /auth/login

```jsonc
// 请求
{ "code": "wx_login_code" }

// 响应
{
  "token": "jwt...",
  "is_new_user": true,
  "profile_completed": false   // 决定是否跳引导流程
}
```

后端用 AppSecret 调微信 `code2Session` 换 openid，首次登录自动建 user 记录。

## 3. 用户信息

### GET /profile · PUT /profile

```jsonc
// PUT 请求
{
  "gender": 2, "birth_year": 1995,
  "height_cm": 165, "weight_kg": 60.5,
  "activity_level": 2, "goal": 1, "goal_rate_kg_wk": 0.5,
  "target_weight_kg": 55,
  "health_flags": ["none"]      // 用于识别排除人群
}

// 响应：返回计算结果，端上无需重复计算
{
  "bmr_kcal": 1350.5,
  "tdee_kcal": 1856.9,
  "target_kcal": 1550.0,
  "target_nutrients": { "energy_kcal": 1550, "protein_g": 108.9, "fat_g": 43.1,
                        "cho_g": 155.0, "fiber_g": 27.0, "sodium_mg": 2000 },
  "warnings": ["rate_too_aggressive"],   // 安全边界触发，需在 UI 明示
  "is_excluded": false
}
```

`health_flags` 用于识别排除人群，取值如 `diabetes`、`hypertension`、`pregnant`、`lactating`、`eating_disorder`、`none`。命中任一非 `none` 值时，`is_excluded` 置 true，后续推荐接口返回 `3001` 错误并附带说明文案。

### GET /preferences · PUT /preferences

```jsonc
{
  "allergens": ["peanut", "shrimp"],
  "avoid_ingredients": ["cilantro"],
  "avoid_categories": ["organ_meat"],
  "diet_type": "omnivore",
  "spice_level": 2,
  "scene_default": "takeout",
  "scene_by_meal": { "lunch": "canteen" }
}
```

## 4. 记录

### POST /intake

支持批量（一次录入一餐的多个食物）。

```jsonc
// 请求
{
  "log_date": "2026-08-12",
  "meal_type": "lunch",
  "items": [
    { "food_id": 1024, "grams": 150, "portion_label": "一碗" },
    { "food_id": 2048, "grams": 120, "portion_label": "一份" }
  ],
  "input_source": "recommend",
  "from_rec_id": 88991           // 采纳推荐时必传，用于统计采纳率
}

// 响应：直接返回更新后的今日汇总，省掉一次 dashboard 请求
{
  "created_ids": [10001, 10002],
  "today": { /* 同 GET /dashboard 的 data */ }
}
```

**设计要点**：写入接口直接返回更新后的汇总。这能避免"记录后再请求一次看板"的两次往返，对录入体验影响明显。

### GET /intake?date=2026-08-12
### DELETE /intake/{id}
### POST /exercise · GET /exercise?date=
### GET /weight?from=&to= · POST /weight

体重接口按 `(user_id, log_date)` upsert，同日重复提交为覆盖。响应中额外返回 7 日移动平均：

```jsonc
{
  "logs": [ { "log_date": "2026-08-12", "weight_kg": 60.2 } ],
  "ma7": [ { "log_date": "2026-08-12", "weight_kg": 60.5 } ],
  "trend_kg_per_week": -0.42
}
```

## 5. 看板

### GET /dashboard?date=2026-08-12

```jsonc
{
  "date": "2026-08-12",
  "target":    { "energy_kcal": 1550, "protein_g": 108.9, "fat_g": 43.1, "cho_g": 155, "fiber_g": 27 },
  "intake":    { "energy_kcal": 820,  "protein_g": 45.2,  "fat_g": 22.1, "cho_g": 95,  "fiber_g": 8 },
  "exercise":  { "kcal_burned": 220, "credited_kcal": 154 },   // 只计入 70%
  "remaining": { "energy_kcal": 884,  "protein_g": 63.7, "fat_g": 21.0, "cho_g": 60, "fiber_g": 19 },
  "meals": {
    "breakfast": { "kcal": 320, "logged": true },
    "lunch":     { "kcal": 500, "logged": true },
    "dinner":    { "kcal": 0,   "logged": false },
    "snack":     { "kcal": 0,   "logged": false }
  },
  "next_meal": "dinner"
}
```

端上也能用本地缓存自行计算这份数据（离线降级），云端接口作为对账与首次加载来源。

## 6. 推荐（核心接口）

### POST /recommend

```jsonc
// 请求
{
  "date": "2026-08-12",
  "meal_type": "dinner",
  "scene": "homecook"          // 可选，缺省用 preferences 中的设置
}

// 响应
{
  "rec_id": 88991,
  "meal_type": "dinner",
  "scene": "homecook",
  "items": [
    { "food_id": 2048, "name": "清蒸鸡胸", "role": "protein",
      "grams": 120, "portion_label": "一份",
      "nutrients": { "energy_kcal": 200, "protein_g": 28.5, "fat_g": 6.0, "cho_g": 0 },
      "swappable": true },
    { "food_id": 1024, "name": "米饭", "role": "staple",
      "grams": 150, "portion_label": "一碗",
      "nutrients": { "energy_kcal": 174, "protein_g": 3.9, "fat_g": 0.5, "cho_g": 38.6 },
      "swappable": true },
    { "food_id": 3072, "name": "炒时蔬", "role": "vegetable",
      "grams": 150, "portion_label": "一份",
      "nutrients": { "energy_kcal": 85, "protein_g": 2.1, "fat_g": 5.0, "cho_g": 7.2 },
      "swappable": true }
  ],
  "total": { "energy_kcal": 459, "protein_g": 34.5, "fat_g": 11.5, "cho_g": 45.8 },
  "budget": { "energy_kcal": 480 },
  "reasons": [
    "今天蛋白质还差 64g，这份约能补 35g",
    "热量约 459 kcal，在你晚餐的 480 kcal 额度内"
  ],
  "avoid_list": [
    { "title": "油炸类", "reason": "减脂期脂肪密度过高", "level": "info" },
    { "title": "高脂肉类", "reason": "今日脂肪已达目标的 92%", "level": "alert" }
  ],
  "swaps_remaining": 3,
  "version": "v1.0"
}
```

`swappable` 字段允许引擎标记某个条目不建议替换（例如它是唯一能填补蛋白缺口的选择）。

排除人群调用此接口返回：

```jsonc
{ "code": 3001, "message": "当前版本暂不为该情况提供饮食建议，建议咨询专业人士", "data": null }
```

### POST /recommend/{rec_id}/swap

```jsonc
// 请求
{ "food_id": 2048, "reason": "not_available" }
// reason 取值：not_available / dont_like / too_much / other

// 响应：与 /recommend 相同结构，swaps_remaining 递减
```

超出免费次数时返回 `4001`，附带引导付费的文案（P2 阶段生效）。

### POST /recommend/{rec_id}/feedback

```jsonc
{ "action": "accept", "food_ids": [2048, 1024, 3072] }
// action: accept / ignore / dislike
```

采纳推荐时前端应调用 `POST /intake` 并携带 `from_rec_id`，此接口用于记录"忽略"等非转化行为。

### GET /avoid-list?date=

独立获取今日避雷清单（首页展示，不必等推荐生成）。

## 7. 食物库

### GET /foods/search?q=鸡胸&scene=canteen&limit=20

```jsonc
{
  "items": [
    { "food_id": 2048, "name": "清蒸鸡胸", "category": "poultry",
      "nutrients_per_100g": { "energy_kcal": 167, "protein_g": 23.7 },
      "portions": [ { "label": "一份", "grams": 120, "is_default": true },
                    { "label": "半份", "grams": 60 } ] }
  ]
}
```

搜索需同时匹配 `name` 与 `aliases`，按 `popularity` 排序。端上对高频食物做本地缓存优先命中。

### GET /foods/{id}
### GET /foods/hot?scene=&limit=300

用于端上初始化本地热门食物缓存。

### POST /foods/contribute（P1）

```jsonc
{ "barcode": "6901234567890", "name": "某品牌酸奶", "image_file_id": "..." }
```

提交后进入 `food_contributions` 待审队列，不立即生效。

## 8. 输入解析

### POST /parse/text

```jsonc
// 请求
{ "text": "两个鸡蛋一碗米饭还有一杯豆浆" }

// 响应
{
  "items": [
    { "food_id": 5001, "name": "鸡蛋", "grams": 100, "portion_label": "两个", "confidence": 0.95 },
    { "food_id": 1024, "name": "米饭", "grams": 150, "portion_label": "一碗", "confidence": 0.92 },
    { "food_id": 6002, "name": "豆浆", "grams": 250, "portion_label": "一杯", "confidence": 0.88 }
  ],
  "unresolved": [],
  "parser": "rule"     // rule / llm，用于监控规则覆盖率
}
```

**实现分层**（见 02 文档 5.2）：先走零成本的规则解析（分词 + 食物库模糊匹配 + 数量单位提取），失败项才降级到大模型。响应中的 `parser` 字段用于监控规则覆盖率——覆盖率越高，AI 成本越低。

`unresolved` 中的条目在 UI 上引导用户手动搜索补全，或提交为 UGC。

### POST /parse/image（P1）

```jsonc
// 请求：multipart，或先上传拿 file_id
{ "image_file_id": "..." }

// 响应
{
  "items": [
    { "food_id": 2048, "name": "清蒸鸡胸", "grams": 120,
      "portion_label": "一份", "confidence": 0.72, "need_confirm": true }
  ],
  "unresolved": ["未能识别的第 2 个菜品"]
}
```

**`need_confirm` 是必须有的字段**：图片识别的份量估算误差大，置信度低于阈值（建议 0.8）的条目必须在 UI 上标记为待确认，且份量默认可编辑（用份量档位选择，不让用户填克数）。

图片处理要求：端上压缩至短边 512px 后再上传（降本关键）；服务端校验格式与大小；按用户限流。

## 9. 同步

### GET /sync?since=2026-08-01T00:00:00Z

供端上增量拉取，用于启动时对账与换设备恢复。

```jsonc
{
  "server_time": "2026-08-12T10:00:00Z",
  "profile": { },
  "preferences": { },
  "intake_logs": [ ],
  "exercise_logs": [ ],
  "weight_logs": [ ],
  "deleted": { "intake_logs": [10005], "weight_logs": [] }
}
```

由于云端为真相源（见 02 文档），冲突策略为**云端覆盖本地**，无需三方合并。`deleted` 字段用于同步删除操作。

### POST /sync/batch

上传本地待同步队列（离线期间产生的操作）。要求每个操作携带客户端生成的 `client_op_id`，服务端**幂等处理**，避免网络重试导致重复记录。

## 10. 配额与限流

| 接口 | 免费用户限制 | 实现 |
| --- | --- | --- |
| `/parse/image` | 每日 3 次 | 云端按 user_id 计数 |
| `/recommend/{id}/swap` | 每餐 3 次 | 云端计数 |
| `/recommend` | 每日 20 次 | 防刷 |
| 全局 | 每 IP 每分钟 60 次 | Nginx 或应用层 |

**配额计数必须在云端**。放本地会被用户清缓存绕过。

## 11. 周报、导出与会员

### GET /report/weekly

返回近 7 日记录天数、日均摄入、营养达成率、纤维/微量元素（仅统计食物库中已有字段，缺失不按 0 计）、饮食结构（按食物分类）和体重变化。所有文案为记录与统计参考。

### GET /export

导出当前用户的档案、偏好、摄入、体重和运动记录。

### GET /membership

```jsonc
{ "plan": "free", "payment_enabled": false, "quotas": { "recommend_daily": 20, "swap_per_meal": 3, "parse_image_daily": 3, "plan_days": 3 } }
```

虚拟支付尚未接入。`POST /membership/checkout` 返回 `4001`。
