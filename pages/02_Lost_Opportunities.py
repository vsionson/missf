import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from snowflake.snowpark import Session

st.title("Lost Opportunities")


@st.cache_data
def load_data():
    connection_parameters = {
        "user": st.secrets.connections.snowflake.user,
        "password": st.secrets.connections.snowflake.password,
        "account": st.secrets.connections.snowflake.account,
        "role": st.secrets.connections.snowflake.role,
        "warehouse": "WH_MIS",
        "database": st.secrets.connections.snowflake.database,
        "schema": st.secrets.connections.snowflake.schema,
    }
    session = Session.builder.configs(connection_parameters).create()

    _df_sales = session.sql("select * from DB_MIS.SALES.SALES").to_pandas()

    session.close()

    _df_sales = _df_sales.loc[~_df_sales.PROJECT.isnull()]
    _df_sales = _df_sales.loc[
        ~_df_sales.PROJECT.isin(["PlancareX", "RivingtonX", "iScanX", "RevivaX"])
    ]
    return _df_sales


def main():
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

    df["Month"] = pd.to_datetime(df["Period"], format="%Y-%m-%d")
    # df["Month"] = df["Month"].dt.strftime("%B %Y")

    col1, col2, col3 = st.columns(3)
    with col1:
        date_start = st.date_input("Starting Date", pd.Timestamp(2024, 4, 1))
    with col2:
        date_end = st.date_input("Ending Date", pd.Timestamp(2024, 4, 30))
    with col3:
        if st.toggle("With threshhold?", True):
            df = df.loc[(df["ind_eligibility"] == 0.0)]
        else:
            df = df.loc[(df["ind_eligibility"] != 1.0)]

    date_start = date_start.strftime("%Y%m%d")
    date_end = date_end.strftime("%Y%m%d")

    df = df.loc[(df["Month"] >= date_start) & (df["Month"] <= date_end)]

    df["Shortfall"] = df.apply(
        lambda x: 0 if x["ind_eligibility"] == 1 else x["Target"] - x["Billed"], axis=1
    )
    df["ShortfallAmt"] = df.apply(
        lambda x: 0.0 if x["ind_eligibility"] == 1 else x["Shortfall"] * x["InitRate"],
        axis=1,
    )

    fig = px.bar(
        df.groupby(["Project"], as_index=False).ShortfallAmt.sum(),
        x="Project",
        y="ShortfallAmt",
        text="ShortfallAmt",
        title="Monthly Lost Opportunities",
    )
    fig.update_traces(texttemplate="%{y:,.2f}")
    st.plotly_chart(fig, use_container_width=True, height=200)

    amt = df.ShortfallAmt.sum()
    st.write(f"Monthly lost opportunity is ${amt: ,.2f}".format(amt))

    if st.toggle("Show details?"):
        df["Month"] = pd.to_datetime(df.Month).dt.strftime("%Y-%m-%d")
        st.dataframe(
            df.loc[
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
                    "ind_eligibility",
                ],
            ].sort_values(["Project", "Employee"]),
            hide_index=True,
        )
        if st.toggle("See individual FTE?"):
            option = st.selectbox("FTE", np.sort(df.Employee.unique()))
            st.write(option)
            if option != "":
                st.dataframe(
                    df.loc[
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
                            "ind_eligibility",
                        ],
                    ].query("Employee ==@option"),
                    hide_index=True,
                )
                st.write("No. of times", len(df.query("Employee ==@option")))
            else:
                st.dataframe(df, hide_index=True)

    return None


if __name__ == "__main__":
    main()
