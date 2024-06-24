import pandas as pd
import streamlit as st
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark import Session
from configparser import ConfigParser
from pathlib import Path

st.set_page_config(page_title="MIS Report", page_icon=":bar_chart:", layout="wide")

st.title(":bar_chart: MIS Report")


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

    _df_sales = session.sql("select * from DB_MIS.SALES.SALES").to_pandas()
    _df_holiday = session.sql("select * from DB_MIS.SALES.HOLIDAY").to_pandas()
    _df_invoice = session.sql(
        "select INV_AMOUNT,PAYMENT_AMOUNT,TX_TYPE,INV_YR,INV_MON,PAYMENT_YR,PAYMENT_MON from DB_MIS.SALES.INVOICE"
    ).to_pandas()

    session.close()

    _df_sales["PERIOD"] = _df_sales["PERIOD"].astype("datetime64[ns]")
    _df_holiday["HOLIDAY"] = _df_holiday["HOLIDAY"].astype("datetime64[ns]")

    _df_sales = _df_sales.loc[~_df_sales.PROJECT.isnull()]
    _df_sales = _df_sales.loc[
        ~_df_sales.PROJECT.isin(
            ["PlancareX", "RivingtonX", "iScanX", "RevivaX", "TempestX"]
        )
    ]
    return _df_sales, _df_holiday, _df_invoice


@st.cache_data
def load_data2():
    config = ConfigParser()
    config.read("config.ini")
    path = config["billing"]["path"]
    file_name_billing = Path(path) / "Billing v3.0.xlsx"
    file_name_invoice = Path(path) / "BAI Collections as of date.xlsx"

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
        file_name_billing,
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

    # holiday
    _df_holiday = pd.read_excel(
        file_name_billing,
        sheet_name="Holidays",
        parse_dates=["Date"],
        date_format="%Y-%m-%d",
        usecols=["Date", "Holiday"],
        engine="openpyxl",
        # skiprows=1,
    )
    _df_holiday["HOLIDAY_NAME"] = _df_holiday["Holiday"]
    _df_holiday["HOLIDAY"] = pd.to_datetime(_df_holiday["Date"])
    # _df_holiday["YYYYMM"] = _df_holiday["Date"].dt.strftime("%Y-%m")
    # _df_holiday["Month"] = _df_holiday["Date"].dt.strftime("%B")

    # invoice
    _df_invoice = pd.read_excel(
        file_name_invoice,
        sheet_name="Raw",
    )
    _df_invoice = _df_invoice.drop(["CURRENCY", "STATUS"], axis=1)

    _df_invoice["INV_DATE"] = _df_invoice["INV_DATE"].astype("datetime64[ns]")
    _df_invoice["DATE_PAID"] = _df_invoice["DATE_PAID"].astype("datetime64[ns]")
    _df_invoice["INV_YR"] = _df_invoice.apply(lambda x: x["INV_DATE"].year, axis=1)
    _df_invoice["PAYMENT_YR"] = _df_invoice.apply(lambda x: x["DATE_PAID"].year, axis=1)
    # _df_invoice = _df_invoice.loc[:4]

    _df_invoice = _df_invoice.loc[
        (_df_invoice["INV_YR"] == 2024)
        & (_df_invoice["INV_AMOUNT"] != 33333.34)
        & (_df_invoice["INV_AMOUNT"] != 70901.49)
    ]
    return _df_sales, _df_holiday, _df_invoice


def format_number(num):
    limit_bil = 1000000000
    limit_mil = 1000000
    limit_thou = 1000

    if num / limit_bil >= 1:
        return f"{round(num / limit_bil,1)} B"
    if num / limit_mil >= 1:
        return f"{round(num / limit_mil,1)} M"
    if num / limit_thou > 1:
        return f"{round(num / limit_thou,1)} K"

    return num


def main_chart(df):
    fig = px.bar(
        df,
        "Month",
        "Billable",
        text=["${:,.2f}".format(x) for x in df["Billable"]],
        template="seaborn",
        title="Projected Revenue",
        opacity=0.7,
    )

    # highlight the target month (tick/x label)
    highlighted_bar = "June 2024"
    fig.update_traces(
        marker_color=["blue" if x == highlighted_bar else "#99ccff" for x in df.Month],
        textposition="inside",  # Position the text inside the bars
    )

    # Find the sales value for for the target month
    highlighted_bar_sales = df.loc[df["Month"] == highlighted_bar, "Billable"].values[0]

    # Add annotation for the highlighted bar
    fig.add_annotation(
        x=highlighted_bar,
        y=highlighted_bar_sales,  # Coordinates for the annotation
        text="Current Month",  # Text to display
        showarrow=True,  # Use arrow or not
        font=dict(size=10, color="Black"),  # Font settings
        bgcolor="White",  # Background color
        opacity=0.8,  # Opacity
    )
    # fig.update_layout(plot_bgcolor="grey")
    st.plotly_chart(fig, use_container_width=True, height=200)
    return None


def ftes(df_rates):
    df = df_rates.groupby(["PERIOD", "PROJECT"], as_index=False).FTE.sum()
    df = df.loc[df.PROJECT.isin(["AIFS", "Cirrus", "Rivington", "Tempest", "TIG"])]

    df2 = df.groupby("PERIOD", as_index=False).FTE.sum()
    df2["PROJECT"] = "Total"

    df = pd.concat([df, df2])

    fig = px.bar(
        df,
        x="PERIOD",
        y="FTE",
        color="PROJECT",
        text="FTE",
        title="FTEs",
        template="seaborn",
    )
    fig.update_traces(texttemplate="%{y:.1f}")
    fig.update_layout(legend_orientation="v")
    fig.update_yaxes(visible=False)
    st.plotly_chart(fig, use_container_width=True, height=400)

    return None


def billable_hrs(df_rates):
    df = df_rates.groupby(["PERIOD", "PROJECT"], as_index=False).TARGET.max()
    df = df.loc[df.PROJECT.isin(["AIFS", "Cirrus", "Rivington", "Tempest", "TIG"])]
    df.loc[(df.PROJECT == "TIG"), "TARGET"] = 160

    fig = px.bar(
        df,
        x="PERIOD",
        y="TARGET",
        color="PROJECT",
        text="TARGET",
        title="Billable Hours",
        template="plotly_dark",
    )
    fig.update_traces(texttemplate="%{y:.0f}")
    fig.update_layout(legend_orientation="v")
    fig.update_yaxes(visible=False)
    st.plotly_chart(fig, use_container_width=True, height=200)

    return None


def okr(df):
    df_inv = df.groupby(["INV_YR", "INV_MON", "TX_TYPE"], as_index=False).agg(
        {"INV_AMOUNT": sum}
    )
    df_payment = df.groupby(
        ["PAYMENT_YR", "PAYMENT_MON", "TX_TYPE"], as_index=False
    ).agg({"PAYMENT_AMOUNT": sum})

    piv_inv = pd.pivot_table(
        data=df_inv, values="INV_AMOUNT", columns="TX_TYPE", index=["INV_MON"]
    )
    piv_payment = pd.pivot_table(
        data=df_payment,
        values="PAYMENT_AMOUNT",
        columns="TX_TYPE",
        index=["PAYMENT_MON"],
    )
    df_conc = pd.concat([piv_inv, piv_payment], axis=1)
    df_conc.fillna(0, inplace=True)

    # df = df.loc[:4]
    no_of_rows_aka_columns = len(df_conc) + 2

    amts_array = [
        dict(
            mon=idx,
            dd_invoiced=dd_invoiced,
            xamun_invoiced=xamun_invoiced,
            fp_invoiced=fp_invoiced,
            dd_collected=dd_collected,
            xamun_collected=xamun_collected,
            fp_collected=fp_collected,
        )
        for idx, dd_invoiced, fp_invoiced, xamun_invoiced, dd_collected, fp_collected, xamun_collected in df_conc.itertuples(
            index=True
        )
    ]

    arr_months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    arr_columns = ["<b>" + arr_months[i] + "</b>" for i in range(0, len(df_conc))]
    arr_columns.insert(0, "")
    arr_columns.append("<b>To Date</b>")
    # arr_columns = [""]
    # for i in range(0, len(df_conc)):
    #     arr_columns.append("<b>" + arr_months[i] + "</b>")
    # arr_columns.append("<b>To Date</b>")

    # accumulate the totals
    dd_invoiced = 0
    dd_collected = 0
    xamun_invoiced = 0
    xamun_collected = 0
    fp_invoiced = 0
    fp_collected = 0

    for elem in amts_array:
        dd_invoiced += elem.get("dd_invoiced", 0)
        dd_collected += elem.get("dd_collected", 0)
        xamun_invoiced += elem.get("xamun_invoiced", 0)
        xamun_collected += elem.get("xamun_collected", 0)
        fp_invoiced += elem.get("fp_invoiced", 0)
        fp_collected += elem.get("fp_collected", 0)

    arr_totals = [
        "",
        "<b>${0:,.0f}</b>".format(dd_invoiced),
        "<b>${0:,.0f}</b>".format(dd_collected),
        "",
        "<b>₱{0:,.0f}</b>".format(xamun_invoiced),
        "<b>₱{0:,.0f}</b>".format(xamun_collected),
        "",
        "<b>₱{0:,.0f}</b>".format(fp_invoiced),
        "<b>₱{0:,.0f}</b>".format(fp_collected),
    ]

    def get_monthly(month):
        # one column of data (for the month)
        dict_month = amts_array[month]
        return [
            "",
            "${0:,.0f}".format(dict_month["dd_invoiced"]),
            "${0:,.0f}".format(dict_month["dd_collected"]),
            "",
            "₱{0:,.0f}".format(dict_month["xamun_invoiced"]),
            "₱{0:,.0f}".format(dict_month["xamun_collected"]),
            "",
            "₱{0:,.0f}".format(dict_month["fp_invoiced"]),
            "₱{0:,.0f}".format(dict_month["fp_collected"]),
        ]

    values = []
    # 1st append: the 1st column (row labels)
    values.append(
        [
            "<b>DD Revenues</b>",
            "Invoiced",
            "Collected",
            "<b>Xamun Revenues</b>",
            "Invoiced",
            "Collected",
            "<b>Other Revenues</b>",
            "Invoiced",
            "Collected",
        ]
    )
    # 1 column per month
    for i in range(0, len(df_conc)):
        values.append(get_monthly(i))

    # final column - the totals
    values.append(arr_totals)
    fig = go.Figure(
        data=[
            go.Table(
                # columnorder=arange(1, len(df)+2)
                columnorder=[i for i in range(1, no_of_rows_aka_columns + 1)],
                columnwidth=[5 for _ in range(1, no_of_rows_aka_columns + 1)],
                header=dict(
                    values=arr_columns,
                    line_color="darkslategray",
                    fill_color="royalblue",
                    # align=["left", "center"],
                    font=dict(color="white", size=16),
                    # height=35,
                ),
                cells=dict(
                    values=values,
                    line_color="darkslategray",
                    fill=dict(
                        color=[
                            "#FBE9E7",
                            "#E3F2FD",
                            "#E0E0E0",
                            "#E3F2FD",
                            "#E0E0E0",
                            "#E3F2FD",
                            "#E0E0E0",
                            "#E3F2FD",
                            "#CFD8DC",
                        ]
                    ),
                    align=["center", "right"],
                    # font_size=12,
                    font=dict(color="black", size=16),
                    height=30,
                ),
            )
        ]
    )
    st.header("Revenues and Collections")
    fig.update_layout(height=600, width=1200)
    st.plotly_chart(fig, use_container_width=True, height=600)

    df = pd.DataFrame(
        {
            "Type": ["DD", "Xamun", "FixedPrice"],
            "Revenue": [dd_invoiced * 58, xamun_invoiced, fp_invoiced],
        }
    )
    fig = px.pie(df, values="Revenue", names="Type", title="Invoiced To-date(Php)")
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True, height=600)
    return None


def main():
    def load_holidays():
        df_holiday["YYYYMM"] = df_holiday["HOLIDAY"].dt.strftime("%Y-%m")
        df_holiday["Month"] = df_holiday["HOLIDAY"].dt.strftime("%B")

        df_cur = df_holiday.loc[
            (df_holiday["HOLIDAY"].dt.year == 2024)
            & (df_holiday["HOLIDAY"].dt.month == 6)
        ]
        df_cur["HOLIDAY"] = df_holiday["HOLIDAY"].dt.strftime("%Y-%m-%d")

        col1, col2 = st.columns(2)
        with col1:
            st.header("Holidays in June")
            st.dataframe(df_cur[["HOLIDAY", "HOLIDAY_NAME"]], hide_index=True)
        with col2:
            st.header("Number of Holidays in 2024")
            df_yr = df_holiday.loc[df_holiday["HOLIDAY"].dt.year == 2024]

            df_yr2 = df_yr.groupby(["YYYYMM"], as_index=False).agg(
                Holidays=("YYYYMM", "count")
            )
            st.dataframe(df_yr2[["YYYYMM", "Holidays"]], hide_index=True)

        return None

    with st.container():
        _, _, col = st.columns(3)
        with col:
            date_start = st.date_input(
                "Starting Date", pd.Timestamp(2023, 10, 1)
            ).strftime("%Y%m%d")

        df_rates, df_holiday, df_invoice = load_data()

        df_rates = df_rates.query("PERIOD >= @date_start")
        df_rates["Billable"] = df_rates["TARGET"] * df_rates["INIT_RATE"]
        df_rates["LossHrs"] = df_rates["TARGET"] - df_rates["BILLED"]
        df_rates["LossAmt"] = df_rates["LossHrs"] * df_rates["INIT_RATE"]
        df_rates["Month"] = df_rates["PERIOD"].dt.strftime("%B %Y")  # .dt.month_name()

        df_rates_grouped = (
            df_rates.groupby(["PERIOD", "Month"], as_index=False).Billable.sum()
            # .query("Period >= @date_start")
        )

    main_chart(df_rates_grouped)
    ftes(df_rates)
    billable_hrs(df_rates)
    load_holidays()
    okr(df_invoice)

    return None


if __name__ == "__main__":
    main()
