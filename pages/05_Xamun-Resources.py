import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark import Session
from pathlib import Path
from configparser import ConfigParser


xamun_projs = [
    "Xamun",
    "Xamun Delivery",
    "Advance Energy",
    "Xamun Marketplace",
    "Xamun Solutions",
    "Steer Marketplace",
    "ePCSO",
    "AE Project 2 WebUI",
]


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

    _df_employee = session.sql(
        "select EMPLOYEE,GRP from DB_MIS.SALES.EMPLOYEE where RESIGNED=False"
    ).to_pandas()

    _df_eod = session.sql("select * from DB_MIS.SALES.EOD").to_pandas()

    session.close()

    _df_employee = _df_employee.rename(columns={"EMPLOYEE": "Employee"})
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
        usecols=["Employee", "GRP", "Resigned"],
        sheet_name="employees",
    )

    _df_emp = _df_emp.loc[
        (_df_emp["Resigned"].str.upper() != "X")
        & (
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
            )
        ),
        ["Employee", "GRP"],
    ]

    return _df_emp, _df_eod


def fill_blanks(arrs, longest):
    for arr in arrs:
        i = len(arr)
        while i < longest:
            arr.append("")
            i += 1
    return None


def main():
    st.title("Xamun Resources")
    xamun_container = st.container()
    with xamun_container:
        _, _, col1, col2 = st.columns([0.25, 0.25, 0.25, 0.25])
        with col1:
            date_start = st.date_input("Starting Date", pd.Timestamp(2024, 6, 1))
        with col2:
            date_end = st.date_input("Ending Date", pd.Timestamp(2024, 6, 30))
        st.divider()

        date_start = date_start.strftime("%Y%m%d")
        date_end = date_end.strftime("%Y%m%d")

        df_emp, df_eod = load_data()
        df_eod.loc[(df_eod["Account"] == "SwiftLoan"), "Account"] = "Xamun Solutions"
        df_dd = df_emp.loc[(~df_emp["GRP"].str.upper().str.startswith("X"))]

        # filter by date range and filter-out non Xamun accts
        df_eod_xamun_projs = df_eod.loc[
            (df_eod["Date"] >= date_start)
            & (df_eod["Date"] <= date_end)
            & (df_eod.Account.isin(xamun_projs))
        ]
        df_eod_xamun_projs_with_da = df_eod.loc[
            (df_eod["Date"] >= date_start)
            & (df_eod["Date"] <= date_end)
            & (df_eod.Account.isin(xamun_projs + ["Data Analytics"]))
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
            & (
                df_eod_xamun_projs["EmployeeName"].isin(
                    [
                        "Allen Christian Tubo",
                        "Avik Das",
                        "Cyrill Binaohan",
                        "John Aldrich Callado",
                        "Maricar Mara",
                        "Sarah Jane Rosales",
                    ]
                )
            )
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
            title=f"Xamun Core ({_df.EmployeeName.nunique()} FTEs; {total_hrs} hrs)",
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
            & (
                ~df_eod_xamun_projs["EmployeeName"].isin(
                    [
                        "Allen Christian Tubo",
                        "Avik Das",
                        "Cyrill Binaohan",
                        "John Aldrich Callado",
                        "Maricar Mara",
                        "Sarah Jane Rosales",
                    ]
                )
            )
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

        _df = (
            df_analytics.groupby(
                ["Account", "EmployeeName"], as_index=False
            ).TotalHrs.sum()
        ).sort_values("EmployeeName")

        total_hrs = "{0:.2f}".format(_df.TotalHrs.sum())
        st.write(total_hrs)
        fig = px.bar(
            _df,
            x="EmployeeName",
            y="TotalHrs",
            color="Account",
            text_auto=True,
            title=f"Data Analytics ({_df.EmployeeName.nunique()} FTEs; {total_hrs} hrs)",
            hover_data=["Account", "TotalHrs"],
            template="ggplot2",
        )
        fig.update_traces(texttemplate="%{y:.2f}")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)

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
        product = [
            "Aevin Earl Molina",
        ]
        product.sort()

        platform = [
            "Allen Christian Tubo - Full Stack",
            "Avik Das - Full Stack",
            "Cyrill Binaohan - TL",
            "John Aldrich Callado - Sr. Flutter",
            "Maricar Mara - PM",
            "Sarah Jane Rosales - Tester",
        ]
        # platform.sort()

        platform_support = [
            "Von Lou Velle Segocio - Mid FrontEnd",
            "Kevin Paul Merwa - Jr Backend (Xamun Delivery)",
            "Noel Guevarra - Mid Flutter (Xamun Delivery)",
            "Erskine Roy Bornillo - Jr Backend (Xamun Delivery)",
            "Ira Louise David - Jr Flutter (Xamun Delivery)",
            "Jean May Alvarez - Mid Flutter (Xamun Delivery)",
        ]
        platform_support.sort()

        delivery = [
            "Janicah Lorra Cequeña - Tester",
            "Lauren James Leal - Backend",
            "Ma. Ethel Yatar - Sr Tester",
            "Mark Rayden Mirafuente - Jr Frontend",
            "Jomar Lagunsad - PM",
        ]
        delivery.sort()

        design = [
            "Glen Ebina - UI/UX",
            "Sam Lucas",
        ]
        design.sort()

        the_rest = [
            "Von Lou Velle Segocio - Mid FrontEnd (Xamun Core Support)",
            "Kevin Paul Merwa - Jr Backend        (Xamun Core Support)",
            "Noel Guevarra - Mid Flutter          (Xamun Core Support)",
            "Erskine Roy Bornillo - Jr Backend    (Xamun Core Support)",
            "Ira Louise David - Jr Flutter        (Xamun Core Support)",
            "Jean May Alvarez - Mid Flutter       (Xamun Core Support)",
            "Aevin Earl Molina                    (Product)",
            "Janicah Lorra Cequeña - Tester       (Xamun Delivery)",
            "Lauren James Leal - Backend          (Xamun Delivery)",
            "Ma. Ethel Yatar - Sr Tester          (Xamun Delivery)",
            "Mark Rayden Mirafuente - Jr Frontend (Xamun Delivery)",
            "Jomar Lagunsad - PM                  (Xamun Delivery)",
            "Glen Ebina - UI/UX                   (Design)",
            "Sam Lucas                            (Design)",
            "Dharyll Jan Calaliman                (QRI)",
            "Jayson Echano                        (QRI)",
            "Jessica Joy Angeles                  (QRI)",
            "Jomari Munsayac                      (QRI)",
            # "Ace Morris Pepito - Contractual       (DD - by July)",
            "Brian Tumibay                        (DD - by July)",
            "Dino Angelo Reyes                    (DD - by July)",
            "Eduard Hinunangan                    (DD - by July)",
            "Jansen Neil Olay                     (DD - by July)",
            "Joseph Artillaga                     (DD - by July)",
            # "Kenneth Audrey Arcenio  - Contractual   (DD - by July)",
            "Marc Alvin Villarin                  (DD - by July)",
            "Raymun Galvez                        (DD - by July)",
        ]

        longest = max(
            len(product),
            len(platform_support),
            len(platform),
            len(delivery),
            len(design),
            len(the_rest),
        )
        fill_blanks(
            [platform, platform_support, product, delivery, design, the_rest], longest
        )

        df_xamun_teams = pd.DataFrame(
            {
                "Platform": platform,
                "PlatformSupport": platform_support,
                "Product": product,
                "Delivery": delivery,
                "Design": design,
                "Rest": the_rest,
            },
            index=np.arange(1, longest + 1),
        )
        df_core = df_xamun_teams.loc[0:6, ["Platform"]]

        fig = go.Figure(
            data=[
                go.Table(
                    columnorder=[
                        1,
                        2,
                    ],
                    columnwidth=[
                        2,
                        5,
                    ],
                    header=dict(
                        values=[
                            ["<b>LINE #</b>"],
                            ["<b>PLATFORM</b>"],
                        ],
                        line_color="darkslategray",
                        fill_color="royalblue",
                        # align=["left", "center"],
                        font=dict(color="white", size=16),
                        # height=35,
                    ),
                    cells=dict(
                        values=[
                            df_core.index,
                            df_core.Platform,
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
        # st.header("FTE Distribution")
        fig.update_layout(height=400)
        fig.update_layout(title_text="FTE Distribution - Xamun Core")
        st.plotly_chart(fig, use_container_width=True)  # , height=600)

        # fig = go.Figure(
        #     data=[
        #         go.Table(
        #             columnorder=[1, 2, 3, 4, 5],
        #             columnwidth=[2, 5, 5, 5, 5],
        #             header=dict(
        #                 values=[
        #                     ["<b>LINE #</b>"],
        #                     ["<b>PLATFORM SUPPORT</b>"],
        #                     ["<b>PRODUCT</b>"],
        #                     ["<b>DELIVERY</b>"],
        #                     ["<b>DESIGN</b>"],
        #                 ],
        #                 line_color="darkslategray",
        #                 fill_color="royalblue",
        #                 # align=["left", "center"],
        #                 font=dict(color="white", size=16),
        #                 # height=35,
        #             ),
        #             cells=dict(
        #                 values=[
        #                     df_xamun_teams.index,
        #                     df_xamun_teams.PlatformSupport,
        #                     df_xamun_teams.Product,
        #                     df_xamun_teams.Delivery,
        #                     df_xamun_teams.Design,
        #                 ],
        #                 line_color="darkslategray",
        #                 fill=dict(
        #                     color=[
        #                         "paleturquoise",
        #                         "white",
        #                         "silver",
        #                         "white",
        #                         "silver",
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

        fig = go.Figure(
            data=[
                go.Table(
                    columnorder=[1, 2],
                    columnwidth=[2, 5],
                    header=dict(
                        values=[
                            ["<b>LINE #</b>"],
                            ["<b>The Rest</b>"],
                        ],
                        line_color="darkslategray",
                        fill_color="royalblue",
                        # align=["left", "center"],
                        font=dict(color="white", size=16),
                        # height=35,
                    ),
                    cells=dict(
                        values=[
                            df_xamun_teams.index,
                            df_xamun_teams.Rest,
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

        # st.header("The rest")
        fig.update_layout(height=1200)
        fig.update_layout(title_text="The Rest")
        st.plotly_chart(fig, use_container_width=True)  # , height=600)
        #############################################

    return None


if __name__ == "__main__":
    main()
