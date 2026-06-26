---
name: daily-review-wechat
description: Use when the user wants a bigATrade daily review, stock recap, WeChat public-account post, review poster, cover image, image-text recap, today review, or next-day trading commentary based on tracked recommendation stocks. Use for requests that need a WeChat-ready title, cover image, short article copy, poster copy, and tomorrow plan from `stock_recommendation_daily_quotes`.
---

# Daily Review Wechat

## Overview

Use this skill to turn the day's tracked recommendation stocks into a WeChat-ready recap that is optimized for WeChat public-account reading, Search visibility, retention, comments, and soft conversion.

The article is not only a result report. It should teach the reader how to read market emotion, sector leadership, intraday support, and next-day scenarios through the tracked recommendation stocks.

Use five fixed sections by default:

1. Title
2. Cover image
3. Poster copy
4. Today review
5. Tomorrow plan

The final user-facing output must be in Chinese. Keep it segmented, practical, and ready to paste into a WeChat article draft. When the user asks for more detail, expand the review and tomorrow plan instead of adding generic filler. When the user asks for a WeChat article, daily review, stock recap, or image-text recap, generate a cover image by default unless the user explicitly says not to generate one.

## Data Source

Always prefer corrected tracked data from `stock_recommendation_daily_quotes`, not recommendation-day assumptions.

Minimum join:

- `stock_recommendation_daily_quotes q`
- `stock_recommendations sr`

Key fields:

- `q.trade_date`
- `q.stock_code`
- `q.stock_name`
- `q.close_price`
- `q.change_pct`
- `q.amount`
- `q.gain_from_recommend_pct`
- `q.hit_target`
- `q.hit_stop_loss`
- `sr.buy_price`
- `sr.target_price`
- `sr.stop_loss_price`
- `sr.recommend_reason`
- `sr.risk_tip`

If available, also pull market context from a public index quote source for:

- SSE Composite
- SZSE Component
- ChiNext

## Workflow

1. Query the latest review date or the user-specified date from `stock_recommendation_daily_quotes`.
2. Join recommendation metadata from `stock_recommendations`.
3. Pull or infer market context before writing: index direction, market breadth, active sectors, and risk appetite.
4. Build a one-sentence market emotion judgment first:
   - strong repair
   - trend continuation
   - high-level divergence
   - weak repair
   - broad selloff
   - mixed market
5. Identify the article's main search theme from the day's data:
   - core stock, such as `凯盛科技`
   - core sector, such as `CPO`, `PCB`, `半导体`, `小金属`, `商业航天`
   - article intent, such as `今日A股复盘`, `明日策略`, `涨停复盘`, `短线情绪`
6. Rank the tracked stocks into:
   - strongest
   - supported but divergent
   - high-volatility divergence
   - weak and risk-first
7. Assign each stock a market role, not only a gain/loss label:
   - core validation stock
   - sector extension stock
   - trend support stock
   - capacity震荡 stock
   - weak observation stock
8. Write WeChat copy using the fixed structure below.
9. Generate a Chinese WeChat finance cover image by default for complete article/review requests. Use the available image generation tool directly when present. Only skip image generation when the user explicitly asks for text only, draft only, no image, or no cover.
10. If the user asks for a poster or image-text version, produce a compact Chinese prompt for the image generation tool with explicit prices, change percentages, turnover, and one-line labels.

## Judgment Rules

Use these heuristics consistently:

- `change_pct` and `gain_from_recommend_pct` are the primary performance numbers.
- `amount` is a heat indicator, not a strength guarantee.
- A close near the high plus a strong gain implies stronger initiative.
- High volume plus a weak close implies divergence, not one-sided strength.
- `hit_stop_loss = true` means the copy must explicitly mention pressure or risk.
- `hit_target = true` means the copy can mention target validation or strong continuation.
- A strong stock with intraday divergence and later recovery should be framed as "分歧后承接验证", not simply "涨了".
- A large high open is not automatically a buy signal. The copy should emphasize whether post-open divergence is supported.
- If the user asks for next-day price positions, use real close, high, low, buy range, target, and stop-loss fields to build scenario levels.

For wording about funds, accumulation, and support:

- Only infer from public price, turnover, and visible quote structure when available.
- Never present these as exact institutional flows unless that source was actually queried.
- Safe wording:
  - funds were more active
  - there was intraday support
  - late-session selling pressure remained
  - this looked more like a divergence trade

## Search And Discovery Rules

Optimize every article for WeChat Search without keyword stuffing.

### Search Keywords

Each article should naturally include several of these terms when relevant:

- `A股复盘`
- `今日复盘`
- `明日策略`
- `盘前计划`
- `短线情绪`
- `涨停复盘`
- `强势股`
- active sector names such as `CPO`, `PCB`, `半导体`, `小金属`, `商业航天`, `AI算力`, `存储芯片`
- core stock names and stock codes from the tracked list

### Title SEO

Titles should follow this pattern when possible:

`核心个股/板块 + 明确情绪判断 + 用户关心的问题`

Good examples:

- `凯盛科技涨停回封，CPO继续发酵：明日强势股怎么处理？`
- `CPO和小金属继续走强：今日A股复盘与明日策略`
- `强势股分歧后谁敢接？从凯盛科技看明日盘前计划`

Avoid titles that only old followers understand, such as:

- `今天又吃肉了`
- `这批推荐股表现不错`
- `5只票复盘`

### Opening Hook

The first 80 to 120 Chinese characters must contain:

- market emotion
- the strongest stock or sector
- one reader-facing question
- the article intent, such as `今日复盘` or `明日策略`

Example:

`今天A股情绪明显回暖，CPO和小金属继续活跃。凯盛科技完成涨停回封，华脉科技和盛屯矿业也给出溢价。今天这篇复盘，重点讲三个问题：强势股分歧后怎么看、凯盛科技明天怎么处理、CPO方向还能不能延续。`

### Suggested Topic Tags

When useful, include a short "建议话题标签" line after the article:

- `#A股复盘`
- `#明日策略`
- `#涨停复盘`
- `#短线情绪`
- one or two sector tags, such as `#CPO`, `#小金属`, `#半导体`

Do not add unrelated hot tags.

## Cover Image Defaults

Always generate a cover image for full WeChat article/review requests unless the user explicitly opts out.

The cover image must:

- Use the final recommended title or the user's specified title as the main headline.
- Use the article's main contradiction as the subtitle, such as index strength vs weak breadth, core validation vs divergence, or profit protection vs chasing.
- Include the review date.
- Include available index performance and breadth, such as SSE Composite, SZSE Component, ChiNext, number of rising/falling stocks, or a user-provided breadth figure.
- Highlight 1-2 core stocks from the article with code, close, daily change, key intraday level, turnover, and a short role label.
- Include the remaining tracked stocks in a compact list when space allows.
- End with a one-line conclusion that matches the article thesis.
- Avoid guaranteed-return language, direct buy/sell instructions, broker logos, QR codes, and "get rich" visuals.

If the generated image may contain imperfect text, still provide it, then briefly state the intended cover copy so the user can verify the key numbers.

## Output Contract

Unless the user asks otherwise, return in this order.

### 1. Title

Give 3 options:

- one conservative
- one more viral
- one recommended default

Each option should include at least one searchable keyword: a stock name, a sector name, `A股复盘`, `明日策略`, `短线情绪`, or `涨停复盘`.

### 2. Cover Image

Generate and show a cover image before the full article body for WeChat article/review requests. After showing it, include one short sentence naming the headline and core data used.

### 3. Poster Copy

Keep it compact. Include:

- main title
- subtitle
- one market sentence
- short labels for the tracked stocks
- one closing conclusion

### 4. Today Review

Write 6 to 10 short paragraphs unless the user asks for a shorter draft.

Rules:

- Use paragraphs, not a long bullet list.
- Bold stock names like `**Da You Neng Yuan**` in the source draft, but output the real Chinese stock names for the user.
- Each paragraph should carry one core point.
- Do not overload every sentence with numbers. Keep only the strongest figures.
- Start with the reader's pain point or decision conflict, not a plain result list.
- Explain the chain `yesterday's plan -> today's market verification -> tomorrow's scenario`.
- For each key stock, explain market role and fund attitude, not only percentage change.
- Include at least one sentence that turns the recap into a learning point, such as `真正重要的不是涨停本身，而是分歧后资金还愿不愿意接。`
- When appropriate, add a soft conversion sentence in the middle or near the end: `想系统学习盘前推演、盘中验证和盘后复盘的朋友，可以点我头像，私信我。`

### 5. Tomorrow Plan

Write 5 to 8 short paragraphs unless the user asks for a shorter draft.

Rules:

- Focus on what to watch and how to respond.
- Do not give absolute buy or sell instructions.
- Prefer language like:
  - focus on whether strength can continue
  - watch whether a high open can hold
  - first confirm whether repair is real
  - if weakness continues, stay cautious
- Prefer scenario writing:
  - if high open is too aggressive, do not chase the first impulse
  - if pullback is supported near a real price level, watch for a second confirmation
  - if volume expands but price cannot recover, protect gains first
  - if sector leadership weakens, lower expectations for follower stocks
- When price levels are requested, use real levels from data:
  - previous close
  - latest close
  - intraday high and low
  - buy range
  - target price
  - stop-loss price

## WeChat Style Rules

- Use short paragraphs.
- Highlight stock names with bold markdown.
- Keep the tone like a post-close recap, not like a broker research note.
- Cut empty transitions.
- Numbers must be real and sourced from queried data.
- If the user says the copy is too long, compress aggressively.
- Use stronger subheadings than generic labels. Prefer:
  - `一、今日A股复盘：情绪到底强在哪里？`
  - `二、核心个股：涨停回封说明什么？`
  - `三、5只推荐股表现：谁主动，谁跟随，谁偏弱？`
  - `四、明日策略：高开不追，回踩看承接`
- Avoid writing like a raw performance table. The reader should learn a method.
- Design one comment prompt near the end, for example:
  - `如果明天核心票一字板后开板，你会先保收益，还是等二次回封？评论区说说你的处理方式。`
  - `你更想看我明天重点拆CPO，还是小金属？留言多的方向，我盘前单独写。`

## Conversion And Compliance

- The article should softly guide interested readers to click the avatar or send a private message, but it must not sound like hard advertising.
- Good conversion wording:
  - `复盘不是事后解释涨跌，而是盘前建立剧本、盘中验证资金、盘后修正策略。想系统学习这套方法的朋友，可以点我头像，私信我。`
  - `很多人亏钱不是因为不努力，而是没有一套可执行的盘前和盘中判断框架。`
- Avoid guaranteed-return or direct trading language:
  - `必涨`
  - `直接买`
  - `保证吃肉`
  - `目标翻倍`
- Always include a risk reminder when the output is a full article:
  - `以上内容仅为个人复盘记录和学习交流，不构成投资建议。市场有风险，操作需谨慎。`

## Poster Prompt Rules

When generating an image prompt:

- Explicitly say it is a Chinese WeChat finance infographic.
- Use a vertical layout.
- Include the review date.
- Include index performance.
- Include each stock's name, code, close, change, turnover in yi, and short label.
- End with a one-line conclusion such as "Today strongest: XX; the rest were mostly divergence or repair trades."

## Resources

- Read `references/wechat-template.md` when you need the exact reusable article skeleton.
