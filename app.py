import pandas as pd
import streamlit as st

# Define CSV export URLs for each sheet
# (Update the gid values if needed to match the correct sheet)
csrd_url = "https://docs.google.com/spreadsheets/d/1Nlyf8Yz_9Fst8rEmQc2IMc-DWLF1fpmBTB7n4FlZwxs/export?format=csv&gid=0"

# Load data from the Google Sheet CSV exports
df = pd.read_csv(csrd_url, skiprows=2)
industry_lookup = pd.read_csv("https://docs.google.com/spreadsheets/d/1Nlyf8Yz_9Fst8rEmQc2IMc-DWLF1fpmBTB7n4FlZwxs/export?format=csv&gid=218767986#gid=218767986")

# Prepare the CSRD DataFrame
df = (
    df
    .query("verified == 'yes'")
    .rename(columns={
        "company": "Company",
        "country": "Country",
        'SASB industry \n(SICS® Industries)': "Industry",
        "publication date": "Published",
        "link": "URL",
        "pages PDF": "Pages",
        "auditor": "Auditor",
    })
    .merge(industry_lookup.rename(columns={
        "SICS® Industries": "Industry",
        "SICS® Sector": "Sector"
    }), on="Industry", how="left")
    .assign(URL = lambda x: [f"{y}#name={z}" for y, z in zip(x["URL"], x["Company"])])
    .loc[:, ['Company', 'URL', 'Country', 'Sector', 'Industry', "Published", "Pages", "Auditor"]]
    .dropna()
    .sort_values("Published", ascending=True)
)

# Set up page and branding
# st.logo("srn-icon.png", link="https://sustainabilityreportingnavigator.com")
st.set_page_config(layout="wide", page_title="SRN CSRD Archive", page_icon="srn-icon.png")
# st.title("SRN CSRD Report Archive")

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
    country_options = ["All"] + sorted(df["Country"].unique())
    selected_countries = st.multiselect("Select countries", options=country_options, default=["All"])

with col2:
    industry_options = ["All"] + sorted(df["Sector"].unique())
    selected_industries = st.multiselect("Select sector", options=industry_options, default=["All"])

# Apply filtering logic
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

# Next, we prepare a list of companies from this filtered DataFrame:
company_list = sorted(filtered_df["Company"].unique())

# We add a 'None' item to represent "no company selected yet".
selected_company = st.selectbox(
    label="Search for a company",
    options=[None] + company_list,            # None is the first option
    format_func=lambda x: "Search for a company..." if x is None else x,  # Display text
    index=0                                   # Default to None selected
)

# If the user selects a company, we filter; otherwise we keep all rows.
if selected_company is not None:
    filtered_df = filtered_df[filtered_df["Company"] == selected_company]

try:
    # Display the filtered table with custom formatting and column configurations
    st.dataframe(
        filtered_df.drop("Company", axis=1),
        column_config={
            "Company": st.column_config.Column(width="medium"),
            "URL": st.column_config.LinkColumn(
                label="Company",
                width="medium", 
                display_text="^https://.*#name=(.*)$"
                ),
            "Sector": st.column_config.Column(width="medium"),
            "Published": st.column_config.DateColumn(format="DD.MM.YYYY", width="small")
        },
        hide_index=True,
        use_container_width=True,
        height=35 * len(filtered_df) + 38
    )

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

hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
