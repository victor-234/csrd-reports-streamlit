import pandas as pd
import streamlit as st
import altair as alt


# Prepare the CSRD DataFrame
df = (
    pd.read_csv("https://docs.google.com/spreadsheets/d/1Nlyf8Yz_9Fst8rEmQc2IMc-DWLF1fpmBTB7n4FlZwxs/export?format=csv&gid=0", skiprows=2)
    .query("verified == 'yes'")
    .rename(columns={
        'SASB industry \n(SICS® Industries)': "industry",
        })
    .merge(
        # Merge Industry-Sector Lookup from separate sheet
        pd.read_csv(
            "https://docs.google.com/spreadsheets/d/1Nlyf8Yz_9Fst8rEmQc2IMc-DWLF1fpmBTB7n4FlZwxs/export?format=csv&gid=218767986#gid=218767986"
            ).rename(columns={
                "SICS® Industries": "industry",
                "SICS® Sector": "sector"
                }
            ), on="industry", how="left"
        )
    .assign(
        link = lambda x: [f"{y}#name={z}" for y, z in zip(x["link"], x["company"])],
        company = lambda x: x["company"].str.strip()
        )
    .loc[:, ['company', 'link', 'country', 'sector', 'industry', "publication date", "pages PDF", "auditor"]]
    .dropna()
    # Merge the standard-counts dataframe
    .merge(
        (
            pd.read_csv("https://docs.google.com/spreadsheets/d/1Vj8yau93kmSs_WqnV5w1V_tdU-JlMo-BV6htDvAv1TI/export?format=csv&gid=1792638779#gid=1792638779")
            .assign(
                company = lambda x: x["company"].str.strip()
                )
            .query("year == 2024")
            .drop("pages", axis=1)
            .drop_duplicates(subset=['company'])
        ),
        on=["company"], how="outer", indicator=True
    )
    .query("_merge != 'right_only'")
    .sort_values("publication date", ascending=True)
)

# Set up page and branding
# st.logo("srn-icon.png", link="https://sustainabilityreportingnavigator.com")
st.set_page_config(layout="wide", page_title="SRN CSRD Archive", page_icon="srn-icon.png")
# st.title("SRN CSRD Report Archive")

st.markdown("""<style> footer {visibility: hidden;} </style> """, unsafe_allow_html=True) 

col1c, col2c = st.columns((0.6, 0.4))
with col1c:
    st.markdown(f"""
                We are crowd-sourcing the collection of CSRD-compliant reports to support prepares and users of sustainability reporting.

                Below, you find a continuously updated list of {len(df)} CSRD-compliant reports.
                
                Want to make an addition? Feel free to do so [using this Google Sheet](https://docs.google.com/spreadsheets/d/1Nlyf8Yz_9Fst8rEmQc2IMc-DWLF1fpmBTB7n4FlZwxs/edit?gid=1695573594#gid=1695573594) and [follow us on LinkedIn](https://www.linkedin.com/company/sustainability-reporting-navigator/).
                """)

with col2c:
    # Custom CSS for Bubble Counter
    st.markdown(
        f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        ">
            <p style="
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100px;
                height: 100px;
                background-color: #4200ff;
                color: white;
                font-size: 36px;
                font-weight: bold;
                border-radius: 50%;
                text-align: center;
                box-shadow: 2px 2px 10px rgba(0,0,0,0.2);
                margin: 0;
            ">
                {len(df)}
            </p>
            <p style="margin-top: 10px;">CSRD reports so far</p>
        </div>
        """,
        unsafe_allow_html=True
    )


st.divider()



# Create filters in two columns
col1, col2 = st.columns(2)

with col1:
    country_options = ["All"] + sorted(df["country"].unique())
    selected_countries = st.multiselect("Select countries", options=country_options, default=["All"])

with col2:
    industry_options = ["All"] + sorted(df["sector"].unique())
    selected_industries = st.multiselect("Select sector", options=industry_options, default=["All"])

# Apply filtering logic
if "All" in selected_countries:
    filtered_countries = df["country"].unique()
else:
    filtered_countries = selected_countries

if "All" in selected_industries:
    filtered_industries = df["sector"].unique()
else:
    filtered_industries = selected_industries

filtered_df = df[
    df["country"].isin(filtered_countries) &
    df["sector"].isin(filtered_industries)
]

# Next, we prepare a list of companies from this filtered DataFrame:
company_list = sorted(filtered_df["company"].unique())

# We add a 'None' item to represent "no company selected yet".
selected_company = st.selectbox(
    label="Search for a company",
    options=[None] + company_list,            # None is the first option
    format_func=lambda x: "Search for a company..." if x is None else x,  # Display text
    index=0                                   # Default to None selected
)

# If the user selects a company, we filter; otherwise we keep all rows.
if selected_company is not None:
    filtered_df = filtered_df[filtered_df["company"] == selected_company]

try:
    tab1, tab2 = st.tabs(["List of reports", "Heatmap of topics reported"])

    with tab1:
        # Display the filtered table with custom formatting and column configurations
        st.dataframe(
            filtered_df.loc[:, ['link', 'company', 'country', 'sector', 'industry', 'publication date', 'pages PDF', 'auditor']],
            column_config={
                # "company": st.column_config.Column(width="medium", label="Company"),
                "link": st.column_config.LinkColumn(
                    label="Company",
                    width="medium", 
                    display_text="^https://.*#name=(.*)$"
                    ),
                "sector": st.column_config.Column(width="medium", label="Sector"),
                "industry": st.column_config.Column(width="medium", label="Industry"),
                "publication date": st.column_config.DateColumn(format="DD.MM.YYYY", width="small", label="Published"),
                "pages PDF": st.column_config.TextColumn(help="The number of pages of the sustainability statement.", label="Pages"),
                "auditor": st.column_config.TextColumn(label="Auditor"),
            },
            hide_index=True,
            use_container_width=True,
            height=35 * len(filtered_df) + 38
        )

    with tab2:
        col1d, _ = st.columns([0.7, 0.3])

        with col1d:
            st.markdown(":gray[For this chart, we counted the number of times, the standard-identifier (e.g., 'E1' for ESRS E1: Climate change) is referenced in the company's sustainability statement.]")
            scale_by_pages = st.checkbox("Scale the references by the length of the sustainability statement", key="scale_by_pages")
            # scale_by_pages = st.session_state.get("scale_by_pages", False)
        
        filtered_melted_df = (
            filtered_df
            .loc[:, ['company', "pages PDF", "esrs 1", "esrs 2", 'e1', 'e2', "e3", "e4", "e5", "s1", "s2", "s3", "s4", "g1", "sbm-3", "iro-1"]]
            .melt(id_vars=["company", "pages PDF"], value_name="hits", var_name="standard")
            .assign(
                standard = lambda x: x["standard"].str.upper(),
                hits=lambda x: x["hits"] / x["pages PDF"] if scale_by_pages else x["hits"]  # Scale if checked
                )
            .dropna()
        )

        if filtered_melted_df.empty:
            st.error(f"We have not analyzed this company yet but will do so very soon!", icon="🚨")

        else:
            heatmap = (
                alt.Chart(filtered_melted_df)
                .mark_rect(stroke="lightgray", filled=True)
                .encode(
                    x = alt.X(
                        "standard", 
                        title=None, 
                        axis=alt.Axis(orient="top"),
                        sort=["esrs 1", "esrs 2", 'e1', 'e2', "e3", "e4", "e5", "s1", "s2", "s3", "s4", "g1", "sbm-3", "iro-1"]
                        ),
                    y = alt.Y("company", title=None),
                    color = alt.Color(
                        "hits", 
                        title="Referenced", 
                        scale=alt.Scale(
                            domain=[0, filtered_melted_df['hits'].max()/2, filtered_melted_df['hits'].max()], 
                            range=['#ffffff', '#a0a0ff', '#4200ff']
                            ),
                        # legend=alt.Legend(orient="none", legendX=520, legendY=-60, tickCount=1, direction="horizontal")
                        ),
                    tooltip = [
                        alt.Tooltip("company",  title="Company"),
                        alt.Tooltip("standard",  title="ESRS topic"),
                        alt.Tooltip("pages PDF",  title="Pages"),
                        alt.Tooltip("hits",  title="Referenced" if not scale_by_pages else "References / pages")
                        ]
                )
                # .properties(
                #     width='container',
                # )
            )
            
            predicate = alt.datum.hits > filtered_melted_df['hits'].max()/2

            labels = (
                alt.Chart(filtered_melted_df)
                .mark_text(
                    fontSize=12,
                    fontWeight="lighter",
                )
                .encode(
                    x="standard",
                    y="company",
                    color=alt.when(predicate).then(alt.value("white")).otherwise(alt.value("gray")),
                    text=alt.Text("hits:Q", format=".1f" if scale_by_pages else ".0f"),
                    tooltip = alt.value(None),
                )
            )

            st.altair_chart(heatmap + labels)

except Exception as e:
    st.error('This is an error. We are working on a fix. In the meantime, check out our Google Sheet!', icon="🚨")
    print(e)



# st.divider()
# col1a, col2a = st.columns(spec=(0.3, 0.7))
# with col1a:
#     st.image("logo.png", width=300)
# with col2a:
#     st.markdown("""
#                 :gray[The platform is part of the Collaborative Research Center TRR 266 [Accounting for Transparency](https://accounting-for-transparency.de).]

#                 :wave: :gray[For questions and feedback, [feel free to reach out](mailto:victor.wagner@lmu.de,maximilian.mueller@wiso.uni-koeln.de)!]
#                 """)


