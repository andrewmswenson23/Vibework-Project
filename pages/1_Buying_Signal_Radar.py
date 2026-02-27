import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# --- CONFIG ---
st.set_page_config(page_title="Vibework | Buying Signal Radar", layout="wide")

TARGETS = {
    # --- Utah Power Players (The $18B Pipeline) ---
    "Big-D Construction": "https://big-d.com",
    "Layton Construction": "https://www.laytonconstruction.com", 
    "Okland Construction": "https://www.okland.com", 
    "Jacobsen Construction": "https://www.jacobsenconstruction.com", 
    "Staker Parson Companies": "https://www.stakerparson.com",
    "Rimrock Construction": "https://www.rimrock.us",
    "R&O Construction": "https://www.randoco.com", 
    "Ralph L. Wadsworth Construction": "https://www.wadsco.com",
    "Hogan & Associates Construction": "https://www.hoganconstruction.com",
    "Westland Construction": "https://www.westlandconstruction.com",
    "Clyde Companies": "https://www.clydeinc.com",
    "Geneva Rock Products": "https://genevarock.com",
    "Sunroc Corporation": "https://sunroc.com",
    "W.W. Clyde & Co.": "https://wwclyde.net",

    # --- National & Multistate Strategic Targets ---
    "Hoffman Construction": "https://www.hoffmancorp.com",
    "Jacobs": "https://www.jacobs.com",
    "McKinstry": "https://www.mckinstry.com",
    "Sundt Construction": "https://www.sundt.com",
    "Clayco": "https://www.claycorp.com",
    "Holder Construction": "https://www.holderconstruction.com",
    "Ryan Companies": "https://www.ryancompanies.com",
    "Skanska USA": "https://www.usa.skanska.com",
    "Lease Crutcher Lewis": "https://lewisbuilds.com",
    "HITT Contracting": "https://www.hitt.com",
    "GLY Construction": "https://www.gly.com",
    "Mortenson": "https://www.mortenson.com",
    "Lydig Construction": "https://www.lydig.com",
    "Swinerton": "https://www.swinerton.com",
    "McCarthy Building Companies": "https://www.mccarthy.com",
    "Hensel Phelps": "https://www.henselphelps.com",
    "Kiewit Corp.": "https://www.kiewit.com",
    "Turner Construction": "https://www.turnerconstruction.com",
    "DPR Construction": "https://www.dpr.com",
    "Granite Construction": "https://www.graniteconstruction.com",
    "Clark Construction": "https://www.clarkconstruction.com",
    "Whiting-Turner": "https://www.whiting-turner.com",
    "Balfour Beatty US": "https://balfourbeattyus.com",
    "PCL Construction": "https://www.pcl.com",
    "Primoris Services": "https://www.prim.com",
    "Hathaway Dinwiddie": "https://www.hathawaydinwiddie.com",
    "Devcon Construction": "https://www.devcon-const.com",
    "Flatiron Construction": "https://www.fdcorp.com/en",
    "Webcor": "https://www.webcor.com",
    "BNBuilders": "https://www.bnbuilders.com",
    "Sellen": "https://www.sellen.com",
    "Absher": "https://www.absherco.com",
    "Tutor Perini": "https://www.tutorperini.com",
    "Suffolk": "https://www.suffolk.com",
    "Zachry": "https://www.zachrygroup.com",
    "Austin Industries": "https://www.austin-ind.com",
    "JE Dunn": "https://www.jedunn.com",
    "Harvey-Cleary": "https://www.harvey-cleary.com",
    "Manhattan Construction": "https://www.manhattanconstruction.com",
    "Satterfield & Pontikes": "https://www.s-p-c.com",
    "SpawGlass": "https://www.spawglass.com",
    "Rogers-O'Brien": "https://www.r-o.com",
    "Pogue": "https://www.pogueconstruction.com",
    "Saunders": "https://www.saundersinc.com",
    "Shaw Construction": "https://www.shawconstruction.net",
    "GE Johnson": "https://www.gejohnson.com",
    "Adolfson & Peterson": "https://www.a-p.com",
    "Haselden": "https://www.haselden.com",
    "GH Phipps": "https://www.ghphipps.com"
}

KEYWORDS = ["vdc", "digital twin", "predictive analytics", "machine learning", "workflow automation", "bim"]

# ============================================
# TIER 1: FREE SURFACE SCANNER
# ============================================

def scan_site(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for noise in soup(["script", "style", "nav", "footer", "header", "head"]):
            noise.decompose()
            
        text = soup.get_text(separator=' ').lower()
        
        results = {}
        for kw in KEYWORDS:
            matches = re.findall(rf'\b{kw}\b', text)
            results[kw] = len(matches)
        return results
    except:
        return {kw: 0 for kw in KEYWORDS}

# ============================================
# TIER 2: FIRECRAWL DEEP SCANNER
# ============================================

@st.cache_data(show_spinner=False)
def deep_scan_firecrawl(url):
    """
    Cached so if you accidentally click it twice for the same URL, 
    it doesn't burn a second credit.
    """
    try:
        api_key = st.secrets.get("FIRECRAWL_API_KEY")
        if not api_key:
            return "⚠️ Please add FIRECRAWL_API_KEY to your Streamlit secrets."
            
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=api_key)
        
        # Scrape the URL and force Markdown format for AI processing
        scrape_result = app.scrape_url(url, params={'formats': ['markdown']})
        
        return scrape_result.get('markdown', 'No markdown returned.')
    except ImportError:
        return "⚠️ Error: The 'firecrawl' package is not installed. Add 'firecrawl-py' to requirements.txt"
    except Exception as e:
        return f"⚠️ API Error: {str(e)}"

# ============================================
# UI DASHBOARD
# ============================================

st.title("🛰️ Buying Signal Radar")
st.markdown("Automated lead intelligence parsing multi-state construction portfolios.")

tab1, tab2 = st.tabs(["📡 Tier 1: Surface Scan (Free)", "🔥 Tier 2: Deep Extraction (Firecrawl)"])

# --- TAB 1: FREE SCAN ---
with tab1:
    st.subheader("High-Volume Intelligence Scan")
    st.markdown("Uses basic NLP to scan all 63 targets simultaneously without using API credits.")
    
    if st.button("🚀 Start Free Daily Scan"):
        results = []
        progress_bar = st.progress(0)
        
        for i, (name, url) in enumerate(TARGETS.items()):
            counts = scan_site(url)
            counts['Company'] = name
            results.append(counts)
            progress_bar.progress((i + 1) / len(TARGETS))
            time.sleep(0.1) # Faster polling
        
        df = pd.DataFrame(results).set_index('Company')
        
        st.success("Surface Scan Complete!")
        
        high_intent = df[df.sum(axis=1) > 0]
        
        st.markdown("### 🚨 High-Signal Targets")
        if not high_intent.empty:
            st.dataframe(high_intent.style.highlight_max(axis=0, color='#2980B9'))
        else:
            st.info("No major signal spikes detected in the last 24 hours.")

        with st.expander("View All Target Metrics"):
            st.write(df)

# --- TAB 2: FIRECRAWL SCAN ---
with tab2:
    st.subheader("Deep Context Extraction")
    st.markdown("Deploy Firecrawl to extract structured, AI-ready markdown from a specific high-value target.")
    
    # Let the user pick ONE company to save credits
    selected_company = st.selectbox("Select Target for Deep Scan", list(TARGETS.keys()))
    selected_url = TARGETS[selected_company]
    
    st.info(f"Target URL: {selected_url}")
    
    # The Enterprise UX Guardrail
    st.warning("⚠️ **Credit Limit Warning:** You are on the free tier (500 credits). Running this deep extraction will consume 1 Firecrawl API credit.")
    
    confirm_scan = st.checkbox(f"I confirm I want to spend 1 credit to extract data from {selected_company}.")
    
    # The button is completely disabled until the checkbox is ticked
    if st.button(f"🔥 Run Deep Scan", disabled=not confirm_scan):
        with st.spinner(f"Firecrawl is extracting structured data from {selected_company}..."):
            markdown_result = deep_scan_firecrawl(selected_url)
            
            st.success("Extraction Complete! Data is now structured for LLM processing.")
            
            st.markdown("### Extracted Markdown Data")
            # Put the raw text in a scrollable box so it doesn't break the UI
            st.text_area("Firecrawl Output", markdown_result, height=400)
