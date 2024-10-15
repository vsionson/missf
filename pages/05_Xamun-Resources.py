import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark import Session
from pathlib import Path
from configparser import ConfigParser
from datetime import date, timedelta


XAMUN_PROJS = [
    "Xamun",
    "Xamun Delivery",
    "Advance Energy",
    "Xamun Marketplace",
    "Xamun Solutions",
    "Steer Marketplace",
    "ePCSO",
    "AE Project 2 WebUI",
    "BPS",
]

XAMUN_CORE = [
    "Aevin Earl Molina",
    "Allen Christian Tubo",
    "Avik Das",
    "Cyrill Binaohan",
    "John Aldrich Callado",
    "Maricar Mara",
    "Sarah Jane Rosales",
    "Von Lou Velle Segocio",
]


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

    _df_employee_all = session.sql("select * from DB_MIS.PUBLIC.EMPLOYEE").to_pandas()
    _df_eod = session.sql("select * from DB_MIS.PUBLIC.EOD").to_pandas()

    session.close()

    # remove dummy records
    _df_employee_all = _df_employee_all.loc[(_df_employee_all["COMPANY"] != "DUMMY")]

    _df_employee_all = _df_employee_all.rename(
        columns={
            "EMPLOYEE": "Employee",
            "RESIGNED": "Resigned",
            "LASTDAY": "LastDay",
            "RANK": "Rank",
            "LEVEL": "Level",
            "START_DATE": "Start",
            "ACCOUNT": "Account",
            "GRP2": "GRP2",
            "COMPANY": "Company",
            "INCLUDE": "Include",
        }
    )
    _df_employee = _df_employee_all.loc[
        :, ["Employee", "Resigned", "LastDay", "Rank", "Level", "Start", "Account"]
    ]

    _df_employee = _df_employee_all.loc[
        (_df_employee_all["Include"] == 1), "Employee":"Account"
    ]
    _df_employee_all.drop(columns=["Include"], inplace=True)

    _df_eod = _df_eod.rename(
        columns={
            "EMPLOYEE": "EmployeeName",
            "DATE": "Date",
            "ACCOUNT": "Account",
            "HOURS": "Hours",
            "MINUTES": "Minutes",
        }
    )
    _df_eod["TotalHrs"] = _df_eod.apply(
        lambda x: ((x["Hours"] * 60) + x["Minutes"]) / 60, axis=1
    )
    _df_eod["Date"] = _df_eod["Date"].astype("datetime64[ns]")

    return _df_employee, _df_eod, _df_employee_all


@st.cache_data
def load_data2():
    # config = ConfigParser()
    # config.read("config.ini")
    # path_billing = config["billing"]["path"]
    path_billing = st.secrets.billing.path
    # path_eod = config["eod"]["path"]
    path_eod = st.secrets.eod.path
    file_name_billing = Path(path_billing) / "Billing v3.0.xlsx"
    file_name_eod = Path(path_eod) / "BAI EOD Log Report V2.xlsx"

    _df_eod = pd.read_excel(
        file_name_eod,
        usecols=["EmployeeName", "Date", "Account", "Hours", "Minutes"],
        dtype={"Date": "datetime64[ns]"},
        engine="openpyxl",
    )
    _df_eod["TotalHrs"] = _df_eod.apply(
        lambda x: ((x["Hours"] * 60) + x["Minutes"]) / 60, axis=1
    )

    # FTEs
    # _df_emp = pd.read_excel(
    #     file_name_billing,
    #     usecols=[
    #         "Employee",
    #         "GRP",
    #         "Resigned",
    #         "LastDay",
    #         "Rank",
    #         "Level",
    #         "Start",
    #         "Account",
    #         "Include",
    #     ],
    #     sheet_name="employees",
    # )
    # _df_emp["temp"] = _df_emp["Resigned"].apply(lambda x: True if x == "X" else False)
    # _df_emp["Resigned"] = _df_emp["temp"]

    # _df_emp = _df_emp.loc[(_df_emp["Include"] == 1)]
    # _df_emp.drop(columns=["temp", "Include"], inplace=True)

    # all employees
    _df_emp_all = pd.read_excel(
        file_name_billing,
        sheet_name="employees",
        # usecols=[
        #     "Employee",
        #     "GRP",
        #     "Resigned",
        #     "LastDay",
        #     "Rank",
        #     "Level",
        #     "Start",
        #     "Account",
        #     "GRP2",
        #     "Company",
        #     "Include",
        #     "Remarks",
        #     "XamunBilledProj"
        # ],
    )
    # remove dummy records
    _df_emp_all = _df_emp_all.loc[(_df_emp_all["Company"] != "DUMMY")]

    # convert "X" to boolean True and blank to False
    _df_emp_all["temp"] = _df_emp_all["Resigned"].apply(
        lambda x: True if x == "X" else False
    )
    _df_emp_all["Resigned"] = _df_emp_all["temp"]
    _df_emp_all.drop(columns=["temp"], inplace=True)

    return _df_eod, _df_emp_all


def main():

    st.set_page_config(page_title="MIS Report", page_icon=":bar_chart:", layout="wide")

    st.title(":bar_chart: Xamun Resources")

    xamun_container = st.container()
    all_fte_container = st.container()
    all_emps_container = st.container()

    with xamun_container:

        _, _, col1, col2 = st.columns([0.25, 0.25, 0.25, 0.25])
        with col1:
            today = date.today()
            date1 = date(today.year, today.month, 1)
            date2 = date(today.year, today.month, 28) + timedelta(days=4)
            date2 = date2 - timedelta(days=date2.day)
            date_start = st.date_input("Starting Date", date1)
        with col2:
            date_end = st.date_input("Ending Date", date2)
        st.divider()

        date_start = date_start.strftime("%Y%m%d")
        date_end = date_end.strftime("%Y%m%d")

        if st.secrets.datasource.source == 2:
            df_eod, df_emp_all = load_data2()
            df_emp = df_emp_all.loc[(df_emp_all["Include"] == 1), "Employee":"Account"]
        else:
            df_emp, df_eod, df_emp_all = load_data()

        # change SwiftLoan into Xamun Solutions
        df_eod.loc[(df_eod["Account"] == "SwiftLoan"), "Account"] = "Xamun Solutions"

        # df_dd = df_emp.loc[(~df_emp["GRP"].str.upper().str.startswith("X"))]
        df_dd = df_emp.loc[(~df_emp["GRP"].str.startswith("X"))]

        # filter by date range and filter-out non Xamun accts
        df_eod_xamun_projs = df_eod.loc[
            (df_eod["Date"] >= date_start)
            & (df_eod["Date"] <= date_end)
            & (df_eod.Account.isin(XAMUN_PROJS))
            ]
        df_eod_xamun_projs_with_da = df_eod.loc[
            (df_eod["Date"] >= date_start)
            & (df_eod["Date"] <= date_end)
            & (df_eod.Account.isin(XAMUN_PROJS + ["Data Analytics"]))
            ]
        df_analytics = df_eod.loc[
            (df_eod.Date >= date_start)
            & (df_eod.Date <= date_end)
            & (df_eod.Account == "Data Analytics")
            ]

        interns = (
            df_eod_xamun_projs.loc[
                (
                    ~df_eod_xamun_projs["EmployeeName"].isin(df_emp["Employee"]),
                    "EmployeeName",
                )
            ]
            .unique()
            .tolist()
        )
        # interns

        # interns
        # _df = df_eod_xamun_projs.groupby(
        #     ["EmployeeName", "Account"], as_index=False
        # ).TotalHrs.sum()

        def get_type(row):
            if row.EmployeeName in (interns):
                return 1
            elif row.EmployeeName in (df_dd.Employee.to_list()):
                return 3
            else:
                return 2

        def get_type_name(value):
            if value == 1:
                return "Interns"
            elif value == 3:
                return "DD/QRI"
            else:
                return "Xamun"

        # chart 1: hrs
        col1, col2, col3 = st.columns([0.5, 0.25, 0.25])

        _df1 = df_eod_xamun_projs.groupby(
            ["EmployeeName"], as_index=False
        ).TotalHrs.sum()
        _df1["Type"] = _df1.apply(lambda x: get_type(x), axis="columns")

        with col1:

            # Total Hours

            _grp = df_eod_xamun_projs_with_da.groupby(["Account"], as_index=False)
            _df = _grp.TotalHrs.sum().sort_values(["Account"])

            fig = px.bar(
                _df,
                x="Account",
                y="TotalHrs",
                template="seaborn",
                title="Total Hours",
                # text_auto=True,
                text=["{:,.0f}".format(x) for x in _df["TotalHrs"]],
            )
            fig.update_yaxes(range=[0, 920], side="left")

            # highlight the target month (tick/x label)
            try:
                highlighted_bar = "Data Analytics"
                fig.update_traces(
                    marker_color=[
                        "blue" if x == highlighted_bar else "#99ccff"
                        for x in _df.Account
                    ],
                    textposition="outside",  # Position the text inside the bars
                )

                # Find the sales value for for the target month
                # highlighted_hrs = _df.loc[
                #     _df["Account"] == highlighted_bar, "TotalHrs"
                # ].values[0]
            except:
                print("Error")

            st.plotly_chart(fig, use_container_width=True, height=200)

        with col2:

            # Total Hrs By Type

            _df2 = _df1.groupby(["Type"], as_index=False).TotalHrs.sum()
            _df2["TypeName"] = _df2["Type"].apply(lambda x: get_type_name(x))

            fig = px.pie(
                _df2, values="TotalHrs", names="TypeName", title="Total Hrs By Type"
            )
            fig.update_traces(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # chart 2: head count
        with col3:

            # Head Count By Type

            # grp = df_eod_xamun_projs.groupby(["Account", "EmployeeName"], as_index=False)
            # _df = (
            #     grp.TotalHrs.count()
            #     .groupby(["Account"], as_index=False)
            #     .EmployeeName.count()
            #     .rename(columns={"EmployeeName": "Head Count"})
            # )

            # fig = px.bar(
            #     _df,
            #     "Account",
            #     "Head Count",
            #     template="plotly",
            #     title="Head Count",
            #     text=["{:,.0f}".format(x) for x in _df["Head Count"]],
            # )
            # # fig.update_layout(template=2)
            # st.plotly_chart(fig, use_container_width=True, height=200)

            _df2 = _df1.groupby(["Type"], as_index=False).EmployeeName.count()
            _df2["TypeName"] = _df2["Type"].apply(lambda x: get_type_name(x))

            fig = px.pie(
                _df2,
                values="EmployeeName",
                names="TypeName",
                title="Head Count By Type",
            )
            st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------
        st.divider()

        #####################################################################
        #
        #               Pie - Percentage Hours By Account
        #
        #####################################################################

        fig = px.pie(
            df_eod_xamun_projs,
            values="TotalHrs",
            names="Account",
            title="Percentage Hours By Account",
            height=600,
        )

        fig.update_traces(showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        st.divider()

        #####################################################################
        #
        #               XAMUN FTEs - not interns nor DD's
        #
        #####################################################################
        _df = df_eod_xamun_projs.loc[
            (~df_eod_xamun_projs.EmployeeName.isin(interns))
            & (~df_eod_xamun_projs.EmployeeName.isin(df_dd.Employee))
            ]
        _df = (
            _df.groupby(["Account", "EmployeeName"], as_index=False)
            .TotalHrs.sum()
            .sort_values("EmployeeName")
        )

        fig = px.bar(
            _df,
            x="EmployeeName",
            y="TotalHrs",
            color="Account",
            text_auto=True,
            title=f"Xamun FTEs ({_df.EmployeeName.nunique()})",
            hover_data=["Account", "TotalHrs"],
        )
        fig.update_traces(texttemplate="%{y:.2f}")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)

        #####################################################################
        #
        #               BORROWED FTEs - DD's
        #
        #####################################################################
        # _df = df_eod_xamun_projs.loc[
        #     # ~(df_eod_xamun_projs.EmployeeName.isin(interns))
        #     (df_eod_xamun_projs.EmployeeName.isin(df_dd.Employee))
        # ]
        _df = df_eod_xamun_projs.loc[
            (df_eod_xamun_projs.EmployeeName.isin(df_dd.Employee))
        ]
        _df = (
            _df.groupby(["Account", "EmployeeName"], as_index=False)
            .TotalHrs.sum()
            .sort_values("EmployeeName")
        )
        if len(_df) > 0:
            fig = px.bar(
                _df,
                x="EmployeeName",
                y="TotalHrs",
                color="Account",
                text_auto=True,
                title=f"'Borrowed' FTEs ({_df.EmployeeName.nunique()})",
                hover_data=["Account", "TotalHrs"],
            )
            fig.update_traces(texttemplate="%{y:.2f}")
            fig.update_xaxes(title_text="")
            st.plotly_chart(fig, use_container_width=True)

        #####################################################################
        #
        #               INTERNS
        #
        #####################################################################
        _df = df_eod_xamun_projs.loc[
            (df_eod_xamun_projs.EmployeeName.isin(interns))
        ].sort_values("EmployeeName")
        _df = _df.groupby(["Account", "EmployeeName"], as_index=False).TotalHrs.sum()
        fig = px.bar(
            _df,
            x="EmployeeName",
            y="TotalHrs",
            color="Account",
            text_auto=True,
            title=f"Interns ({_df.EmployeeName.nunique()})",
            hover_data=["Account", "TotalHrs"],
        )
        fig.update_traces(texttemplate="%{y:.2f}", opacity=0.95)
        fig.update_xaxes(title_text="")
        fig.update_layout(barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

        #####################################################################
        #
        #               ALL
        #
        #####################################################################
        _df = (
            df_eod_xamun_projs.groupby(
                ["Account", "EmployeeName"], as_index=False
            ).TotalHrs.sum()
        ).sort_values("EmployeeName")

        fig = px.bar(
            _df,
            x="EmployeeName",
            y="TotalHrs",
            color="Account",
            text_auto=True,
            title=f"All ({_df.EmployeeName.nunique()})",
            hover_data=["Account", "TotalHrs"],
        )
        fig.update_traces(texttemplate="%{y:.2f}")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)
        #####################################################################
        #
        #               Xamun Core
        #
        #####################################################################
        _df = df_eod_xamun_projs.loc[
            (~df_eod_xamun_projs.EmployeeName.isin(interns))
            & (~df_eod_xamun_projs.EmployeeName.isin(df_dd.Employee))
            & (df_eod_xamun_projs["Account"] == "Xamun")
            & (df_eod_xamun_projs["EmployeeName"].isin(XAMUN_CORE))
            ]
        _df = (
            _df.groupby(["EmployeeName"], as_index=False)
            .TotalHrs.sum()
            .sort_values("EmployeeName")
        )

        total_hrs = "{0:,.2f}".format(_df.TotalHrs.sum())

        fig = px.bar(
            _df,
            x="EmployeeName",
            y="TotalHrs",
            text_auto=True,
            title=f"Xamun Core/Solutions ({_df.EmployeeName.nunique()} FTEs; {total_hrs} hrs)",
            hover_data=["TotalHrs"],
            # template="ggplot2",
        )
        fig.update_traces(texttemplate="%{y:.2f}")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)
        #####################################################################
        #
        #               Xamun Core Support
        #
        #####################################################################
        _df = df_eod_xamun_projs.loc[
            (~df_eod_xamun_projs.EmployeeName.isin(interns))
            & (~df_eod_xamun_projs.EmployeeName.isin(df_dd.Employee))
            & (df_eod_xamun_projs["Account"] == "Xamun")
            & (~df_eod_xamun_projs["EmployeeName"].isin(XAMUN_CORE))
            ]
        _df = (
            _df.groupby(["EmployeeName"], as_index=False)
            .TotalHrs.sum()
            .sort_values("EmployeeName")
        )

        total_hrs = "{0:,.2f}".format(_df.TotalHrs.sum())

        fig = px.bar(
            _df,
            x="EmployeeName",
            y="TotalHrs",
            text_auto=True,
            title=f"Xamun Core Support({_df.EmployeeName.nunique()} FTEs; {total_hrs} hrs)",
            hover_data=["TotalHrs"],
            template="seaborn",
        )
        fig.update_traces(texttemplate="%{y:.2f}")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)

        #####################################################################
        #
        #               Analytics
        #
        #####################################################################

        # _df = (
        #     df_analytics.groupby(
        #         ["Account", "EmployeeName"], as_index=False
        #     ).TotalHrs.sum()
        # ).sort_values("EmployeeName")

        # total_hrs = "{0:.2f}".format(_df.TotalHrs.sum())
        # st.write(total_hrs)
        # fig = px.bar(
        #     _df,
        #     x="EmployeeName",
        #     y="TotalHrs",
        #     color="Account",
        #     text_auto=True,
        #     title=f"Data Analytics ({_df.EmployeeName.nunique()} FTEs; {total_hrs} hrs)",
        #     hover_data=["Account", "TotalHrs"],
        #     template="ggplot2",
        # )
        # fig.update_traces(texttemplate="%{y:.2f}")
        # fig.update_xaxes(title_text="")
        # st.plotly_chart(fig, use_container_width=True)

        ################################################################
        if st.toggle("Show FTEs based on EOD?"):
            arr = []
            st.header("Based on EOD")
            df = (
                df_eod_xamun_projs.groupby(["EmployeeName", "Account"], as_index=False)
                .TotalHrs.sum()
                .pivot(index="EmployeeName", columns="Account", values="TotalHrs")
                .fillna("")
                .reset_index()
            )
            df.index = range(1, len(df) + 1)

            st.subheader("All")
            dfx = df.style.format(precision=2)
            st.dataframe(
                dfx,
                use_container_width=True,
                hide_index=False,
            )
            # fig = px.bar(df, x="EmployeeName", y="TotalHrs")
            # st.plotly_chart(fig, use_container_width=True, height=200)

            st.subheader("Interns")
            df1 = df.loc[df.EmployeeName.isin(interns)]
            df1.index = range(1, len(df1) + 1)
            # df1 = df1.reset_index(drop=True).style.format(precision=2)
            df1 = df1.style.format(precision=2)

            st.dataframe(
                df1,
                use_container_width=True,
                hide_index=False,
            )

            st.subheader("Xamun FTEs")
            df2 = (
                df.loc[
                    (~df.EmployeeName.isin(interns))
                    & (~df.EmployeeName.isin(df_dd.Employee))
                    ].reset_index(drop=True)
                # .style.format(precision=2)
            )
            df2.index = range(1, len(df2) + 1)
            df2 = df2.style.format(precision=2)
            st.dataframe(
                df2,
                use_container_width=True,
            )

            st.subheader("FTEs from DD/QRI")
            df2 = (
                df.loc[
                    (~df.EmployeeName.isin(interns))
                    & (df.EmployeeName.isin(df_dd.Employee))
                    ].reset_index(drop=True)
                # .style.format(precision=2)
            )
            df2.index = range(1, len(df2) + 1)
            df2 = df2.style.format(precision=2)
            st.dataframe(
                df2,
                use_container_width=True,
            )

            # if st.toggle("Save to disk"):
            #     fname = st.text_input("File Name", value="file.xlsx")
            #     if st.button("Save"):
            #         with pd.ExcelWriter(fname) as writer:
            #             df.to_excel(writer, index=False)
            #         st.write("Saved!")

        # if st.toggle("Show FTE Distribution?"):
        # st.table(grp.TotalHrs.sum())

        # assignments

        #####################################################################
        #
        #               FTE Distribution
        #
        #####################################################################

        core = [
            {"Employee": "Allen Christian Tubo", "Remarks": "Jr. Full Stack"},
            {"Employee": "Avik Das", "Remarks": "Sr. Full Stack"},
            {"Employee": "Cyrill Binaohan", "Remarks": "TL"},
            {"Employee": "John Aldrich Callado", "Remarks": "Sr. Flutter"},
            {"Employee": "Sarah Jane Rosales", "Remarks": "Tester"},
        ]

        core2 = [
            {"Employee": "Aevin Earl Molina", "Remarks": "Jr FrontEnd"},
            {"Employee": "Maricar Mara", "Remarks": "PM"},
            {"Employee": "Von Lou Velle Segocio", "Remarks": "Mid FrontEnd"},
        ]

        the_rest2 = [
            {
                "Employee": "Aleeza Mae Agulay",
                "Remarks": "Designer",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Steer2, Xamun Delivery Design, Atlas Home",
                "is_billed": False,
            },
            {
                "Employee": "Brain Tumibay",
                "Remarks": "Sr Web/Solution Architect",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, AE Phase 2",
                "is_billed": False,
            },
            {
                "Employee": "Dharyll Jan Calaliman",
                "Remarks": "Mobile Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS",
                "is_billed": False,
            },
            {
                "Employee": "Dino Angelo Reyes",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS",
                "is_billed": True,
            },
            {
                "Employee": "Dominic Glenn Zabala",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Eduard Hinunangan",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Eliseo Libarios",
                "Remarks": "Sr Full Stack",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Debugging/Optimization QR",
                "is_billed": False,
            },
            {
                "Employee": "Erskine Roy Bornillo",
                "Remarks": "Jr Backend",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Genevieve Raymundo",
                "Remarks": "BA",
                # "Group": "Xamun Delivery",
                "Billable Proj": "WinCredit, Atlas Home, Xamun Template",
                "is_billed": False,
            },
            {
                "Employee": "Glen Ebina",
                "Remarks": "UI/UX",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, WinCredit",
                "is_billed": False,
            },
            {
                "Employee": "Ira Louise David",
                "Remarks": "Jr Flutter",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS/Core Support",
                "is_billed": True,
            },
            {
                "Employee": "Ivan Joshua Merete",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS",
                "is_billed": True,
            },
            {
                "Employee": "Janicah Lorra Cequeña",
                "Remarks": "Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "WinCredit, Atlas Home, AE Phase 2, QRI",
                "is_billed": False,
            },
            {
                "Employee": "Jansen Neil Olay",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Jayson Echano",
                "Remarks": "Mobile Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, AE Phase 2",
                "is_billed": False,
            },
            {
                "Employee": "Jessica Joy Angeles",
                "Remarks": "Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS",
                "is_billed": False,
            },
            {
                "Employee": "Jomar Lagunsad",
                "Remarks": "PM",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Delivery PM",
                "is_billed": True,
            },
            {
                "Employee": "Jomari Munsayac",
                "Remarks": "Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Steer2, iScan",
                "is_billed": False,
            },
            {
                "Employee": "Joseph Artillaga",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Kevin Paul Merwa",
                "Remarks": "Jr Full Stack",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Krischell Villadulid",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Lauren James Leal",
                "Remarks": "Backend",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Ma. Ethel Yatar",
                "Remarks": "Sr Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Delivery, Kit Sumabat",
                "is_billed": False,
            },
            {
                "Employee": "Marc Alvin Villarin ",
                "Remarks": "Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, iScan",
                "is_billed": True,
            },
            {
                "Employee": "Mark Rayden Mirafuente",
                "Remarks": "Jr Frontend",
                # "Group": "Xamun Delivery",
                "Billable Proj": "TMG R&D",
                "is_billed": False,
            },
            {
                "Employee": "Michael Dizon",
                "Remarks": "BA",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Eon Pharma, Xamun Template",
                "is_billed": False,
            },
            {
                "Employee": "Noel Guevarra",
                "Remarks": "Mid Flutter",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, AE Phase 2",
                "is_billed": False,
            },
            {
                "Employee": "Raymund Galvez",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "TMG R&D",
                "is_billed": False,
            },
        ]

        #########################################################################
        #
        #                    CORE
        #
        #########################################################################
        st.header("Xamun Inc")

        df_xamun_core = (
            df_emp_all
            .loc[(df_emp_all.Resigned==False) & (df_emp_all.Company=="Xamun") & (df_emp_all.Account=="Xamun Core")
            , ["Employee", "Rank", "Level", "Remarks"]]
        )
        df_xamun_core.index = range(1, len(df_xamun_core)+1)

        df_xamun_solutions = (
            df_emp_all
            .loc[(df_emp_all.Resigned==False) & (df_emp_all.Company=="Xamun") & (df_emp_all.Account=="Xamun Solutions")
            , ["Employee", "Rank", "Level", "Remarks"]]
        )
        df_xamun_solutions.index = range(1, len(df_xamun_solutions)+1)

        # df_xamun_core.index += 1

        # fig = go.Figure(
        #     data=[
        #         go.Table(
        #             columnorder=[
        #                 1,
        #                 2,
        #                 3,
        #             ],
        #             columnwidth=[
        #                 1,
        #                 5,
        #                 5,
        #             ],
        #             header=dict(
        #                 values=[
        #                     ["<b>LINE #</b>"],
        #                     ["<b>Name</b>"],
        #                     ["<b>Remarks</b>"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill_color="royalblue",
        #                 # align=["left", "center"],
        #                 font=dict(color="white", size=16),
        #                 # height=35,
        #             ),
        #             cells=dict(
        #                 values=[
        #                     df_xamun_core.index,
        #                     df_xamun_core.Employee,
        #                     df_xamun_core.Remarks,
        #                 ],
        #                 line_color="darkslategray",
        #                 fill=dict(
        #                     color=[
        #                         "paleturquoise",
        #                         "white",
        #                     ]
        #                 ),
        #                 align=["center", "left", "center"],
        #                 # font_size=12,
        #                 font=dict(color="black", size=16),
        #                 height=30,
        #             ),
        #         )
        #     ]
        # )
        # fig.update_layout(height=400, title_text="Xamun Core")
        # st.plotly_chart(fig, use_container_width=True)  # , height=600)

        st.subheader(f"Xamun Core ({len(df_xamun_core)})")
        st.dataframe(
            df_xamun_core,
            use_container_width=True,
            width=1000,
            height=210,
            # hide_index=True,
            column_config={
                "Start": st.column_config.DatetimeColumn(
                    format="MM/DD/YY", width="small"
                ),
                "LastDay": st.column_config.DatetimeColumn(
                    format="MM/DD/YY", width="small"
                ),
            }
        )

        #########################################################################
        #
        #                    XAMUN SOLUTIONS
        #
        #########################################################################

        # df_xamun_core = pd.DataFrame(core2).sort_values(by="Employee").reset_index()
        # df_xamun_core.index += 1
        #
        # fig = go.Figure(
        #     data=[
        #         go.Table(
        #             columnorder=[
        #                 1,
        #                 2,
        #                 3,
        #             ],
        #             columnwidth=[
        #                 1,
        #                 5,
        #                 5,
        #             ],
        #             header=dict(
        #                 values=[
        #                     ["<b>LINE #</b>"],
        #                     ["<b>Name</b>"],
        #                     ["<b>Remarks</b>"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill_color="royalblue",
        #                 # align=["left", "center"],
        #                 font=dict(color="white", size=16),
        #                 # height=35,
        #             ),
        #             cells=dict(
        #                 values=[
        #                     df_xamun_core.index,
        #                     df_xamun_core.Employee,
        #                     df_xamun_core.Remarks,
        #                 ],
        #                 line_color="darkslategray",
        #                 fill=dict(
        #                     color=[
        #                         "paleturquoise",
        #                         "white",
        #                     ]
        #                 ),
        #                 align=["center", "left", "center"],
        #                 # font_size=12,
        #                 font=dict(color="black", size=16),
        #                 height=30,
        #             ),
        #         )
        #     ]
        # )
        # fig.update_layout(height=350, title_text="Xamun Solutions")
        # st.plotly_chart(fig, use_container_width=True)  # , height=600)


        st.subheader(f"Xamun Solutions ({len(df_xamun_solutions)})")
        st.dataframe(
            df_xamun_solutions,
            use_container_width=True,
            width=1000,
            height=143,
            # hide_index=True,
            column_config={
                "Start": st.column_config.DatetimeColumn(
                    format="MM/DD/YY", width="small"
                ),
                "LastDay": st.column_config.DatetimeColumn(
                    format="MM/DD/YY", width="small"
                ),
            }
        )

        _df_xamun_rest = pd.DataFrame(the_rest2)

        #########################################################################
        #
        #                    BILLED
        #
        #########################################################################
        st.divider()
        st.header("BAI - Xamun Delivery")

        df_xamun_billed = (
            df_emp_all
            .loc[(df_emp_all.Resigned == False) & (~df_emp_all.XamunBilledProj.isnull())
            , ["Employee", "Rank", "Level", "Remarks", "XamunBilledProj"]]
        )
        df_xamun_billed.index = range(1, len(df_xamun_billed)+1)

        st.subheader(f"Billable ({len(df_xamun_billed)})")
        st.dataframe(
            df_xamun_billed,
            use_container_width=True,
            width=1000,
            height=200,
            # hide_index=True,
            column_config={
                "Start": st.column_config.DatetimeColumn(
                    format="MM/DD/YY", width="small"
                ),
                "LastDay": st.column_config.DatetimeColumn(
                    format="MM/DD/YY", width="small"
                ),
            }
        )
        # st.header("Billable Xamun Projects")

        # is_sorted_by_grp = st.checkbox("Sort by Group?")

        # df_xamun_billed = (
        #     _df_xamun_rest.loc[(_df_xamun_rest["is_billed"] == True)]
        #     # .sort_values(by=["Group", "Employee"] if is_sorted_by_grp else ["Employee"])
        #     .sort_values(by=["Employee"]).reset_index()
        # )
        # df_xamun_billed.index += 1
        #
        # fig = go.Figure(
        #     data=[
        #         go.Table(
        #             columnorder=[1, 2, 3, 4],
        #             columnwidth=[1, 4, 4, 5],
        #             header=dict(
        #                 values=[
        #                     ["<b>LINE #</b>"],
        #                     ["<b>Name</b>"],
        #                     ["<b>Remarks</b>"],
        #                     # ["<b>Group</b>"],
        #                     ["<b>Billed Project</b>"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill_color="royalblue",
        #                 # align=["left", "center"],
        #                 font=dict(color="white", size=16),
        #                 # height=35,
        #             ),
        #             cells=dict(
        #                 values=[
        #                     df_xamun_billed.index,
        #                     df_xamun_billed.Employee,
        #                     df_xamun_billed.Remarks,
        #                     # df_xamun_billed["Group"],
        #                     df_xamun_billed["Billable Proj"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill=dict(
        #                     color=[
        #                         "paleturquoise",
        #                         "white",
        #                     ]
        #                 ),
        #                 align=["center", "left", "left", "left"],
        #                 # font_size=12,
        #                 font=dict(color="black", size=16),
        #                 height=30,
        #             ),
        #         )
        #     ]
        # )
        # fig.update_layout(height=400, title_text="Billable")
        # st.plotly_chart(fig, use_container_width=True)  # , height=600)

        #########################################################################
        #
        #                    BENCH
        #
        #########################################################################
        # st.header("Bench")

        # is_sorted_by_grp2 = st.checkbox("Sort by Group ?")

        df_xamun_bench = (
            df_emp_all
            .loc[(df_emp_all.Resigned==False) & (df_emp_all.XamunBilledProj.isnull()) &
                (df_emp_all.Account=="Xamun Delivery") & (df_emp_all.Include==1)
            , ["Employee", "Rank", "Level", "Remarks", "XamunActivities"]]
        )
        df_xamun_bench.index = range(1, len(df_xamun_bench)+1)

        st.subheader(f"Bench ({len(df_xamun_bench)})")
        st.dataframe(
            df_xamun_bench,
            use_container_width=True,
            width=1000,
            height=800,
        )


        # df_xamun_rest = (
        #     _df_xamun_rest.loc[(_df_xamun_rest["is_billed"] == False)]
        #     .sort_values(
        #         # by=["Group", "Employee"] if is_sorted_by_grp2 else ["Employee"]
        #         by=["Employee"]
        #     )
        #     .reset_index()
        # )
        # df_xamun_rest.index += 1
        # fig = go.Figure(
        #     data=[
        #         go.Table(
        #             columnorder=[1, 2, 3, 4],
        #             columnwidth=[1, 4, 4, 5],
        #             header=dict(
        #                 values=[
        #                     ["<b>LINE #</b>"],
        #                     ["<b>Name</b>"],
        #                     ["<b>Remarks</b>"],
        #                     # ["<b>Group</b>"],
        #                     ["<b>Activities/Tasks</b>"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill_color="royalblue",
        #                 # align=["left", "center"],
        #                 font=dict(color="white", size=16),
        #                 # height=35,
        #             ),
        #             cells=dict(
        #                 values=[
        #                     df_xamun_rest.index,
        #                     df_xamun_rest.Employee,
        #                     df_xamun_rest.Remarks,
        #                     # df_xamun_rest["Group"],
        #                     df_xamun_rest["Billable Proj"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill=dict(
        #                     color=[
        #                         "paleturquoise",
        #                         "white",
        #                     ]
        #                 ),
        #                 align=["center", "left", "left", "left"],
        #                 # font_size=12,
        #                 font=dict(color="black", size=16),
        #                 height=30,
        #             ),
        #         )
        #     ]
        # )
        # #
        # fig.update_layout(height=1100, title_text="Bench")
        # st.plotly_chart(fig, use_container_width=True)  # , height=600)
        #############################################

        st.divider()
        #########################################################################
        #
        #                    SUMMARY
        #
        #########################################################################

        df_summary = (
            df_emp_all
            .loc[(df_emp_all.Resigned == False)]
            .groupby(["Company"], as_index=False)
            .agg({"Employee": "count"})
        )
        # st.dataframe(df_summary
        #              , hide_index=True
        #              , column_config={"Employee": st.column_config.Column(label="Employee Count", width="medium")})

        fig = px.bar(
            df_summary.sort_values("Employee"),
            x="Company",
            y="Employee",
            text_auto=True,
            template="seaborn",
            opacity=0.89,
            title="By Company",
            height=300
        )
        # fig.update_traces(texttemplate="%{y:,.0f}")
        # fig.update_layout(bargap=0.2)
        fig.update_layout(bargap=0.2, xaxis_title="", yaxis_title="No. of employees"
                          , xaxis={"tickfont": {"size": 14}}
                          , yaxis={"tickfont": {"size": 14}}
                          )
        fig.update_traces(textposition="outside", textfont_size=14)
        fig.update_yaxes(range=[0, 90], side="left")
        st.plotly_chart(fig, use_container_width=False, height=400)

        df_summary = (
            df_emp_all
            .loc[(df_emp_all.Resigned == False)]
            .groupby(["GRP2"], as_index=False)
            .agg({"Employee": "count"})
        )
        df_summary = df_summary.rename(columns={"GRP2": "Department"})
        # st.dataframe(df_summary
        #              , hide_index=True
        #              , height=460
        #              , column_config={"Employee": st.column_config.Column(label="Employee Count", width="medium")
        #                               , "GRP2": st.column_config.Column(label="Department", width="medium")
        #                               })
        fig = px.bar(
            df_summary.sort_values("Employee"),
            x="Department",
            y="Employee",
            text_auto=True,
            template="plotly",
            opacity=0.89,
            title="By Department/Group",
            height=300
        )
        fig.update_layout(bargap=0.2, xaxis_title="", yaxis_title="No. of employees"
                          , xaxis=dict(tickfont=dict(size=14))
                          , yaxis=dict(tickfont=dict(size=14)))
        fig.update_traces(textposition="outside", textfont_size=14)
        fig.update_yaxes(range=[0, 65], side="left")
        st.plotly_chart(fig, use_container_width=True)

        if st.toggle("Show Employee List?",value=False):

            st.divider()

            with all_fte_container:
                st.header("All FTEs")
                is_active = st.checkbox("Active", value=True)
                is_resigned = st.checkbox("Resigned", value=False)

                df_emp_copy = df_emp.loc[
                    ((df_emp["Resigned"] != is_active) | (df_emp["Resigned"] == is_resigned))
                ]
                df_emp_copy["Account"] = df_emp_copy["Account"].fillna("nan")
                acct_list = df_emp_copy["Account"].unique().tolist()
                try:
                    acct_list.sort()
                except:
                    pass

                selected_accts = st.multiselect("Account", options=acct_list, default=acct_list)

                if is_active or is_resigned:
                    st.dataframe(
                        df_emp_copy.loc[(df_emp["Account"].isin(selected_accts))],
                        use_container_width=True,
                        width=900,
                        height=600,
                        hide_index=True,
                        column_config={
                            "Start": st.column_config.DatetimeColumn(
                                format="MM/DD/YY", width="small"
                            ),
                            "LastDay": st.column_config.DatetimeColumn(
                                format="MM/DD/YY", width="small"
                            ),

                        }
                    )
                    cnt: int = len(df_emp_copy.loc[(df_emp["Account"].isin(selected_accts))])
                    st.write(f"Count: {cnt}")
                else:
                    st.dataframe(None)

            with all_emps_container:
                st.header("All Employees")
                is_active2 = st.checkbox("Active", value=True, key=3)
                is_resigned2 = st.checkbox("Resigned", value=False, key=4)

                df_emp_all_copy = df_emp_all.loc[
                    (
                            (df_emp_all["Resigned"] != is_active2)
                            | (df_emp_all["Resigned"] == is_resigned2)
                    )
                , ["Employee", "Resigned", "LastDay", "Rank", "Level", "GRP", "Start", "Account", "GRP2", "Company", "Remarks"]]
                df_emp_all_copy["Account"] = df_emp_all_copy["Account"].fillna("nan")

                company_list = df_emp_all_copy["Company"].unique().tolist()
                try:
                    company_list.sort()
                except:
                    pass

                selected_companies = st.multiselect(
                    "Company", options=company_list, default=company_list
                )
                df_emp_all_copy = df_emp_all_copy.loc[
                    (df_emp_all_copy["Company"].isin(selected_companies))
                ]

                grp2_list = df_emp_all_copy["GRP2"].unique().tolist()
                try:
                    grp2_list.sort()
                except:
                    pass

                selected_grp2 = st.multiselect("GRP2", options=grp2_list, default=grp2_list)

                if is_active2 or is_resigned2:
                    st.dataframe(
                        df_emp_all_copy.loc[
                            (df_emp_all["Company"].isin(selected_companies))
                            & (df_emp_all["GRP2"].isin(selected_grp2))
                            ],
                        use_container_width=True,
                        width=1000,
                        height=600,
                        hide_index=True,
                        column_config={
                            "Start": st.column_config.DatetimeColumn(
                                format="MM/DD/YY", width="small"
                            ),
                            "LastDay": st.column_config.DatetimeColumn(
                                format="MM/DD/YY", width="small"
                            ),
                        }
                    )
                    cnt: int = len(
                        df_emp_all_copy.loc[
                            (df_emp_all["Company"].isin(selected_companies))
                            & (df_emp_all["GRP2"].isin(selected_grp2))
                            ]
                    )
                    st.write(f"Count: {cnt}")


                else:
                    st.dataframe(None)

    return None


# if __name__ == "__main__":
main()
