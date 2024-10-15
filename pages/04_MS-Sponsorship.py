import pandas as pd
import streamlit as st
import plotly.express as px
from configparser import ConfigParser
from pathlib import Path
from datetime import datetime


@st.cache_data
def load_data2():
    # config = ConfigParser()
    # config.read("config.ini")
    # path = config["sponsorship"]["path"]
    path = st.secrets.sponsorshipnoel.path

    def load_monthly(file):
        df: pd.DataFrame = pd.read_csv(
            file,
        )
        return df

    # arr = sorted(Path(path).glob("* 2024-*.csv"))
    arr = sorted(Path(path).glob("BAI Azure Sponsorship - Aug 1 to Oct 10 2024.csv"))
    arr_df = [load_monthly(el) for el in arr]
    df = pd.concat(arr_df).loc[:,["Date", "ServiceName", "ServiceType", "ServiceResource", "Cost"]]

    return df

def main():

    st.set_page_config(page_title="MIS Report", page_icon=":bar_chart:", layout="wide")

    st.title(":bar_chart: 12K Microsoft Azure Sponsorship")

    sponsor_container = st.container()

    df = load_data2()
    df["Date"] = df["Date"].astype("datetime64[ns]")
    df["ReportDate"] = df["Date"].dt.strftime("%Y-%m")

    df3 = df.groupby(["ServiceName"], as_index=False).agg({"Cost": "sum"})
    df4 = df.groupby(["ServiceResource"], as_index=False).agg({"Cost": "sum"})

    with sponsor_container:

        # monthly cost
        fig = px.bar(
            df.groupby(pd.Grouper(key="Date", freq="ME")).agg({"Cost": "sum"}).reset_index(),
            x="Date",
            y="Cost",
            text_auto=True,
            template="seaborn",
            opacity=0.89,
            title="Monthly Cost",
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)

        total_cost: float = df["Cost"].sum()
        max_date: datetime = df["Date"].max().strftime("%b %-d, %Y")

        # st.write(f"Running Total: {total_cost}")
        st.write("Running Total: $ {0:,.2f} as of {1}".format(total_cost, max_date))


        # running total by ServiceName
        fig = px.bar(
            df.groupby(["ServiceName"], as_index=False).agg({"Cost": "sum"}),
            # df3,
            x="ServiceName",
            y="Cost",
            text_auto=True,
            template="seaborn",
            opacity=0.89,
            title="Running Cost By Service",
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)


        # running total by ServiceResource
        fig = px.bar(
            df.groupby(["ServiceResource"], as_index=False).agg({"Cost": "sum"}),
            # df4,
            x="ServiceResource",
            y="Cost",
            text_auto=True,
            template="seaborn",
            opacity=0.89,
            title="Running Cost By Resource",
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)

    return None


# if __name__ == "__main__":
main()
