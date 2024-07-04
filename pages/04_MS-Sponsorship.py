import pandas as pd
import streamlit as st
import plotly.express as px
from check_pwd import check_password


def main():

    if not check_password():
        st.stop()  # Do not continue if check_password is not True.

    st.title(":bar_chart: Microsoft Azure Sponsorship")

    sponsor_container = st.container()
    with sponsor_container:

        df_spons = pd.DataFrame(
            [
                ["Aug 5-Sep 4", 761],
                ["Sep 5-Oct 4", 1022],
                ["Oct 5-Nov 4", 1091],
                ["Nov 5-Dec 4", 1069],
                ["Dec 5-Jan 4", 1819],
                ["Jan 5-Feb 4", 1455],
                ["Feb 5-Mar 4", 1325],
                ["Mar 5-Apr 4", 1322],
                ["Apr 5-May 4", 1520],
            ],
            columns=["Period", "Monthly"],
        )

        df_spons["Variance"] = df_spons["Monthly"].pct_change(1) * 100

        fig = px.line(
            df_spons,
            x="Period",
            y="Monthly",
            template="ggplot2",
            title="BAI MS Sponsorship",
            text=["${:,.2f}".format(x) for x in df_spons["Monthly"]],
        )
        fig.update_traces(textposition="top center", textfont=dict(color="blue"))
        fig.update_layout(font=dict(size=14))
        st.plotly_chart(fig, use_container_width=True, height=200)

        st.divider()
        st.image(
            "./pages/BAI_sponsorship.jpg",
            caption="Sponsorship Monitoring",
        )

        # fig, ax = plt.subplots(figsize=(12, 4))
        # cont = ax.bar(
        #     df_spons["Period"].to_numpy(),
        #     df_spons["Monthly"].to_numpy(),
        #     width=0.5,
        #     label=df_spons["Monthly"].to_numpy(),
        # )
        # ax.set_title("BAI MS Sponsorship")
        # ax.bar_label(cont, color="white", label_type="center", fmt="{:,.0f}")
        # st.pyplot(fig)
        # st.dataframe(df_spons, use_container_width=True)

        # p = so.Plot(df_spons, x="Period", y="Monthly").add(so.Bar(width=0.5))
        # p.label(title="BAI MS Sponsorship")
        # f4 = plt.figure()
        # p.on(f4).show()
        # st.pyplot(f4, use_container_width=True)
    return None


if __name__ == "__main__":
    main()
