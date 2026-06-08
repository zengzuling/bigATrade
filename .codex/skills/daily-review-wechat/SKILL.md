---
name: daily-review-wechat
description: Use when the user wants a bigATrade daily review, stock recap, WeChat public-account post, review poster, image-text recap, today review, or next-day trading commentary based on tracked recommendation stocks. Use for requests that need a title, short article copy, poster prompt, and tomorrow plan from `stock_recommendation_daily_quotes`.
---

# Daily Review Wechat

## Overview

Use this skill to turn the day's tracked recommendation stocks into a WeChat-ready recap with four fixed sections:

1. Title
2. Poster copy
3. Today review
4. Tomorrow plan

The final user-facing output must be in Chinese. Keep it short, segmented, and ready to paste into a WeChat article draft.

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
3. Build a market summary first: strong market, weak market, or mixed market.
4. Rank the tracked stocks into:
   - strongest
   - supported but divergent
   - high-volatility divergence
5. Write WeChat copy using the fixed structure below.
6. If the user asks for a poster or image-text version, produce a compact Chinese prompt for `GPT-IMAGE-2` with explicit prices, change percentages, turnover, and one-line labels.

## Judgment Rules

Use these heuristics consistently:

- `change_pct` and `gain_from_recommend_pct` are the primary performance numbers.
- `amount` is a heat indicator, not a strength guarantee.
- A close near the high plus a strong gain implies stronger initiative.
- High volume plus a weak close implies divergence, not one-sided strength.
- `hit_stop_loss = true` means the copy must explicitly mention pressure or risk.
- `hit_target = true` means the copy can mention target validation or strong continuation.

For wording about funds, accumulation, and support:

- Only infer from public price, turnover, and visible quote structure when available.
- Never present these as exact institutional flows unless that source was actually queried.
- Safe wording:
  - funds were more active
  - there was intraday support
  - late-session selling pressure remained
  - this looked more like a divergence trade

## Output Contract

Unless the user asks otherwise, return in this order.

### 1. Title

Give 3 options:

- one conservative
- one more viral
- one recommended default

### 2. Poster Copy

Keep it compact. Include:

- main title
- subtitle
- one market sentence
- short labels for the tracked stocks
- one closing conclusion

### 3. Today Review

Write 4 to 7 short paragraphs.

Rules:

- Use paragraphs, not a long bullet list.
- Bold stock names like `**Da You Neng Yuan**` in the source draft, but output the real Chinese stock names for the user.
- Each paragraph should carry one core point.
- Do not overload every sentence with numbers. Keep only the strongest figures.

### 4. Tomorrow Plan

Write 3 to 5 short paragraphs.

Rules:

- Focus on what to watch and how to respond.
- Do not give absolute buy or sell instructions.
- Prefer language like:
  - focus on whether strength can continue
  - watch whether a high open can hold
  - first confirm whether repair is real
  - if weakness continues, stay cautious

## WeChat Style Rules

- Use short paragraphs.
- Highlight stock names with bold markdown.
- Keep the tone like a post-close recap, not like a broker research note.
- Cut empty transitions.
- Numbers must be real and sourced from queried data.
- If the user says the copy is too long, compress aggressively.

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
