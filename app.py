import streamlit as st
from check_pwd import check_password

p0 = st.Page("Azure_Consumption.py", title="Azure Consumption")
p1 = st.Page("pages/01_Projected_Revenue.py", title="Projected Revenue")
p2 = st.Page("pages/02_Lost_Opportunities.py", title="Lost Opportunities")
p3 = st.Page("pages/04_MS-Sponsorship.py", title="12K MS Sponsorship")
p4 = st.Page("pages/04_MS-Sponsorship_2nd.py", title="150K MS Sponsorship")
p5 = st.Page("pages/05_Xamun-Resources.py", title="Xamun Resources")

pg = st.navigation([p0, p1, p2, p3, p4, p5])
if not check_password():
    st.stop()  # Do not continue if check_password is not True.

pg.run()
