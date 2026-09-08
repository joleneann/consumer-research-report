# Published studies

Four complete studies produced by this engine. Each folder holds a study README, the final DOCX report, a manifest of what the pipeline produced, and the item-level workbook the report is built from, so any figure can be traced back to the items behind it. The research brief sits either in the study folder or in [`../briefs/`](../briefs/), and each study README links its own.

No setup, no credentials and no run are needed to read them. Open a DOCX for the full deliverable: executive summary, theme landscape, per-insight deep dives with radar charts, brand health score, and methodology disclosure.

---

## UK Weight Loss Medication, 30-Day Conversation Study

[Open the study](uk_weight_loss/) · [the report](uk_weight_loss/uk_weight_loss_report.docx) · [the workbook](uk_weight_loss/uk_weight_loss_insights_data.xlsx)

30 days of UK conversation about weight loss medication, collected 7 July to 6 August 2026 from Reddit r/MounjaroUK and r/WegovyUK, Mumsnet, and UK news. 12,450 items collected, 10,890 classified, 15 themes discovered inductively from the corpus. Collection cost $9.70.

The 400 news articles sit in the corpus to be compared against, not counted with, so every theme carries two shares: how much of press output it takes, and how much of patient conversation.

**85.2% of press output is about companies, share prices, approvals and policy. That subject is 1.1% of patient conversation.**

| Theme | Patient conversation | Press output |
|---|---|---|
| The weekly weigh-in ritual | 21.7% | 0.2% |
| Dose titration and click-counting | 21.6% | 0.8% |
| Hair loss | 0.8% | 7.0% |
| Business and policy | 1.1% | 85.2% |

The two largest things in patients' lives get almost no coverage. Relevance was measured rather than assumed: a 60-item random-sample audit at seed 7 found 57 of 60 on topic, the 3 misses conversational glue, zero wrong-topic items.

---

## The other three

| Study | Type | Items | Insights | NSS |
|-------|------|-------|----------|-----|
| [India Hair Colour](hair_colour/) | Topic | 8,969 | 16 | +22.3% |
| [Make in India](make_in_india/) | Brand | 3,516 | 12 | +24.0% |
| [Weight Loss Medication in India](weight_loss/) | Topic | 2,484 | 12 | +16.8% |

India Hair Colour is the largest corpus of the four before filtering: 75,964 items collected across Twitter, YouTube, Instagram, Amazon and Reddit, cut to 8,969 by relevance. Make in India is the only brand study rather than a category study. Weight Loss Medication in India covers the same category as the UK study in a market where the drugs arrived later, which makes the two readable side by side.

---

Method, scoring and known limitations are documented in the [repository README](../../README.md).
