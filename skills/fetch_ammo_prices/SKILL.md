---
name: fetch_ammo_prices
description: 从 orzice.com 获取三角洲行动游戏子弹实时价格数据，包括名称、等级、金本位、当前价格、今日涨幅，保存为JSON文件。
---

# 获取子弹实时价格 Skill

从 orzice.com 抓取《三角洲行动》游戏所有子弹的实时价格数据（含等级信息）。

## 前置条件

- 需要在 orzice.com 登录后才能查看实时价格
- 需要本地安装 Chromium 内核浏览器（Edge 优先，其次 Chrome）
- 定时采集任务应使用 headless 模式（所有工具调用加 `isHeadless=true`）

### 浏览器路径检测

启动前需自动检测本地浏览器，按以下优先级查找：

1. **Edge（优先）**
   - `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
   - `C:\Program Files\Microsoft\Edge\Application\msedge.exe`

2. **Chrome**
   - `C:\Program Files\Google\Chrome\Application\chrome.exe`
   - `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`

3. **Brave**
   - `C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe`
   - `C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe`

检测逻辑：按优先级顺序遍历路径，使用第一个存在的路径作为 `browser_path`。若均未找到，提示用户安装 Edge 或 Chrome。

## 操作步骤

> **Skill 概述**：本 skill 的核心流程是：打开网页 → 按等级抓取子弹数据 → 保存 JSON → 合并历史数据 → 更新网站（含折线图）→ 关闭浏览器。

### 1. 打开网页并检查登录状态

```
navigate(url="https://orzice.com/v/ammo", browser_path=检测到的浏览器路径, isHeadless=true)
content(url="https://orzice.com/v/ammo", browser_path=..., isHeadless=true)
```

> 注意：首次登录需要用 `isHeadless=false`（默认）手动登录一次，之后 cookies 会保存在 `__browser_profile/` 目录，后续可用 headless 模式。

检查页面文本中是否包含"未登录"字样。如果未登录：
- **提示用户**：请在浏览器中手动登录 orzice.com，登录完成后告知我继续。
- 等待用户确认后再继续。

### 2. 关闭广告和弹窗

```
detect_popups(url="https://orzice.com/v/ammo", browser_path=..., isHeadless=true)
close_popup(url, selector, method="escape", browser_path=..., isHeadless=true)
detect_ads(url="https://orzice.com/v/ammo", browser_path=..., isHeadless=true)
close_ads(url="https://orzice.com/v/ammo", browser_path=..., isHeadless=true)
```

### 3. 按等级逐级获取数据

网站支持通过 URL 参数按等级筛选子弹。核心 URL 格式：

```
https://orzice.com/v/ammo?a=ammo&top=1-2&p={page}&grade={level}&n=
```

**参数说明**：
- `grade`：等级（5=5级、4=4级、3=3级、2=2级、1=1级）
- `p`：页码（从1开始）
- `a=ammo`：弹药类别
- `top=1-2`：排序参数
- `n=`：搜索名称（空=全部）

**按等级循环获取**：从 grade=5 到 grade=1，逐级获取数据。每个等级可能有多页，逐页提取直到某页返回0条数据为止。

```
for grade in [5, 4, 3, 2, 1]:
    page = 1
    while True:
        extract(selector="table tbody tr", url="https://orzice.com/v/ammo?a=ammo&top=1-2&p={page}&grade={grade}&n=", browser_path=..., isHeadless=true)
        if 匹配数为0: break
        记录该页数据（并标记等级=grade）
        page++
```

### 4. 每条数据的结构

每条 extract 结果的结构为：
```
名称
推荐方式：...
    金本位(30发)
    金本位(单价)
        当前价格
        今日涨幅
        3日价格
        3日涨幅
        7日价格
        7日涨幅
        30日价格
        30日涨幅
```

每页10条（最后一页可能不足10条）。注意：部分等级第2页的首条数据可能与第1页末条重复，需要去重。

### 5. 保存数据

将提取的数据整理为 JSON 格式，保存到技能目录下的 `data/` 文件夹中（即 `skills/fetch_ammo_prices/data/`）。

**文件名**：`ammo_prices_{YYYYMMDD_HHmm}.json`（如 `ammo_prices_20260504_1417.json`）

**JSON 数据结构**：

```json
{
  "meta": {
    "title": "三角洲行动 - 子弹实时价格",
    "source": "https://orzice.com/v/ammo",
    "updateTime": "2026-05-04 14:17",
    "total": 87
  },
  "ammo": [
    {
      "name": "子弹名称",
      "grade": 5,
      "goldStandard": 0.41,
      "goldStandardPer": 0.14,
      "currentPrice": 799,
      "todayChange": 29.08
    }
  ]
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 子弹名称 |
| grade | number | 等级（1-5） |
| goldStandard | number | 金本位（30发价格） |
| goldStandardPer | number | 金本位（单价） |
| currentPrice | number | 当前价格（整数） |
| todayChange | number | 今日涨幅（%，正数为涨，负数为跌） |

### 6. 关闭浏览器（可选）

```
shutdown(browser_path=检测到的浏览器路径, isHeadless=true)
```

### 7. 合并历史数据（最近7天）

运行合并脚本，将 `data/` 目录下最近7天的所有快照合并为时序数据：

```
Bash: python tools/merge_history.py
```

- 输出文件：`data/__history_data.json`
- 只处理文件名日期在最近7天内的 `ammo_prices_*.json`
- 只保留 grade >= 3 且 currentPrice > 0 的子弹

### 8. 更新网站

将最新快照数据嵌入 `DATA` 常量，将历史时序数据嵌入 `HISTORY` 常量，生成 `web_template/index.html`：

- 用 `data/__history_data.json` 的内容替换 HTML 中 `const HISTORY = {...};`
- 用最新 JSON 文件的内容替换 HTML 中 `const DATA = {...};`
- 替换时用正则匹配 `const HISTORY = {...};` 和 `const DATA = {...};` 整体替换
- 生成的 `index.html` 放在 `web_template/` 目录下（即 `skills/fetch_ammo_prices/web_template/index.html`）

## 文件存储路径

所有文件均在技能目录 `skills/fetch_ammo_prices/` 下：

```
skills/fetch_ammo_prices/
├── SKILL.md
├── data/
│   ├── ammo_prices_20260504_2204.json
│   ├── __history_data.json
│   └── ...
├── tools/
│   ├── merge_history.py
│   ├── collect_ammo_prices.bat
│   ├── collect_ammo_prices_silent.vbs
│   └── schedule_task.bat
└── web_template/
    ├── index_template.html
    └── index.html           ← 生成的网站
```

## 注意事项

- 按等级获取数据，共5个等级（5级≈17条、4级≈25条、3级≈26条、2级≈12条、1级≈7条，总计约87条）
- 同一等级的相邻页之间可能有1条重复数据，需按名称去重
- 金本位为 0 的子弹表示无交易数据（如 SUB 类子弹）
- 每次获取会生成带日期时间后缀的新文件，不会覆盖历史数据
- 如果浏览器已登录过，cookies 会保存在 `__browser_profile/` 目录，下次无需重新登录
