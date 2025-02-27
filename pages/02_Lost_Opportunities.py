import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from snowflake.snowpark import Session
from pathlib import Path
from configparser import ConfigParser
from datetime import date, timedelta


@st.cache_data
def load_data():
    connection_parameters = {
        "user": st.secrets.connections.snowflake.user,
        "password": st.secrets.connections.snowflake.password,
        "account": st.secrets.connections.snowflake.account,
        "role": st.secrets.connections.snowflake.role,
        "warehouse": st.secrets.connections.snowflake.warehouse,
        "database": st.secrets.connections.snowflake.database,
        "schema": st.secrets.connections.snowflake.schema,
    }
    session = Session.builder.configs(connection_parameters).create()

    _df_sales = session.sql("select * from DB_MIS.PUBLIC.SALES").to_pandas()

    session.close()

    _df_sales = _df_sales.loc[~_df_sales.PROJECT.isnull()]
    _df_sales = _df_sales.loc[
        ~_df_sales.PROJECT.isin(
            ["PlancareX", "RivingtonX", "iScanX", "RevivaX", "TempestX"]
        )
    ]
    return _df_sales


@st.cache_data
def load_data2():
    # config = ConfigParser()
    # config.read("config.ini")
    # file_name = Path(config["billing"]["path"]) / "Billing v3.0.xlsx"
    file_name = Path(st.secrets.billing.path) / "Billing v3.0.xlsx"
    # sales/rates
    cols = [
        "Employee",
        "Project",
        "InitRate",
        "FTE",
        "Rate",
        "Period",
        "Rank",
        "Level",
        "Target2",
        "Billed",
        "ind_eligibility",
    ]
    _df_sales = pd.read_excel(
        file_name,
        sheet_name="RateCard",
        skiprows=1,
        usecols=cols,
        engine="openpyxl",
    )
    _df_sales = _df_sales.loc[~_df_sales.Project.isnull()]
    _df_sales = _df_sales.loc[
        ~_df_sales.Project.isin(
            ["PlancareX", "RivingtonX", "iScanX", "RevivaX", "TempestX"]
        )
    ]
    _df_sales = _df_sales.rename(
        columns={
            "InitRate": "INIT_RATE",
            "Target2": "TARGET",
            "ind_eligibility": "INDIV_ELIGIBILITY",
            "Employee": "EMPLOYEE",
            "Project": "PROJECT",
            "Period": "PERIOD",
            "Rank": "RANK",
            "Level": "LEVEL",
            "Billed": "BILLED",
        }
    )
    return _df_sales


def main():

    st.set_page_config(page_title="MIS Report", page_icon=":bar_chart:", layout="wide")

    st.title(":bar_chart: Lost Opportunities")

    # config = ConfigParser()
    # config.read("config.ini")

    # if config["datasource"]["source"] == "2":
    if st.secrets.datasource.source == 2:
        df = load_data2()
    else:
        df = load_data()

    df = df.rename(
        columns={
            "EMPLOYEE": "Employee",
            "PROJECT": "Project",
            "INIT_RATE": "InitRate",
            "PERIOD": "Period",
            "RANK": "Rank",
            "LEVEL": "Level",
            "TARGET": "Target",
            "BILLED": "Billed",
            "INDIV_ELIGIBILITY": "ind_eligibility",
        }
    )

    date1 = date.today()
    date1 = date(date1.year, date1.month, 1) - timedelta(days=1)
    date1 = date(date1.year, date1.month, 1)
    date2 = date(date1.year, date1.month, 28) + timedelta(days=4)
    date2 = date2 - timedelta(days=date2.day)

    col1, col2, col3 = st.columns(3)
    with col1:
        date_start = st.date_input("Starting Date", date1)  # pd.Timestamp(2024, 6, 1)
        date_start = pd.to_datetime(date_start)
    with col2:
        date_end = st.date_input("Ending Date", date2)  #  pd.Timestamp(2024, 6, 30)
        date_end = pd.to_datetime(date_end)
    with col3:
        threshhold_applied = st.toggle("Apply threshhold?", True)

    df["Period"] = df["Period"].astype("datetime64[ns]")

    # filter out those not within specified date range
    df = df.loc[(df["Period"] >= date_start) & (df["Period"] <= date_end)]

    df["Shortfall"] = df.apply(
        lambda x: 0 if x["ind_eligibility"] == 1 else x["Target"] - x["Billed"], axis=1
    )
    df["ShortfallAmt"] = df.apply(
        lambda x: 0.0 if x["ind_eligibility"] == 1 else x["Shortfall"] * x["InitRate"],
        axis=1,
    )

    df = df.loc[~(df["Shortfall"]).isna() & (df["Shortfall"] > 0)]
    df_filt = df[
        (
                ((df["ind_eligibility"] == 0.0) & (threshhold_applied))
                | ((df["ind_eligibility"] != 1.0) & (~threshhold_applied))
        )
    ]

    fig = px.bar(
        df_filt.groupby(["Project"], as_index=False).ShortfallAmt.sum(),
        x="Project",
        y="ShortfallAmt",
        text="ShortfallAmt",
        title="Monthly Lost Opportunities",
    )
    fig.update_traces(texttemplate="%{y:,.2f}")
    st.plotly_chart(fig, use_container_width=True, height=200)

    amt = df_filt.ShortfallAmt.sum()
    st.write(f"Monthly lost opportunity is ${amt: ,.2f}".format(amt))

    if st.toggle("Show details?"):
        df_filt["Month"] = pd.to_datetime(df_filt.Period).dt.strftime("%Y-%m-%d")
        st.dataframe(
            df_filt.loc[
            :,
            [
                "Project",
                "Employee",
                "Rank",
                "Level",
                "Month",
                "Target",
                "Billed",
                "Shortfall",
                "ShortfallAmt",
                # "ind_eligibility",
            ],
            ].sort_values(["Project", "Employee"]),
            hide_index=True,
        )
        if st.toggle("See individual FTE?"):
            option = st.selectbox("FTE", np.sort(df_filt.Employee.unique()))
            st.write(option)
            if option != "":
                st.dataframe(
                    df.loc[
                        (
                                ((df["ind_eligibility"] == 0.0) & (with_threshhold))
                                | ((df["ind_eligibility"] != 1.0) & (~with_threshhold))
                        ),
                        [
                            "Project",
                            "Employee",
                            "Rank",
                            "Level",
                            "Period",
                            "Target",
                            "Billed",
                            "Shortfall",
                            "ShortfallAmt",
                            # "ind_eligibility",
                        ],
                    ].query("Employee ==@option"),
                    hide_index=True,
                )
                st.write("No. of times", len(df.query("Employee ==@option")))
            else:
                st.dataframe(df, hide_index=True)

    return None


# if __name__ == "__main__":
main()
