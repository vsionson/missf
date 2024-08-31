import pandas as pd

name = "Azure Usage 2024-07"
name2 = name.replace(" ", "_")
name2 = name2.replace("-", "_")
xlsx_file = f"/Users/shaun/projects/mis/data/{name}.xlsx"
sheet_name = "Sheet1"
csv_file = f"/Users/shaun/projects/mis/data/csv/{name2}.csv"

df = pd.read_excel(
    xlsx_file,
    sheet_name=sheet_name,
    skiprows=2,
    date_format={"UsageDate": "%Y-%m-%d %H:%M:%S"},
    engine="openpyxl",
)
df.to_csv(csv_file, index=False, sep=",")
