import streamlit as st

# --- Page Config ---
st.set_page_config(page_title="Vibework | AEC Pivot Prototypes", layout="wide")

# --- Landing Page Content ---
st.title("🏗️ Vibework AI: Construction AEC Prototypes")

st.markdown("""
### Technical Validation & Sales Intelligence
Welcome to the Vibework mid-term deliverable dashboard. As part of our pivot into the **$18B Utah construction market**, we have developed two primary technical engines to validate our product-market fit.

**Use the sidebar on the left to explore our live prototypes:**

* **🛰️ Buying Signal Radar**: Automated market intelligence that scans 30 enterprise construction firms for innovation "buying signals."
* **📉 Project Risk Engine**: A dynamic simulation tool that predicts project finish dates and identifies financial exposure using Monte Carlo logic.

---
**Presented by:** Andrew Swenson, Canyon, Joseph, Ashton C., and Aston A.
""")

st.info("👈 Select a tool from the sidebar to begin the live demonstration.")