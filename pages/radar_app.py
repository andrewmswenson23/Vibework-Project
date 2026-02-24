import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# --- CONFIG ---
st.set_page_config(page_title="Vibework | Buying Signal Radar", layout="wide")

TARGETS = {
    "Hoffman Construction": "https://www.hoffmancorp.com",
    "Jacobs": "https://www.jacobs.com",
    "Skanska USA": "https://www.usa.skanska.com",
    "Turner Construction": "https://www.turnerconstruction.com",
    "Kiewit Corp.": "https://www.kiewit.com"
    # Add your full list of 30 targets here 
}

KEYWORDS = ["vdc", "digital twin", "predictive analytics", "machine learning", "workflow automation", "bim"]

def scan_site(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        for noise in soup(["script", "style", "nav", "footer", "header"]):
            noise.decompose()
        text = soup.get_text(separator=' ').lower()
        return {kw: text.count(kw) for kw in KEYWORDS}
    except:
        return {kw: 0 for kw in KEYWORDS}

# --- UI ---
st.title("🛰️ Buying Signal Radar")
st.subheader("Automated Lead Intelligence for AEC Innovation")

if st.button("🚀 Start Daily Scan"):
    results = []
    progress_bar = st.progress(0)
    
    for i, (name, url) in enumerate(TARGETS.items()):
        counts = scan_site(url)
        counts['Company'] = name
        results.append(counts)
        progress_bar.progress((i + 1) / len(TARGETS))
        time.sleep(0.5) # Polite scraping
    
    df = pd.DataFrame(results).set_index('Company')
    
    # Highlight companies where keywords were found
    st.success("Scan Complete!")
    
    # Create "High Intent" filter
    high_intent = df[df.sum(axis=1) > 0]
    
    st.markdown("### 🚨 High-Signal Targets")
    if not high_intent.empty:
        st.dataframe(high_intent.style.highlight_max(axis=0, color='#2980B9'))
    else:
        st.info("No major signal spikes detected in the last 24 hours.")

    st.markdown("### 📋 All Target Metrics")
    st.write(df)