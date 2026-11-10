---
title: 颜色透明度
date: '2017-08-17T17:08:05+08:00'
category: Tools
summary: 由于项目实际开发中，设计师习惯报百分比形容颜色透明度，每次都需要手动换算，非常麻烦，故记录一些常用的透明度换算。
permalink: /2017/08/17/wt-alpha/
---

## 简介 {#简介}
由于项目实际开发中，设计师习惯报百分比形容颜色透明度，每次都需要手动换算，非常麻烦，故记录一些常用的透明度换算。

### 常用 {#常用}

```shell
100% — FF
95% — F2
90% — E6
85% — D9
80% — CC
75% — BF
70% — B3
65% — A6
60% — 99
55% — 8C
50% — 80
45% — 73
40% — 66
35% — 59
30% — 4D
25% — 40
20% — 33
15% — 26
10% — 1A
5% — 0D
0% — 00
```

<a id="more"></a>

### 简单的在线换算工具 {#简单的在线换算工具}
<div id="wt_alpha" class="alpha-tool">
  <div class="alpha-tool-heading"><strong>透明度换算</strong><button type="button" id="wt_switch">切换为 0–255 数值</button></div>
  <div class="alpha-fields"><label for="wt_input"><span id="wt_input_label">百分比（0–100）</span><input type="number" min="0" max="100" step="any" inputmode="decimal" id="wt_input" placeholder="例如 50"></label><span aria-hidden="true">→</span><label>十六进制<output id="wt_result" for="wt_input" aria-live="polite">—</output></label></div>
</div>
