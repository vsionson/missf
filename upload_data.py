import pandas as pd
from snowflake.snowpark import Session
import snowflake.snowpark as snowpark
from snowflake.snowpark.functions import col
import streamlit as st


def from_xlsx_to_csv(**kwargs):
    df = pd.read_excel(
        xlsx_file,
        sheet_name=sheet_name,
        skiprows=kwargs.get("skiprows", 0),
        usecols=kwargs.get("usecols", None),
        date_format=kwargs.get("date_format", None),
        engine="openpyxl",
    )
    df.to_csv(stage_file, index=False, sep=kwargs.get("sep", ","))
    return None


CONNECTION_PARAMS = {
    "user": st.secrets.connections.snowflake.user,
    "password": st.secrets.connections.snowflake.password,
    "account": st.secrets.connections.snowflake.account,
    "role": st.secrets.connections.snowflake.role,
    "warehouse": st.secrets.connections.snowflake.warehouse,
    "database": st.secrets.connections.snowflake.database,
    "schema": st.secrets.connections.snowflake.schema,
}


MENU_ITEMS: str = "".join(
    [
        "A - Azure\n",
        "C - Collections/Invoice\n",
        "E - Employees\n",
        "H - Holiday\n",
        "R - Ratecard/Sales\n",
        "T - EOD\n\n",
        "X - Exit\n\nYour Choice: ",
    ]
)


FILE_NAME = {
    "A": (
        "/Users/shaun/projects/mis/data/data.xlsx",  # Excel file
        "Sheet1",  # sheet
        "/Users/shaun/projects/mis/data/csv/azure.csv",  # csv file
        "@db_mis.public.crayon",  # stage name
    ),
    "C": (
        "/Users/shaun/Documents/BAI Collections as of date.xlsx",
        "Raw",
        "/Users/shaun/projects/mis/data/csv/collections.csv",
        "@db_mis.public.collections",
    ),
    "E": (
        "/Users/shaun/Documents/Billing v3.0.xlsx",
        "employees",
        "/Users/shaun/projects/mis/data/csv/employees.csv",
        "@db_mis.public.employee",
    ),
    "H": (
        "/Users/shaun/Documents/Billing v3.0.xlsx",
        "Holidays",
        "/Users/shaun/projects/mis/data/csv/holidays.csv",
        "@db_mis.public.holidays",
    ),
    "R": (
        "/Users/shaun/Documents/Billing v3.0.xlsx",
        "RateCard",
        "/Users/shaun/projects/mis/data/csv/ratecard.csv",
        "@db_mis.public.ratecard",
    ),
    "T": (
        "/Users/shaun/eod/BAI EOD Log Report V2.xlsx",
        "data",
        "/Users/shaun/projects/mis/data/csv/eod.csv",
        "@db_mis.public.eod",
    ),
    "Y": (1, 2, 3, 4),
}


while True:
    which_one = input(MENU_ITEMS).upper()

    if which_one == "X":
        print("Exited.")
        break

    xlsx_file, sheet_name, stage_file, stage_name = FILE_NAME[which_one]

    session = Session.builder.configs(CONNECTION_PARAMS).create()

    if which_one == "A":  # azure
        from_xlsx_to_csv(skiprows=2, date_format={"UsageDate": "%Y-%m-%d %H:%M:%S"})
    elif which_one == "T":  # EOD
        from_xlsx_to_csv(
            usecols=["EmployeeName", "Date", "Account", "Hours", "Minutes"]
        )
    elif which_one == "C":  # Collections/Invoice
        from_xlsx_to_csv(sep="|")
    elif which_one == "R":  # RateCard/Sales
        from_xlsx_to_csv(
            skiprows=1,
            usecols=[
                "Employee",
                "Project",
                "InitRate",
                "FTE",
                "Period",
                "Rank",
                "Level",
                "Target2",
                "Billed",
                "ind_eligibility",
            ],
        )
    else:  # "E": employee, "H": holiday
        from_xlsx_to_csv()

    put_result = session.file.put(stage_file, stage_name, overwrite=True)

    print(put_result[0].status)
    print("\n")

    session.close()
