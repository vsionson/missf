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
    # path = config["sponsorshippam"]["path"]
    path = st.secrets.sponsorshippam.path

    def load_monthly(file):
        df: pd.DataFrame = pd.read_csv(
            file,
        )
        return df

    # arr = sorted(Path(path).glob("*.csv"))
    arr = sorted(Path(path).glob("AzureUsage-6.csv"))
    arr_df = [load_monthly(el) for el in arr]
    df = pd.concat(arr_df).loc[:,["Date", "ServiceName", "ServiceType", "ServiceRegion", "ServiceResource", "Cost"]]

    return df

def main():
    st.set_page_config(page_title="MIS Report", page_icon=":bar_chart:", layout="wide")

    st.title(":bar_chart: 150K Microsoft Azure Sponsorship")

    sponsor_container = st.container()

    df = load_data2()
    df["Date"] = df["Date"].astype("datetime64[ns]")
    df["ReportDate"] = df["Date"].dt.strftime("%Y-%m")

    with sponsor_container:

        #
        # monthly cost
        #
        fig = px.bar(
            # df.groupby(pd.Grouper(key="Date", freq="ME")).agg(Cost=("Cost", "sum")).reset_index(),
            # df2,
            df.groupby(["ReportDate"], as_index=False).agg({"Cost": "sum"})
            , x="ReportDate"
            , y="Cost"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Monthly Cost"
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)

        """
        Running Total text
        """
        total_cost: float = df["Cost"].sum()
        max_date: datetime = df["Date"].max().strftime("%b %-d, %Y")

        st.write("Running Total: $ {0:,.2f} as of {1}".format(total_cost, max_date))



        #
        # running total by ServiceName
        #
        fig = px.bar(
            # df.groupby(pd.Grouper(key="Date", freq="ME")).agg({"Cost": sum}),
            df.groupby(["ServiceName"], as_index=False).agg({"Cost": "sum"})
            , x="ServiceName"
            , y="Cost"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Running Cost By Service"
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)


        #
        # Running Cost By Resource (>= $20)
        #
        fig = px.bar(
            # df.groupby(pd.Grouper(key="Date", freq="ME")).agg({"Cost": sum}),
            df
            .groupby(["ServiceResource"], as_index=False)
            .agg({"Cost": "sum"})
            .query("Cost >= 20.0")
            , x="ServiceResource"
            , y="Cost"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Running Cost By Resource (>= $20)"
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)


        #
        # Running Cost By Resource (from $1-$20)
        #
        fig = px.bar(
            # df.groupby(pd.Grouper(key="Date", freq="ME")).agg({"Cost": sum}),
            df
            .groupby(["ServiceResource"], as_index=False).agg({"Cost": "sum"})
            .query("20 > Cost > 1.0")
            , x="ServiceResource"
            , y="Cost"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Running Cost By Resource (from $1-$20)"
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)


        #
        # By Service Region
        #
        fig = px.bar(
            df
            .groupby("ServiceRegion", as_index=False)
            .agg({"Cost": "sum"})
            .pipe(lambda _df: _df.loc[(_df.Cost > 1000)])
            , x="ServiceRegion"
            , y="Cost"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Running Cost By Service Region (> 1K)"
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2)
        st.plotly_chart(fig, use_container_width=True, height=200)


        #
        # By Service Name by Month, facet
        # Monthly Cost By Service Name (> 500)
        #
        fig = px.bar(
            df
            .groupby(["ReportDate", "ServiceName"], as_index=False)
            .agg(Total=("Cost", "sum"))
            .query("Total > 500")
            , x="ReportDate"
            , y="Total"
            , facet_row= "ServiceName"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Monthly Cost By Service Name (> 500)"
            , facet_row_spacing=0.1
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2, height=600)
        st.plotly_chart(fig, use_container_width=True)


        #
        # Monthly Cost By Service Type (> 500)
        #
        # st.dataframe(df
        #     .groupby(["ReportDate", "ServiceType"], as_index=False)
        #     .agg(Total=("Cost", "sum")).query("Total>500"))
        fig = px.bar(
            df
            .groupby(["ReportDate", "ServiceType"], as_index=False)
            .agg(Total=("Cost", "sum"))
            .query("Total > 500")
            , x="ReportDate"
            , y="Total"
            , facet_row= "ServiceType"
            , text_auto=True
            , template="seaborn"
            , opacity=0.89
            , title="Monthly Cost By Service Type (> 500)"
            , facet_row_spacing=0.2
        )
        fig.update_traces(texttemplate="%{y:,.2f}")
        fig.update_layout(bargap=0.2, height=1000)
        st.plotly_chart(fig, use_container_width=True)

    return None


# if __name__ == "__main__":
main()
