import pandas as pd
import streamlit as st

st.logo("srn-icon.png", link="https://sustainabilityreportingnavigator.com")
st.title("SRN CSRD Report Archive")
st.markdown("""
            Welcome to the Sustainability Reporting Navigator's CSRD report archive!

            [The SRN](https://sustainabilityreportingnavigator.com/) is an open-science platform to make sustainability reporting accessible for firms and stakeholders. The platform is part of the Collaborative Research Center TRR 266 Accounting for Transparency and jointly hosted and developed by Goethe University, University of Cologne and LMU Munich.
            
            Below, you find a continuously updated list of CSRD-compliant reports.
            
            If you want to make an addition, feel free to do so [using this Google Sheet.](https://docs.google.com/spreadsheets/d/1Nlyf8Yz_9Fst8rEmQc2IMc-DWLF1fpmBTB7n4FlZwxs/edit?gid=1695573594#gid=1695573594) and [follow us on LinkedIn](https://www.linkedin.com/company/sustainability-reporting-navigator/).
            """)

st.divider()

df = pd.read_excel("SRN-CSRD_report_archive.xlsx", sheet_name="csrd")

industry_lookup = (
    pd.read_excel("SRN-CSRD_report_archive.xlsx", sheet_name="industries")
    .rename(columns={
        "SICS® Industries": "Industry",
        "SICS® Sector": "Sector"
    })
)

df = (
    df
    .query("verified == 'yes'")
    .rename(columns={
        "company": "Company",
        "country": "Country",
        'SASB industry \n(SICS® Industries)': "Industry",
        "publication date": "Published",
        "link": "URL",
    })
    .merge(industry_lookup)
    .loc[:, ['Company', 'Country', 'Sector', "Published", 'URL']]
    .dropna()
    .sort_values("Published", ascending=True)
)

country_options = ["All"] + sorted(df["Country"].unique())
industry_options = ["All"] + sorted(df["Sector"].unique())

selected_countries = st.multiselect("Select Countries", options=country_options, default=["All"])
selected_industries = st.multiselect("Select Sector", options=industry_options, default=["All"])


if "All" in selected_countries:
    filtered_countries = df["Country"].unique()
else:
    filtered_countries = selected_countries

if "All" in selected_industries:
    filtered_industries = df["Sector"].unique()
else:
    filtered_industries = selected_industries

filtered_df = df[
    df["Country"].isin(filtered_countries) &
    df["Sector"].isin(filtered_industries)
]

st.dataframe(
    filtered_df.style.format(lambda x: "Link to report" if type(x) == str and x.startswith("https") else x),
    column_config={
        "Company": st.column_config.Column(width="medium"),
        "URL": st.column_config.LinkColumn(),
        "Sector": st.column_config.Column(width="medium"),
        "Published": st.column_config.DateColumn(format="DD.MM.YYYY", width="small")
    },
    hide_index=True,
    use_container_width=True
)

st.divider()
st.image("logo.png", width=300)
st.markdown(":gray[The platform is part of the Collaborative Research Center TRR 266 [Accounting for Transparency](https://accounting-for-transparency.de). For questions and feedback, [feel free to reach out](mailto:victor.wagner@lmu.de,maximilian.mueller@wiso.uni-koeln.de)]")
