import json
import os
import sys

import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
import openpyxl
from lib import common
from lib import evaldata_manager as edm
from pandas.api.types import is_numeric_dtype

# Key Prefix
KP = "eval_dashboard."


def get_fig(df, sequence, fn):
    fig = fn(
        df,
        title='-'.join(sequence),
        path=reversed(sequence)
    )
    fig.update_traces(textinfo="label+value+percent entry")
    return fig


def show_visual(df, title, df_records):
    def display_barplots(df, categories):
        fig = px.bar(df, x="model", y=categories, text_auto='.2s')
        st.plotly_chart(fig, theme="streamlit", use_container_width=True)

    def display_radarchats(df, categories):
        fig = go.Figure()
        rmax = 0
        for i, model in enumerate(df["model"].unique()):
            r = df[df["model"] == model][categories].values.tolist()[0]
            r.append(r[0])
            # print(model, r)
            if i == 0:
                rmax = max(r)
            else:
                rmax = min([rmax, max(r)])
            fig.add_trace(go.Scatterpolar(
                r=r,
                theta=categories + [categories[0]],
                fill=st.session_state[KP + "chart_fill"] if KP + "chart_fill" in st.session_state else "none",
                name=model
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, rmax]
                )),
            showlegend=True
        )

        st.plotly_chart(fig, theme=None, use_container_width=True)

    def create_queried_df(qdf, df, standard_cols, categories):
        mrecords = []
        for model in df["model"].unique():
            # Standard Cols
            # print("Run Time", model, df[df["model"] == model]["run_time"].values)
            mrecord = {"model": model, "run_spec": df["run_spec"].unique()[0],
                       "run_time": df[df["model"] == model]["run_time"].values[0]}
            mcols = list(qdf.columns)
            mqdf = qdf[qdf["model"] == model]
            # Categorical Columns
            for category in categories:
                field = category
                if field not in mcols:
                    field = category + "_" + model
                if is_numeric_dtype(mqdf[field]):
                    mrecord[category] = mqdf[mqdf[field] > 0][field].mean()
                else:
                    mrecord[category] = mqdf[field].iloc[0]
            mrecords.append(mrecord)
        mdf = pd.DataFrame(mrecords)
        mdf = mdf[list(df.columns)]
        return mdf

    def display_df(df, title):
        standard_cols = {"model", "run_spec", "run_time"}
        df_columns = set(df.columns)
        categories = list(df_columns - standard_cols)
        if KP + "query" + title in st.session_state and st.session_state[KP + "query" + title]:
            mdf = None
            if KP + "query.data" + title in st.session_state:
                mdf = create_queried_df(st.session_state[KP + "query.data" + title], df, standard_cols, categories)
            left, right = st.columns(2)
            with left:
                if len(categories) < 3:
                    st.markdown("### :blue[Original]")
                    display_barplots(df, categories)
                    if mdf is not None:
                        with right:
                            st.markdown("### :red[Queried]")
                            display_barplots(mdf, categories)
                else:
                    st.markdown("### :blue[Original]")
                    display_radarchats(df, categories)
                    if mdf is not None:
                        with right:
                            st.markdown("### :red[Queried]")
                            display_radarchats(mdf, categories)
            return mdf
        else:
            if len(categories) < 3:
                display_barplots(df, categories)
            else:
                display_radarchats(df, categories)
        return None

    def show_dataframe(df, mdf):
        with st.expander("See Data"):
            st.markdown("### :blue[Original]")
            st.dataframe(df, use_container_width=True)
            if mdf is not None:
                st.markdown("### :red[Queried]")
                st.dataframe(mdf, use_container_width=True)
            # st.data_editor(df, use_container_width=True, key=KP + 'data.' + title)

    def handle_query(df_records, title):
        if st.session_state[KP + "query" + title]:
            st.session_state[KP + "query.data" + title] = df_records.query(st.session_state[KP + "query" + title])
        else:
            del st.session_state[KP + "query.data" + title]

    def show_records_dataframe(df_records, title):
        if df_records is not None:
            with st.expander("See Records"):
                left, mid, right, moreright = st.columns([2, 1, 1, 1])
                right.link_button("Query Documentation",
                                  "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html")
                moreright.link_button("Another Doc", "https://note.nkmk.me/en/python-pandas-query/")
                left.text_input("Query", placeholder="Query", label_visibility="collapsed", key=KP + "query" + title,
                                on_change=handle_query, args=(df_records,title,))
                # print("Columns:", df_records.columns)
                st.info(' | '.join(list(df_records.columns)))
                df = df_records
                if KP + "query.data" + title in st.session_state:
                    df = st.session_state[KP + "query.data" + title]
                st.dataframe(df, use_container_width=True)

    st.markdown("## " + title)
    mdf = display_df(df, title)
    show_dataframe(df, mdf)
    show_records_dataframe(df_records, title)


def filter_df(df, ring, ring_select):
    return df.loc[df[ring].isin(ring_select)]


def show_selection(items, keytag, label):
    st.sidebar.markdown(
        f"""
                <style>
                    .stMultiSelect [data-baseweb=select] span {{
                        max-width: 1000px;
                        font-size: 0.9rem;
                    }}
                </style>""",
        unsafe_allow_html=True,
    )
    st.sidebar.multiselect("Select %s" % label, options=items, key=keytag, placeholder="Choose %s" % label)


def show_model_selection(models):
    show_selection(models, KP + "models", "Model")


def show_runspecs_selection(runspecs):
    show_selection(runspecs, KP + "runspecs", "Run Specs")
    if KP + "runspecs" in st.session_state and st.session_state[KP + "runspecs"]:
        st.sidebar.divider()
        st.sidebar.radio("Chart Fill", ["none", "toself", "tonext"], key=KP + "chart_fill", horizontal=True)


def load_config():
    def dump_session_state(msg):
        print("*" * 50, msg)
        for k in sorted(st.session_state):
            if k != "global.EMOJI_LIST":
                print(k, "==>", st.session_state[k])
        print("-" * 50)

    st.session_state[KP + "config_loaded"] = common.get_config_as_dict(st.session_state[KP + "config"])
    for section in st.session_state[KP + "config_loaded"]:
        for key in st.session_state[KP + "config_loaded"][section]:
            if section == "GLOBAL":
                st.session_state[KP + key] = st.session_state[KP + "config_loaded"][section][key]
            else:
                st.session_state[KP + section + '.' + key] = st.session_state[KP + "config_loaded"][section][key]
    # dump_session_state("Loading Config")


def eval_dashboard():
    load_config()
    st.markdown("# Evaluation")
    st.sidebar.button("Reload Cache", key=KP + "reload_cache", on_click=st.cache_resource.clear)
    st.sidebar.divider()
    models, runspecs = edm.get_model_runspec_map(st.session_state[KP + "data_dir"])
    show_model_selection(models)
    if KP + "models" in st.session_state and len(st.session_state[KP + "models"]) > 0:
        runspecs_set = set()
        for model in st.session_state[KP + "models"]:
            print(model, models[model])
            runspecs_set.update(models[model])
        runspecs_set = list(runspecs_set)
        # print("RunSpecs", runspecs)
        show_runspecs_selection(runspecs_set)
        # print("Runspecs:", st.session_state[KP + "runspecs"])

        # Create a df with all the data files
        df_map, record_data = edm.load_data_from_files(st.session_state[KP + "data_dir"], st.session_state[KP + "models"],
                                          st.session_state[KP + "runspecs"])
        edm.convert_runspec_to_df(df_map)
        df_records_map = edm.denormalize_records_data(record_data)
        edm.convert_runspec_to_df(df_records_map)

        for runspec in st.session_state[KP + "runspecs"]:
            if runspec in df_map:
                show_visual(df_map[runspec], runspec, df_records_map[runspec] if runspec in df_records_map else None)


if __name__ == "__main__":
    st.set_page_config(layout="wide")
    eval_dashboard()
