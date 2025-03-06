import os
import requests

import pandas as pd
import streamlit as st
import altair as alt

from streamlit_pdf_viewer import pdf_viewer
from openai import OpenAI
# from dotenv import load_dotenv

from helpers import read_data
from helpers import define_standard_info_mapper
from helpers import plot_ui
from helpers import plot_heatmap
from helpers import download_pdf
    
# load_dotenv()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ------------------------------------ SETUP ----------------------------------
st.set_page_config(layout="wide", page_title="SRN CSRD Archive", page_icon="srn-icon.png")
st.markdown("""<style> footer {visibility: hidden;} </style> """, unsafe_allow_html=True)


# ------------------------------------ DATA ----------------------------------
df = read_data()
standard_info_mapper = define_standard_info_mapper()

if "selected_companies" not in st.session_state:
    st.session_state.selected_companies = set()


# ------------------------------------ WELCOME ----------------------------------
left_main_col, right_main_col = st.columns((0.6, 0.4))
with left_main_col:
    plot_ui("welcome-text", df=df)

with right_main_col:
    # Custom CSS for Bubble Counter
    plot_ui("bubble-counter", df=df)

st.divider()


# ------------------------------------ FILTERS ----------------------------------
st.markdown("### Filters")

col1, col2, col3 = st.columns(3)
with col1:
    country_options = ["All"] + sorted(df["country"].unique())
    selected_countries = st.multiselect("Filter by country", options=country_options, default=["All"], key="tab1_country")

with col2:
    industry_options = ["All"] + sorted(df["sector"].unique())
    selected_industries = st.multiselect("Filter by sector", options=industry_options, default=["All"], key="tab1_industry")

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

with col3:
    selected_companies = st.multiselect(
        label="Filter by name",
        options=[None] + sorted(df["company"].unique()),
        default=None,
        key="tab1_selectbox"
    )

# If the user selects a company, we filter; otherwise we keep all rows.
if len(selected_companies) != 0:
    filtered_df = filtered_df[filtered_df["company"].isin(selected_companies)]





try:
    tab1, tab2 = st.tabs(["List of reports", "Heatmap of topics reported"])

    # ------------------------------------ TABLE ----------------------------------
    with tab1:

        table = st.dataframe(
            filtered_df.loc[:, ["link", "country", "sector", "industry", "publication date", "pages PDF", "auditor"]],
            column_config={
                "link": st.column_config.LinkColumn(
                    label="Company",
                    width="medium",
                    display_text="^https://.*#name=(.*)$"
                ),
                "country": st.column_config.Column(label="Country"),
                "sector": st.column_config.Column(width="medium", label="Sector"),
                "industry": st.column_config.Column(width="medium", label="Industry"),
                "publication date": st.column_config.DateColumn(
                    format="DD.MM.YYYY", width="small", label="Published"
                ),
                "pages PDF": st.column_config.TextColumn(
                    help="Number of pages of the sustainability statement.",
                    label="Pages"
                ),
                "auditor": st.column_config.TextColumn(label="Auditor"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            # height=35 * len(filtered_df) + 38,
        )

        query_companies = table.selection.rows
        query_companies_df = filtered_df.iloc[query_companies, :]["company"].tolist()


    st.markdown("### Search Engine")

    with st.popover(
        "Select companies from the table by selecting the box to the left of the name to start searching." if query_companies == [] else f"Search in the reports of {len(query_companies)} companies" if len(query_companies) > 1 else "Search in the report of one company",
        disabled=query_companies == [], 
        use_container_width=True,
        icon="🔍"
        ):
        
        prompt = st.chat_input("Do the firms have a Paris-aligned decarbonization plan?")

        if prompt:
            data = {
                "query": prompt,
                "year": 2024,
            }
            
            with st.spinner("Analyzing the PDFs", show_time=True):
                response = requests.post(
                    "https://sunhat-api.onrender.com/sustainability-reports/query", 
                    headers={"Content-Type": "application/json"},
                    json=data, 
                    )
                
            reports_queried = {}
            # Aggregate responses by report
            for r in response.json():
                if r["reportId"] not in reports_queried.keys():
                    reports_queried[r["reportId"]] = [r]
                else:
                    reports_queried[r["reportId"]].append(r)
            
            # Display the results per report
            for report, chunks in reports_queried.items():
                report_metadata = requests.get(
                    f"https://sunhat-api.onrender.com/sustainability-reports/reports/{report}"
                    ).json()
                    
                with st.expander(report_metadata['company']['name'], expanded=True):
                    col1f, col2f = st.columns([0.35, 0.65])
                    relevant_chunks = sorted(chunks, key=lambda x: x["score"], reverse=True) # use these for the annotations but feed all to GPT
                        
                    with col1f:
                        relevant_texts = "\n".join([f"Page {c['page']+1}: {c['text']}" for c in relevant_chunks])
                        # for chunk in relevant_chunks:
                        #     text = chunk["text"].replace("|", "").replace("-", "").replace(">", "")
                        #     page = f"**Page {chunk['page']+1}**"
                        #     st.markdown(f"{page}: {text}")
                        with st.chat_message("assistant"):
                            stream = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "You are an expert in gathering information from sustainability reports."},
                                    {"role": "user", "content": f"Answer diligently on this question {prompt} from the following chunks of the report:"},
                                    {"role": "user", "content": relevant_texts},
                                    {"role": "user", "content": f"Be concise and provide the most relevant information from the texts only. Do not use the internet or general knowledge."},
                                ],
                                stream=True
                                )
                            
                            gpt_response = st.write_stream(stream)

                            # for chunk in completion:
                            #     print(chunk.choices[0].delta)

                            st.markdown(f"[Full report]({report_metadata['link']})")
                    
                    with col2f:
                        annotations = [{
                            "page": c["page"]+1,
                            "x": c["x1"],
                            "y": c["y1"],
                            "height": c["y2"] - c["y1"],
                            "width": c["x2"] - c["x1"],
                            "color": "#4200ff"
                            } for c in relevant_chunks]
                        
                        with st.spinner("Downloading the PDF", show_time=True):
                            pdf_viewer(
                                input=download_pdf(report_metadata["link"]),
                                annotations=annotations,
                                height=800,
                                pages_to_render=[a["page"] for a in annotations],
                            )

        



    # ------------------------------------ HEATMAP ----------------------------------
    with tab2:
        col_tab2_left, col_tab2_right = st.columns([0.5, 0.5])

        with col_tab2_left:
            st.markdown("""##### Explanation \n\n This chart shows simple counts of how often a standard is referenced in the company's sustainability statement. To compute the count, we scan the pages of the sustainability statement and count the occurrences of the standard identifier (e.g., E1, E2, ..., G1).""")

            st.markdown("###### Scaling\n\n")
            st.checkbox(label="Scale the counts by the number of datapoints per standard from IG-3 (to control for longer standards)", key="scale_by_dp")
            scale_by_dp = st.session_state.get("scale_by_dp", False)

            st.markdown("###### Split view")
            split_view = st.radio(label="None", options=("by sector", "by country", "by auditor", "no split"), index=0, horizontal=True, label_visibility="collapsed")


        with col_tab2_right:
            filtered_melted_df = (
                filtered_df
                .loc[:, [
                    'company', "sector", "country", "auditor", "pages PDF", 
                    'e1', 'e2', "e3", "e4", "e5", "s1", "s2", "s3", "s4", "g1"
                    ]
                ]
                .melt(id_vars=["company", "sector", "country", "auditor", "pages PDF"], value_name="hits", var_name="standard")
                .merge(standard_info_mapper)
                .assign(
                    standard=lambda x: x['standard'].str.upper(),
                    hits=lambda x: x["hits"] / x["ig3_dp"] if scale_by_dp else x["hits"],  
                    )
                .sort_values("sector")
                .dropna()
            )

            if filtered_melted_df.empty:
                st.error(f"We have not analyzed this company yet but will do so very soon!", icon="🚨")

            else:
                plot_heatmap(filtered_melted_df, split_view)




# ------------------------------------ ERROR HANDLING ----------------------------------
except Exception as e:
    st.error('This is an error. We are working on a fix. In the meantime, check out our Google Sheet!', icon="🚨")
    print(e)