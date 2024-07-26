import pandas as pd
from snowflake.snowpark import Session
import snowflake.snowpark as snowpark
from snowflake.snowpark.functions import col
import streamlit as st

connection_parameters = {
    "user": "Cozily5399",
    "password": "#3A9#^xGF29ii$TJ2%8Bef2ASzpk#eSQ",
    "account": "vnyurlw-dn22987",
    "role": "ACCOUNTADMIN",
    "warehouse": "COMPUTE_WH",
    "database": "DB_MIS",
    "schema": "PUBLIC",
}


# Options:
#     0 - Azure;
#     1 - EOD;
#     2 - Collections/Invoice;
#     3 - RateCard/Sales;
#     4 - Employee;
#     5 - Holiday


file_name = [
    (
        # "/Users/shaun/projects/mis/data/data.xlsx",  # Excel file
        "/Users/shaun/projects/mis/data/Azure Usage 2024-06.xlsx",  # Excel file
        "Sheet1",  # sheet
        # "/Users/shaun/projects/mis/data/csv/azure.csv",  # csv file
        "/Users/shaun/projects/mis/data/csv/azure_2024_06.csv",  # csv file
        "@db_mis.public.crayon",  # stage name
    ),
    (
        "/Users/shaun/eod/BAI EOD Log Report V2.xlsx",
        "data",
        "/Users/shaun/projects/mis/data/csv/eod.csv",
        "@db_mis.public.eod",
    ),
    (
        "/Users/shaun/Documents/BAI Collections as of date.xlsx",
        "Raw",
        "/Users/shaun/projects/mis/data/csv/collections.csv",
        "@db_mis.public.collections",
    ),
    (
        "/Users/shaun/Documents/Billing v3.0.xlsx",
        "RateCard",
        "/Users/shaun/projects/mis/data/csv/ratecard.csv",
        "@db_mis.public.ratecard",
    ),
    (
        "/Users/shaun/Documents/Billing v3.0.xlsx",
        "employees",
        "/Users/shaun/projects/mis/data/csv/employees.csv",
        "@db_mis.public.employee",
    ),
    (
        "/Users/shaun/Documents/Billing v3.0.xlsx",
        "Holidays",
        "/Users/shaun/projects/mis/data/csv/holidays.csv",
        "@db_mis.public.holidays",
    ),
]


def put_to_stage(**kwargs):
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


while True:
    which_one = int(
        input(
            "0 - Azure\n1 - EOD\n2 - Collections/Invoice\n3 - Ratecard/Sales\n4 - Employees\n5 - Holiday\n\n9 - Exit\n\nChoice: "
        )
    )

    if which_one == 9:
        break

    xlsx_file, sheet_name, stage_file, stage_name = file_name[which_one]

    session = Session.builder.configs(connection_parameters).create()

    if which_one == 0:  # azure
        put_to_stage(skiprows=2, date_format={"UsageDate": "%Y-%m-%d %H:%M:%S"})
    elif which_one == 1:  # EOD
        put_to_stage(usecols=["EmployeeName", "Date", "Account", "Hours", "Minutes"])
    elif which_one == 2:  # Collections/Invoice
        put_to_stage(sep="|")
    elif which_one == 3:  # RateCard/Sales
        put_to_stage(
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
    else:  # 4: employee, 5: holiday
        put_to_stage()

    put_result = session.file.put(stage_file, stage_name, overwrite=True)

    print(put_result[0].status)
    print("\n")

    session.close()
