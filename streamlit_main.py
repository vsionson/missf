"""
streamlit_main.py
Azure Consumption
    sorted(Path("/Users/shaun/projects/mis/data").glob("*2024-*.xlsx"))
    /Users/shaun/projects/mis/data/Jan to Dec 2023.xlsx

01_Projected_Revenue.py
    /Users/shaun/Documents/Billing v3.0.xlsx   
        sheet_name="RateCard"
        sheet_name="Holidays"
    /Users/shaun/Documents/dropzone/BAI Collections as of date.xlsx
        sheet_name="Raw"

02_Lost_Opportunities.py
    /Users/shaun/Documents/Billing v3.0.xlsx   
        sheet_name="RateCard"

05_Xamun_Resources.py
    /Users/shaun/eod/BAI EOD Log Report V2.xlsx
    /Users/shaun/Documents/Billing v3.0.xlsx"
        sheet_name="employees"
        
"""

import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
import plotly.express as px
from pathlib import Path
from snowflake.snowpark import Session
import snowflake.snowpark as snowpark
from configparser import ConfigParser
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher


@st.cache_data
def sum_daily_subscription(df):
    return df.groupby(["USAGEDATE", "SUBSCRIPTION"], as_index=False).COST.sum()


@st.cache_data
def load_data():
    connection_parameters = {
        "user": st.secrets.connections.snowflake.user,
        "password": st.secrets.connections.snowflake.password,
        "account": st.secrets.connections.snowflake.account,
        "role": st.secrets.connections.snowflake.role,
        "warehouse": "BAI_WH",
        "database": st.secrets.connections.snowflake.database,
        "schema": st.secrets.connections.snowflake.schema,
    }
    session = Session.builder.configs(connection_parameters).create()
    df = session.sql("select * from AZURECONSUMPTION").to_pandas()
    session.close()
    return df


@st.cache_data
def load_data2():
    config = ConfigParser()
    config.read("config.ini")
    path = config["azure"]["path"]

    def load_monthly(file):
        _df = pd.read_excel(
            file,
            skiprows=2,
            usecols=["Category", "Subscription", "Cost", "UsageDate", "Resource Group"],
            engine="openpyxl",
            dtype={"Cost": "float16"},
        )

        # change 'QR Core Production'==>'Beta'; and 'QR Core POC'==>'Production'

        _df.loc[_df.Subscription == "QR Core Production", "Subscription"] = "Beta"
        _df.loc[_df.Subscription != "Beta", "Subscription"] = "Production"
        return _df

    arr = sorted(Path(path).glob("*2024-*.xlsx"))
    arr_df = [load_monthly(el) for el in arr]

    file_name = Path(path) / "Azure Usage Jan to Dec 2023.xlsx"

    df_since_2023 = pd.read_excel(
        file_name,
        skiprows=2,
        usecols=["Category", "Subscription", "Cost", "UsageDate", "Resource Group"],
        engine="openpyxl",
        dtype={"Cost": "float16"},
    )

    # change 'QR Core Production'==>'Production'; and 'QR Core POC'==>'Beta'
    df_since_2023.loc[
        df_since_2023.Subscription == "QR Core Production", "Subscription"
    ] = "Production"
    df_since_2023.loc[df_since_2023.Subscription != "Production", "Subscription"] = (
        "Beta"
    )

    arr_df.append(df_since_2023)  ## add 2023

    _df = pd.concat(arr_df)
    _df["Category"] = _df["Category"].astype("category")
    _df = _df.rename(
        columns={
            "Category": "CATEGORY",
            "Subscription": "SUBSCRIPTION",
            "Cost": "COST",
            "UsageDate": "USAGEDATE",
            "Resource Group": "RESOURCEGROUP",
        }
    )
    return _df


def remaining_days_of_the_month(ts):
    today = ts.date()
    next_month = date(today.year, today.month, 28) + timedelta(days=4)
    return (next_month - timedelta(days=next_month.day) - today).days


def plot_the_chart_combined(df):
    _df = sum_daily_subscription(df)

    title = _df.USAGEDATE[0].strftime("%B")

    fig = px.line(
        _df,
        x="USAGEDATE",
        y="COST",
        color="SUBSCRIPTION",
        template="plotly_dark",
        title=title + " Total Cost per Day per Subscription",
        text=["${:,.2f}".format(x) for x in _df["COST"]],
    )
    fig.update_traces(textposition="top right")

    st.plotly_chart(fig, use_container_width=True, height=100)
    return None


def chart_daily_total_cost(df):
    dt1 = df.USAGEDATE.min()
    dt2 = df.USAGEDATE.max()

    day1 = dt1.day
    mon1 = dt1.month
    yr1 = dt1.year

    day2 = dt2.day
    mon2 = dt2.month
    yr2 = dt2.year

    start_date = st.slider(
        "Starting Date",
        value=datetime(yr1, mon1, day1),
        format="MM/DD/YYYY",
        min_value=datetime(yr1, mon1, day1),
        max_value=datetime(yr2, mon2, day2),
    )

    df_sliding = df.loc[df.USAGEDATE >= start_date]

    fig = px.line(
        df_sliding.groupby(["USAGEDATE"], as_index=False).COST.sum(),
        x="USAGEDATE",
        y="COST",
        template="seaborn",
        title="Daily Total Cost",
    )
    fig.update_traces(textposition="top center")

    st.plotly_chart(fig, use_container_width=True, height=200)

    return None


def chart_top_consumers(type, df, arr_dates):
    st.header(type)

    cols = st.columns(4)

    for i in range(0, 4):
        with cols[i]:

            _df = df.loc[(df.REPORTDATE == arr_dates[3 - i])].reset_index()

            st.subheader(_df.USAGEDATE[0].strftime("%B"))

            _df2 = (
                _df.query(f"SUBSCRIPTION == '{type}'")
                .groupby("CATEGORY", as_index=False)
                .COST.sum()
                .sort_values("COST", ascending=False)
            )
            _df2.style.format(precision=2)
            text = ["{:,.2f}".format(x) for x in _df2.head(6)["COST"]]
            fig = px.bar(
                _df2.head(6),
                x="CATEGORY",
                y="COST",
                opacity=0.8,
                template="gridon",
                text=text,
            )
            fig.update_traces(
                width=0.7,
                textposition="outside",
            )
            fig.update_xaxes(title_text="")
            fig.update_yaxes(range=(0, 1100 if type == "Production" else 650))
            st.plotly_chart(fig, use_container_width=True)

    return None


# ----------------------------------------------------
#       main module
# ----------------------------------------------------


def main():

    def chart_beta_vs_prod(category):
        st.header(category)
        col1, col2 = st.columns(2)

        orientation = "v"
        x = "REPORTDATE"
        y = "COST"
        height = 800
        range_high = 1200

        def get_category_by_subscription(df, category, subscription):
            return (
                df.loc[(df.CATEGORY == category) & (df.SUBSCRIPTION == subscription)]
                .groupby(["CATEGORY", "REPORTDATE"], as_index=False)
                .COST.sum()
            )

        with col1:
            df = get_category_by_subscription(df_since_2023, category, "Beta")

            text = ["{:,.2f}".format(x) for x in df["COST"]]
            fig = px.bar(df, x=x, y=y, title="Beta", text=text, orientation=orientation)
            fig.update_yaxes(range=[0, 1300])
            fig.update_traces(textposition="outside")

            st.plotly_chart(fig, use_container_width=True, height=height)
        with col2:
            df = get_category_by_subscription(df_since_2023, category, "Production")

            text = ["{:,.2f}".format(x) for x in df["COST"]]
            fig = px.bar(
                df,
                x=x,
                y=y,
                title="Production",
                text=text,
                orientation=orientation,
            )
            fig.update_yaxes(range=[0, 1300])
            fig.update_traces(textposition="outside")

            st.plotly_chart(fig, use_container_width=True, height=height)
        return None

    st.set_page_config(page_title="MIS Report", page_icon=":bar_chart:", layout="wide")

    st.title("QuickReach Azure Consumption")

    df_since_2023 = load_data()

    df_since_2023["USAGEDATE"] = df_since_2023["USAGEDATE"].astype("datetime64[ns]")
    df_since_2023["REPORTDATE"] = df_since_2023["USAGEDATE"].dt.strftime("%Y-%m")

    arr_desc_report_dates = df_since_2023.sort_values(
        ["USAGEDATE"], ascending=False
    ).REPORTDATE.unique()

    lst = df_since_2023["RESOURCEGROUP"].unique().tolist()
    if lst[-1] is None:
        lst.pop()

    azure_container = st.container()
    with azure_container:
        ##########################################
        #
        #   filter out unwanted Resource Groups
        #
        ##########################################
        selected = st.sidebar.multiselect(
            label="Resource Groups",
            options=lst,  # default=lst
        )

        if len(selected) > 0:  # filter out unwanted resource groups
            df_since_2023 = df_since_2023.loc[
                df_since_2023["RESOURCEGROUP"].isin(selected)
            ]

        # ---------------------------------------------
        #
        #              chart - monthly cost
        #
        # ---------------------------------------------

        fig = px.histogram(
            df_since_2023,
            x="REPORTDATE",
            y="COST",
            text_auto=True,
            template="seaborn",
            opacity=0.89,
            title="Monthly Cost",
        )
        fig.update_traces(texttemplate="%{y:,.0f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)

        # ---------------------------------------------
        #
        #              chart - Daily Total Cost
        #
        # ---------------------------------------------

        # chart_daily_total_cost(df_since_2023)
        dt1 = df_since_2023.USAGEDATE.min()
        dt2 = df_since_2023.USAGEDATE.max()

        day1 = dt1.day
        mon1 = dt1.month
        yr1 = dt1.year

        day2 = dt2.day
        mon2 = dt2.month
        yr2 = dt2.year

        start_date = st.slider(
            "Starting Date",
            value=datetime(yr1, mon1, day1),
            format="MM/DD/YYYY",
            # min_value=datetime(yr1, mon1, day1),
            # max_value=datetime(yr2, mon2, day2),
            min_value=dt1,
            max_value=dt2,
        )

        _df = df_since_2023.loc[df_since_2023.USAGEDATE >= start_date].sort_values(
            "USAGEDATE"
        )
        fig = px.line(
            _df.groupby(["USAGEDATE"], as_index=False).COST.sum(),
            x="USAGEDATE",
            y="COST",
            template="seaborn",
            title="Daily Total Cost",
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True, height=200)

        # ---------------------------------------------
        #
        #              chart - Month X Total Cost Per Day Per Beta/Production
        #
        # ---------------------------------------------
        # plot_the_chart_combined(
        #     df_since_2023.loc[
        #         (df_since_2023.REPORTDATE == arr_desc_report_dates[0])
        #     ].reset_index(),
        # )
        _df1 = df_since_2023.loc[
            (df_since_2023.REPORTDATE == arr_desc_report_dates[0])
        ].reset_index()
        _df2 = sum_daily_subscription(_df1)
        title = _df2.USAGEDATE[0].strftime("%B")

        fig = px.line(
            _df2,
            x="USAGEDATE",
            y="COST",
            color="SUBSCRIPTION",
            # row=1,
            # col=1,
            template="plotly_dark",
            title=title + " Total Cost per Day per Subscription",
            text=["${:,.2f}".format(x) for x in _df2["COST"]],
        )
        fig.update_traces(textposition="top right")

        st.plotly_chart(fig, use_container_width=True, height=100)

        if st.toggle("Show previous months?"):
            for i in range(1, 4):

                plot_the_chart_combined(
                    df_since_2023.loc[
                        (df_since_2023.REPORTDATE == arr_desc_report_dates[i])
                    ].reset_index(),
                )

        st.divider()

        # ----------------------------------------------------------------------
        if st.toggle("Daily Cost per Monthly Subscription"):
            ###########################################################
            #
            #           Daily Cost per Monthly Subscription
            #
            ###########################################################

            def get_subset(subscription, report_date):
                return df_since_2023.copy().loc[
                    # (df_since_2023.Subscription == subscription) &
                    (df_since_2023.REPORTDATE == report_date)
                ]

            # Option: Current Month or Including Previous Month
            subscription = st.radio(
                "Options",
                ["Specified Month", "Including previous months"],
            )

            arr = df_since_2023.REPORTDATE.sort_values(ascending=False).unique()

            if subscription == "Specified Month":
                report_date = st.selectbox(
                    "Month",
                    arr,
                )

                df = get_subset("subscription", report_date)
            else:
                mos = st.slider("No of months", 1, 12)
                df = df_since_2023.loc[df_since_2023.REPORTDATE.isin(arr[0:mos])]

            df_since_2023.REPORTDATE.sort_values(ascending=False).unique()

            sorter = (
                df.groupby(["CATEGORY"], as_index=False)
                .COST.sum()
                .sort_values("COST", ascending=False)["CATEGORY"]
                .to_list()
            )

            df.CATEGORY = df.CATEGORY.astype("category")
            df.CATEGORY = df.CATEGORY.cat.set_categories(sorter)

            df = (
                df.groupby(["SUBSCRIPTION", "CATEGORY", "USAGEDATE"], as_index=False)
                .COST.sum()
                .sort_values(["CATEGORY", "USAGEDATE"])
            )

            fig = px.line(
                df,
                x="USAGEDATE",
                y="COST",
                color="SUBSCRIPTION",
                facet_row="CATEGORY",
                height=6000,
                markers=True,
                # text=["${:,.2f}".format(x) for x in df["COST"]],
                template="plotly_dark",
            )
            fig.update_traces(textposition="top center")
            fig.update_yaxes(range=[0, 35], side="left")

            fig.for_each_xaxis(lambda x: x.update(showticklabels=True, matches=None))
            # fig.update_layout(legend_orientation="h", legend_title_side="top")
            st.plotly_chart(fig, use_container_width=True, height=6000)
            st.divider()

        # ----------------------------------------------------------------------
        if st.toggle("Average"):
            ###########################################################
            #
            #           Average Per Month
            #
            ###########################################################

            st.header("Average per Month")

            arr_arr = []
            for i in range(0, 4):
                arr_arr.append(
                    df_since_2023.loc[
                        (df_since_2023.REPORTDATE == arr_desc_report_dates[i])
                    ]
                )

            _df1 = pd.concat(arr_arr)

            _df2 = (
                _df1.groupby(
                    ["REPORTDATE", "USAGEDATE", "SUBSCRIPTION"], as_index=False
                )
                .COST.sum()
                .groupby(
                    [
                        "REPORTDATE",
                        # pd.Grouper(key="USAGEDATE", freq="1M"),
                        "SUBSCRIPTION",
                    ],
                    as_index=False,
                )
                .COST.mean()
            )

            _df3 = _df2.groupby(["REPORTDATE"], as_index=False).COST.sum()
            _df3["SUBSCRIPTION"] = "Total"

            _df2 = pd.concat([_df2, _df3])
            _df2.sort_values(["REPORTDATE"], inplace=True)

            fig = px.bar(
                _df2,
                x="REPORTDATE",
                y="COST",
                barmode="group",
                color="SUBSCRIPTION",
                text_auto=True,
                # text=["${:,.2f}".format(x) for x in _df2["COST"]],
            )
            fig.update_traces(texttemplate="%{y:$.2f}")
            fig.update_xaxes(
                ticktext=_df2.REPORTDATE.unique(), tickvals=_df2.REPORTDATE.unique()
            )

            st.plotly_chart(fig, use_container_width=True, height=200)

            # get the lastest total amount
            current_total = df_since_2023.groupby(
                pd.Grouper(key="USAGEDATE", freq="1M")
            ).sum()["COST"][-1]

            remaining_days = remaining_days_of_the_month(dt2)

            latest_total_ave = _df2["COST"].tolist()[-1]

            balance = remaining_days * latest_total_ave

            total_by_eom = balance + current_total

            # msg = f"With {remaining_days} remaining days till EOM and at ${latest_total_ave:.2f} ave by EOM the estimated total will be ${total_by_eom:.2f}"
            # f"Estimated by EOM ${total_by_eom:.2f}"

            st.write(f"Remaining days : {remaining_days}")
            st.write(f"Current total : ${current_total:,.2f}")
            st.write(f"By end of the month : ${total_by_eom:,.2f}")

            st.divider()
            ###########################################################
            #
            #           Moving Average
            #
            ###########################################################

            _df = df_since_2023.copy().groupby(["USAGEDATE"], as_index=False).COST.sum()
            _df["Avg"] = _df["COST"].rolling(window=7).mean()
            _df = _df.loc[(_df.USAGEDATE >= "2024-02-01")]

            fig = px.line(
                _df,
                x="USAGEDATE",
                y="Avg",
                # text=["{:,.2f}".format(x) for x in _df["Avg"]],
                template="seaborn",
                title="Moving Average (per 7 days)",
            )
            fig.update_traces(textposition="top center", orientation="h")

            st.plotly_chart(fig, use_container_width=True, height=200)

            st.divider()

        # ----------------------------------------------------------------------
        if st.toggle("Overall Cost since Jan 2023?"):
            # ---------------------------------------------
            #
            #    chart - overall cost per service since jan 2023
            #
            # ---------------------------------------------
            _df = df_since_2023.groupby(["CATEGORY"], as_index=False).COST.sum()

            fig = px.line(
                _df,
                x="CATEGORY",
                y="COST",
                text=["${:,.2f}".format(x) for x in _df["COST"]],
                template="seaborn",
                title="Overall Cost Per Service since Jan 2023",
            )
            fig.update_traces(textposition="top center")

            st.plotly_chart(fig, use_container_width=True, height=200)

        # ----------------------------------------------------------------------
        if st.toggle("Top 6"):
            st.header("Top 6 consumers")
            ###########################################################
            #
            #           Top 6 consumers
            #
            ###########################################################

            # top 6 consumers
            chart_top_consumers("Beta", df_since_2023, arr_desc_report_dates)
            chart_top_consumers("Production", df_since_2023, arr_desc_report_dates)

            st.divider()

        # ----------------------------------------------------------------------
        if st.toggle("Compare Services per Month"):
            ###########################################################
            #
            #           Compare Services per Month
            #
            ###########################################################
            chart_beta_vs_prod("Virtual Machines")
            chart_beta_vs_prod("SQL Database")
            chart_beta_vs_prod("Log Analytics")
            chart_beta_vs_prod("Azure Cosmos DB")
            chart_beta_vs_prod("Storage")
            chart_beta_vs_prod("Azure Database for MySQL")
            chart_beta_vs_prod("SignalR")

            st.divider()

        # ----------------------------------------------------------------------
        if st.toggle("Show Resource Groups?"):
            ###########################################################
            #
            #           Show All Resource Groups
            #
            ###########################################################

            period = st.text_input("Period (YYYY-MM)")

            _df = df_since_2023.loc[
                # (df_since_2023.REPORTDATE == arr_desc_report_dates[0])
                (df_since_2023.REPORTDATE == period)
            ].reset_index()

            df = (
                _df.groupby(["RESOURCEGROUP"], as_index=False)
                .COST.sum()
                .sort_values("COST", ascending=False)
            )
            fig = px.histogram(
                df.sort_values("COST", ascending=False),
                x="RESOURCEGROUP",
                y="COST",
                # color="RESOURCEGROUP",
                title="Resource Groups",
                template="seaborn",
                text_auto=True,
            )
            fig.update_traces(texttemplate="%{y:.1f}")
            st.plotly_chart(fig, use_container_width=True, height=200)

            ###########################################################
            #
            #           Show Individual Resource Groups
            #
            ###########################################################
            lst2 = df["RESOURCEGROUP"].unique()
            for rg in lst2:
                fig = px.histogram(
                    _df.query("`RESOURCEGROUP` == @rg"),
                    x="USAGEDATE",
                    y="COST",
                    color="CATEGORY",
                    title=rg,
                )
                fig.update_layout(bargap=0.1)
                st.plotly_chart(fig, use_container_width=True, height=200)
                st.dataframe(
                    df.loc[df["RESOURCEGROUP"] == rg, ["RESOURCEGROUP", "COST"]],
                    hide_index=True,
                )

            st.header("Resource Group Summary")
            fig = px.histogram(
                _df,
                x="CATEGORY",
                y="COST",
                color="RESOURCEGROUP",
                title="Per Service",
                height=600,
            )
            fig.update_yaxes(range=[0, 1400])
            st.plotly_chart(fig, use_container_width=True, height=600)

    return None


if __name__ == "__main__":
    main()
