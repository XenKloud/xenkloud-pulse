# Cloud Cost Report — {{CLIENT_NAME}}
**Prepared by Xenkloud Pulse · {{REPORT_DATE}}**

---

## Summary

This month, {{CLIENT_NAME}} spent **${{SPEND_SO_FAR}}** against a budget of **${{BUDGET}}**, currently pacing toward a projected month-end total of **${{PROJECTED}}**.

{{#IF_OVER_BUDGET}}
⚠️ At the current pace, this account is projected to run **{{OVER_PERCENT}}% over budget** this month.
{{/IF_OVER_BUDGET}}
{{#IF_UNDER_BUDGET}}
✅ At the current pace, this account is on track to stay within budget this month.
{{/IF_UNDER_BUDGET}}

We identified **{{ANOMALY_COUNT}} anomalies** and **${{TOTAL_SAVINGS}}/month in available savings** with low-to-medium effort to fix.

---

## Where the money is going

| Service | Monthly cost | Change |
|---|---|---|
{{#EACH_SERVICE}}
| {{SERVICE_NAME}} | ${{SERVICE_VALUE}} | {{SERVICE_DELTA}}% |
{{/EACH_SERVICE}}

---

## What looks unusual

{{#EACH_ALERT}}
**{{ALERT_TITLE}}** — *{{ALERT_LEVEL}}*
{{ALERT_DETAIL}}
Estimated impact: **+${{ALERT_IMPACT}}/month**

{{/EACH_ALERT}}

---

## Recommended fixes, ranked by ease

| # | Fix | Monthly savings | Effort |
|---|---|---|---|
{{#EACH_REC}}
| {{REC_INDEX}} | {{REC_TITLE}} | ${{REC_SAVE}} | {{REC_EFFORT}} |
{{/EACH_REC}}

**Total available savings: ${{TOTAL_SAVINGS}}/month** — roughly **${{ANNUAL_SAVINGS}}/year** if left unaddressed.

---

## Next steps

1. We recommend starting with the "Low effort" items above — these typically take under an hour combined and carry no risk to production.
2. We're happy to implement these fixes directly if you'd prefer not to — just reply and let us know.
3. Xenkloud Pulse continues watching your account daily going forward, so the next spike gets caught before it hits the invoice.

---

*Questions about anything in this report? Reply directly — happy to walk through it live.*

**{{YOUR_NAME}} · Xenkloud**
