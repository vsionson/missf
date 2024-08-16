import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark import Session
from pathlib import Path
from configparser import ConfigParser
from check_pwd import check_password
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

    _df_employee = session.sql("select * from DB_MIS.PUBLIC.EMPLOYEE").to_pandas()

    _df_eod = session.sql("select * from DB_MIS.PUBLIC.EOD").to_pandas()

    session.close()

    _df_employee = _df_employee.rename(
        columns={
            "EMPLOYEE": "Employee",
            "RESIGNED": "Resigned",
            "LASTDAY": "LastDay",
            "RANK": "Rank",
            "LEVEL": "Level",
            "START_DATE": "StartDate",
            "ACCOUNT": "Account",
        }
    )
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

    return _df_employee, _df_eod


@st.cache_data
def load_data2():
    config = ConfigParser()
    config.read("config.ini")
    path_billing = config["billing"]["path"]
    path_eod = config["eod"]["path"]
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

    _df_emp = pd.read_excel(
        file_name_billing,
        usecols=[
            "Employee",
            "GRP",
            "Resigned",
            "LastDay",
            "Rank",
            "Level",
            "Start",
            "Acct",
        ],
        sheet_name="employees",
    )
    _df_emp["temp"] = _df_emp["Resigned"].apply(
        lambda x: True if x == "X" else False, True
    )
    _df_emp["Resigned"] = _df_emp["temp"]
    _df_emp = _df_emp.drop(columns=["temp"])

    _df_emp = _df_emp.loc[
        (
            ~_df_emp["Employee"].isin(
                [
                    "Conrado Cruz",
                    "Roy Saberon",
                    "Samuel Lucas",
                    "PM",
                    "SE",
                    "TE",
                    "UI",
                ]
            ),
        )
    ]
    _df_emp = _df_emp.rename(columns={"Acct": "Account"})
    return _df_emp, _df_eod


def main():
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.

    st.title(":bar_chart: Xamun Resources")

    xamun_container = st.container()
    all_fte_container = st.container()

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

        config = ConfigParser()
        config.read("config.ini")

        if config["datasource"]["source"] == "2":
            df_emp, df_eod = load_data2()
        else:
            df_emp, df_eod = load_data()

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
            {"Employee": "Allen Christian Tubo", "Remarks": "Full Stack"},
            {"Employee": "Avik Das", "Remarks": "Full Stack"},
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
            # {
            #     "Employee": "Aevin Earl Molina",
            #     "Remarks": "Web Dev",
            #     # "Group": "Xamun Delivery",
            #     "Billable Proj": "Xamun Content",
            #     "is_billed": False,
            # },
            {
                "Employee": "Aleeza Mae Agulay",
                "Remarks": "Designer",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Delivery Design, Steer2",
                "is_billed": False,
            },
            {
                "Employee": "Brain Tumibay",
                "Remarks": "Sr Web/Solution Architect",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, Karl, Avensys POC",
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
                "Billable Proj": "Xamun Core Support, Smart Pen R&D",
                "is_billed": False,
            },
            {
                "Employee": "Eduard Hinunangan",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support, Design Studio",
                "is_billed": False,
            },
            {
                "Employee": "Eliseo Libarion",
                "Remarks": "Sr Full Stack",
                # "Group": "Xamun Delivery",
                "Billable Proj": "",
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
                "Billable Proj": "WinCredit, Atlas Home, Solviva",
                "is_billed": False,
            },
            {
                "Employee": "Glen Ebina",
                "Remarks": "UI/UX",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Design, BPS,ShellPower",
                "is_billed": False,
            },
            {
                "Employee": "Ira Louise David",
                "Remarks": "Jr Flutter",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS",
                "is_billed": True,
            },
            # {
            #     "Employee": "Irish Quilla",
            #     "Remarks": "PM",
            #     # "Group": "Xamun Delivery",
            #     "Billable Proj": "Swiftloan, Steer",
            #     "is_billed": False,
            # },
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
                "Billable Proj": "Solviva, Avensys POC, Atlas Home",
                "is_billed": False,
            },
            {
                "Employee": "Jansen Neil Olay",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Design Studio",
                "is_billed": False,
            },
            {
                "Employee": "Jayson Echano",
                "Remarks": "Mobile Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS",
                "is_billed": False,
            },
            {
                "Employee": "Jessica Joy Angeles",
                "Remarks": "Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Ramcar",
                "is_billed": False,
            },
            {
                "Employee": "Jomar Lagunsad",
                "Remarks": "PM",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Project Management",
                "is_billed": True,
            },
            {
                "Employee": "Jomari Munsayac",
                "Remarks": "Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Steer2",
                "is_billed": False,
            },
            {
                "Employee": "Joseph Artillaga",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Design Studio",
                "is_billed": False,
            },
            {
                "Employee": "Kevin Paul Merwa",
                "Remarks": "Jr Backend",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Xamun Core Support",
                "is_billed": False,
            },
            {
                "Employee": "Krischell Villadulid",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Avensys POC",
                "is_billed": False,
            },
            {
                "Employee": "Lauren James Leal",
                "Remarks": "Web Dev",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Karl Group, Design Studio",
                "is_billed": False,
            },
            {
                "Employee": "Ma. Ethel Yatar",
                "Remarks": "Sr Tester",
                # "Group": "Xamun Delivery",
                "Billable Proj": "Karl Group, Shell Group",
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
                "Billable Proj": "Karl Group, RamCar",
                "is_billed": False,
            },
            {
                "Employee": "Noel Guevarra",
                "Remarks": "Mid Flutter",
                # "Group": "Xamun Delivery",
                "Billable Proj": "BPS, Steer Mobile for Xamun",
                "is_billed": False,
            },
            {
                "Employee": "Raymun Galvez",
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

        df_xamun_core = pd.DataFrame(core).sort_values(by="Employee").reset_index()
        df_xamun_core.index += 1

        fig = go.Figure(
            data=[
                go.Table(
                    columnorder=[
                        1,
                        2,
                        3,
                    ],
                    columnwidth=[
                        1,
                        5,
                        5,
                    ],
                    header=dict(
                        values=[
                            ["<b>LINE #</b>"],
                            ["<b>Name</b>"],
                            ["<b>Remarks</b>"],
                        ],
                        line_color="darkslategray",
                        fill_color="royalblue",
                        # align=["left", "center"],
                        font=dict(color="white", size=16),
                        # height=35,
                    ),
                    cells=dict(
                        values=[
                            df_xamun_core.index,
                            df_xamun_core.Employee,
                            df_xamun_core.Remarks,
                        ],
                        line_color="darkslategray",
                        fill=dict(
                            color=[
                                "paleturquoise",
                                "white",
                            ]
                        ),
                        align=["center", "left", "center"],
                        # font_size=12,
                        font=dict(color="black", size=16),
                        height=30,
                    ),
                )
            ]
        )
        fig.update_layout(height=400, title_text="Xamun Core")
        st.plotly_chart(fig, use_container_width=True)  # , height=600)

        df_xamun_core = pd.DataFrame(core2).sort_values(by="Employee").reset_index()
        df_xamun_core.index += 1

        fig = go.Figure(
            data=[
                go.Table(
                    columnorder=[
                        1,
                        2,
                        3,
                    ],
                    columnwidth=[
                        1,
                        5,
                        5,
                    ],
                    header=dict(
                        values=[
                            ["<b>LINE #</b>"],
                            ["<b>Name</b>"],
                            ["<b>Remarks</b>"],
                        ],
                        line_color="darkslategray",
                        fill_color="royalblue",
                        # align=["left", "center"],
                        font=dict(color="white", size=16),
                        # height=35,
                    ),
                    cells=dict(
                        values=[
                            df_xamun_core.index,
                            df_xamun_core.Employee,
                            df_xamun_core.Remarks,
                        ],
                        line_color="darkslategray",
                        fill=dict(
                            color=[
                                "paleturquoise",
                                "white",
                            ]
                        ),
                        align=["center", "left", "center"],
                        # font_size=12,
                        font=dict(color="black", size=16),
                        height=30,
                    ),
                )
            ]
        )
        fig.update_layout(height=350, title_text="Xamun Solutions")
        st.plotly_chart(fig, use_container_width=True)  # , height=600)

        _df_xamun_rest = pd.DataFrame(the_rest2)

        #########################################################################
        #
        #                    BILLED
        #
        #########################################################################
        st.header("BAI - Xamun Delivery")
        # st.header("Billable Xamun Projects")

        # is_sorted_by_grp = st.checkbox("Sort by Group?")

        df_xamun_billed = (
            _df_xamun_rest.loc[(_df_xamun_rest["is_billed"] == True)]
            # .sort_values(by=["Group", "Employee"] if is_sorted_by_grp else ["Employee"])
            .sort_values(by=["Employee"]).reset_index()
        )
        df_xamun_billed.index += 1

        fig = go.Figure(
            data=[
                go.Table(
                    columnorder=[1, 2, 3, 4],
                    columnwidth=[1, 4, 4, 5],
                    header=dict(
                        values=[
                            ["<b>LINE #</b>"],
                            ["<b>Name</b>"],
                            ["<b>Remarks</b>"],
                            # ["<b>Group</b>"],
                            ["<b>Billed Project</b>"],
                        ],
                        line_color="darkslategray",
                        fill_color="royalblue",
                        # align=["left", "center"],
                        font=dict(color="white", size=16),
                        # height=35,
                    ),
                    cells=dict(
                        values=[
                            df_xamun_billed.index,
                            df_xamun_billed.Employee,
                            df_xamun_billed.Remarks,
                            # df_xamun_billed["Group"],
                            df_xamun_billed["Billable Proj"],
                        ],
                        line_color="darkslategray",
                        fill=dict(
                            color=[
                                "paleturquoise",
                                "white",
                            ]
                        ),
                        align=["center", "left", "left", "left"],
                        # font_size=12,
                        font=dict(color="black", size=16),
                        height=30,
                    ),
                )
            ]
        )
        fig.update_layout(height=400, title_text="Billable")
        st.plotly_chart(fig, use_container_width=True)  # , height=600)

        #########################################################################
        #
        #                    BENCH
        #
        #########################################################################
        # st.header("Bench")

        # is_sorted_by_grp2 = st.checkbox("Sort by Group ?")

        df_xamun_rest = (
            _df_xamun_rest.loc[(_df_xamun_rest["is_billed"] == False)]
            .sort_values(
                # by=["Group", "Employee"] if is_sorted_by_grp2 else ["Employee"]
                by=["Employee"]
            )
            .reset_index()
        )
        df_xamun_rest.index += 1
        fig = go.Figure(
            data=[
                go.Table(
                    columnorder=[1, 2, 3, 4],
                    columnwidth=[1, 4, 4, 5],
                    header=dict(
                        values=[
                            ["<b>LINE #</b>"],
                            ["<b>Name</b>"],
                            ["<b>Remarks</b>"],
                            # ["<b>Group</b>"],
                            ["<b>Activities/Tasks</b>"],
                        ],
                        line_color="darkslategray",
                        fill_color="royalblue",
                        # align=["left", "center"],
                        font=dict(color="white", size=16),
                        # height=35,
                    ),
                    cells=dict(
                        values=[
                            df_xamun_rest.index,
                            df_xamun_rest.Employee,
                            df_xamun_rest.Remarks,
                            # df_xamun_rest["Group"],
                            df_xamun_rest["Billable Proj"],
                        ],
                        line_color="darkslategray",
                        fill=dict(
                            color=[
                                "paleturquoise",
                                "white",
                            ]
                        ),
                        align=["center", "left", "left", "left"],
                        # font_size=12,
                        font=dict(color="black", size=16),
                        height=30,
                    ),
                )
            ]
        )

        fig.update_layout(height=1100, title_text="Bench")
        st.plotly_chart(fig, use_container_width=True)  # , height=600)
        #############################################

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
        acct_list.sort()
        selected_accts = st.multiselect("Account", options=acct_list, default=acct_list)

        if is_active or is_resigned:
            st.dataframe(
                df_emp_copy.loc[
                    # (
                    #     (df_emp["RESIGNED"] != is_active)
                    #     | (df_emp["RESIGNED"] == is_resigned)
                    # ) &
                    (df_emp["Account"].isin(selected_accts))
                ],
                width=900,
                height=600,
                hide_index=True,
            )
        else:
            st.dataframe(None)
    return None


if __name__ == "__main__":
    main()
