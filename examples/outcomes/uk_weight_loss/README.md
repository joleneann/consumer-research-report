# UK Weight Loss Medication, 30-Day Conversation Study

## Report

[`uk_weight_loss_report.docx`](uk_weight_loss_report.docx): 10,890 items analysed, 15 themes, NSS +14.3%

Open the DOCX for the full deliverable: charts, verbatims, per-theme insights, methodology disclosure and data provenance.

[`uk_weight_loss_insights_data.xlsx`](uk_weight_loss_insights_data.xlsx) is the layer underneath: one tab per theme, every item that theme was built from, with its sentiment, emotion, engagement and source link. [`artifacts_manifest.json`](artifacts_manifest.json) records the run and the collection funnel.

## Study Summary

| | |
|---|---|
| Window | 7 July to 6 August 2026, 30 days |
| Geography | United Kingdom |
| Items collected | 12,450 |
| Items analysed | 10,890 (10,490 conversation, 400 news) |
| Themes | 15, discovered inductively from the corpus |
| Net Sentiment Score | +14.3% |
| Brand Health Score | 64/100 |
| Collection cost | $9.70, all of it Reddit |
| Sources | Reddit r/MounjaroUK and r/WegovyUK, Mumsnet, UK news via Google News RSS, Google Trends for query design only |

## The headline finding: press agenda versus patient agenda

The 400 news articles sit in the corpus to be compared against, not counted with. Every theme carries two shares: how much of press output it takes, and how much of patient conversation.

**85.2% of press output is about companies, share prices, approvals and policy. That subject is 1.1% of patient conversation.** UK coverage of this category is written for investors and policymakers, and patients read almost none of it.

The two largest things in patients' lives get almost no coverage:

| Theme | Patient conversation | Press output |
|---|---|---|
| The weekly weigh-in ritual | 21.7% | 0.2% |
| Dose titration and click-counting | 21.6% | 0.8% |
| Hair loss | 0.8% | 7.0% |
| Business and policy | 1.1% | 85.2% |

A large positive gap means a concern arriving from coverage rather than from customers, which should be answered rather than amplified. A large negative gap means unserved attention.

## Themes

1. The weekly ritual: weigh-ins, plateaus and stalls
2. Dose titration and click-counting economics
3. Side effects and their management
4. Provider shopping, prices and switching
5. Eating mechanics on the medication
6. Food noise and appetite psychology
7. Body image transformations and non-scale victories
8. Stopping, maintenance and regain fear
9. Community ritual and mutual support
10. Eligibility, BMI gates and verification
11. The pill pivot: oral GLP-1s arrive
12. The business and policy layer
13. Stigma, secrecy and telling people
14. Safety, deaths, counterfeits and the grey market
15. Hair loss

## Auditability

Every number in the report traces back to the items behind it.

- **Relevance was measured, not assumed.** A 60-item random-sample audit at seed 7 found 57 of 60 on topic, the 3 misses conversational glue, zero wrong-topic items.
- **Emotion classification is auditable.** Each of the 8 Plutchik emotions is shown with real verbatims from the items scored into it, so the classification can be checked rather than trusted.
- **Query framing bias is documented as a limitation.** Search vocabulary is not conversation vocabulary, and the report says where that mattered. Seed terms came from 284 Google Trends related queries rather than intuition, and themes were still discovered inductively from the corpus rather than taken from Trends.
- **Deviations are recorded.** Two charts and the source labelling were corrected after generation, and the report says so.

## Brief and configuration

- [`brief.json`](brief.json): 12 aspects, 10 business questions, 13 competitors, geography GB, 30-day window
- [`config.json`](config.json): pipeline configuration for the run
