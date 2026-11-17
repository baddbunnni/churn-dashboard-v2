# CMP7227 Group Dashboard (v2): Who is more likely to cancel their subscription?

One Streamlit app combining every team member's section. All 243,787 rows are bundled in
`data/subscription_churn.parquet` (8 MB), so it opens with no upload step.

## Where each person clicks (for the group, not shown in the app)

| Sidebar page | Owner | Q1 | Q2 | Q3 / interaction to demo |
|---|---|---|---|---|
| Overview | All | Factor ranking chart; topic cards | | |
| Content preferences | Suraj | Content-type columns (sorted by rate) | Genre bars (sorted) | **Device pills** filter both. **Click a content-type column** to filter genres (as in his Power BI). Genre × device heatmap |
| Plans & pricing | Umaira | Plan bars | Charge-band line | **Click a plan bar** to filter Q2. One line per plan below |
| Engagement | Abdullah | Viewing-hours line | Downloads bars | **Duration slider** filters everything. **Click a viewing point** to filter downloads and highlight the heatmap row |
| Account age | Sunil | Age-band bars | Age × plan heatmap | **Engagement toggle** filters Q1 and Q2. **Click an age bar** to highlight that heatmap row. Light vs heavy viewer lines |
| Customer experience | Nelson | Rating bars | Ticket line | **Click a rating bar** to filter Q2 and highlight the heatmap row |
| Risk profiles | All | Build a profile from every section; top/bottom 10 combinations | | |
| Method & limitations | All | Data checks, calculation, design decisions, limitations | | |

Double-click a chart to clear its selection. Direct links: `/content-preferences`, `/plans-and-pricing`,
`/engagement`, `/account-age`, `/customer-experience`, `/risk-profiles`, `/method`.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a public GitHub repository and upload everything in this folder, keeping the structure
   (`app.py`, `core.py`, `requirements.txt`, `sections/`, `data/`, `.streamlit/`).
   On a Mac, press Cmd+Shift+. in Finder to see the hidden `.streamlit` folder.
2. share.streamlit.io → **Create app** → choose the repo, branch `main`, main file `app.py`.
3. **Advanced settings** → Python 3.12 → **Deploy**.

## Editing

- Shared rules (colours, bands, charts, the calculation, click behaviour) live in `core.py`.
- Each person's section is its own file in `sections/`.
- Set the dataset source text in `DATA_SOURCE` at the top of `core.py`.
