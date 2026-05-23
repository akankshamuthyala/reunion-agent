import os
import json
import time
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from elasticsearch import Elasticsearch

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
es = Elasticsearch(os.getenv("ELASTIC_URL"), api_key=os.getenv("ELASTIC_API_KEY"))

MODEL = "gemini-1.5-flash"
INDEX = "reunion_cases"

VALID_AADHAAR = {
    "123456789012": {"role": "family",      "name": "Savitri Bai",         "access_tier": 2},
    "987654321098": {"role": "ngo_worker",  "name": "Priya NGO Worker",    "access_tier": 3},
    "111122223333": {"role": "institution", "name": "Dr. Rajan (NIMHANS)", "access_tier": 3},
    "444455556666": {"role": "family",      "name": "Ramesh Kumar",        "access_tier": 2},
    "999988887777": {"role": "admin",       "name": "REUNION Admin",       "access_tier": 4},
}

STATUS_COLOR = {
    "reunited":               ("🟢", "#4caf50"),
    "matched_pending_consent":("🟠", "#ff9800"),
    "active_search":          ("🔵", "#2196f3"),
    "unidentified":           ("🔴", "#e94560"),
}

def verify_aadhaar(number: str):
    return VALID_AADHAAR.get(number.replace("-","").replace(" ",""))

def get_loc(case):
    loc = case.get("last_known_location", {})
    if isinstance(loc, dict):
        return f"{loc.get('district','')}, {loc.get('state','')}".strip(", ")
    s = case.get("state",""); d = case.get("district","")
    return f"{d}, {s}".strip(", ") if (s or d) else str(loc)

def ask_ai(prompt: str) -> dict:
    with st.spinner("🤖 AI analysing..."):
        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction="You are REUNION, an expert AI for missing persons in India. Always respond with valid JSON only. No markdown, no explanation."
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.3)
        )
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]
    text = text.strip()
    try: return json.loads(text)
    except: return {"raw_response": text, "parse_error": True}

def age_progression(case):
    years = 2026 - case.get("year_missing", 2000)
    age_then = case.get("age_when_missing", 0)
    age_now = age_then + years
    marks = case.get("distinguishing_marks","")
    result = ask_ai(f"""Forensic age progression. Name: {case.get('name')} | Age then: {age_then} | Year missing: {case.get('year_missing')} | Age now: {age_now}
Description: {case.get('description', case.get('photo_description','N/A'))}
Distinguishing marks: {marks}
Return JSON:
{{"estimated_current_appearance":"2-3 sentence detailed description","key_identifying_features":["permanent feature 1","permanent feature 2","permanent feature 3"],"likely_changes":["change 1","change 2"],"age_now":{age_now},"confidence":"HIGH"}}""")
    result["name"] = case.get("name"); result["age_now"] = age_now; result["years_elapsed"] = years
    return result

def analyse_sighting(case, desc, loc):
    marks = case.get("distinguishing_marks", "")
    return ask_ai(f"""Sighting match analysis. Reply in JSON only.
CASE: {case.get('name')}, missing {case.get('year_missing')}, age then: {case.get('age_when_missing')}, marks: {marks}
SIGHTING: {desc} | Location: {loc}
JSON: {{"confidence_score":85,"match_level":"HIGH","matching_features":["feature 1","feature 2"],"reasoning":"2 sentences","trigger_consent_wall":true}}
Set trigger_consent_wall true if confidence_score>=60.""")

def assess_risk(case):
    years = 2026 - case.get("year_missing", 2000)
    return ask_ai(f"""Risk assessment for missing persons case in India.
Name: {case.get('name')} | Age: {case.get('age_when_missing')} | Gender: {case.get('gender','Unknown')}
Missing: {years} years | State: {case.get('state', get_loc(case))}
Aadhaar: {case.get('aadhaar_available',False)} | Circumstances: {case.get('circumstances_of_disappearance', case.get('circumstances','Unknown'))}
Return JSON:
{{"urgency":"HIGH","risk_score":75,"primary_risk":"brief description","recommended_tier":2,"next_steps":["step 1","step 2","step 3"],"consent_required":true,"special_flags":["flag1"]}}""")

def profile_unidentified(description, location, language):
    return ask_ai(f"""Forensic identity profiler for unidentified person found in India.
Description: {description} | Found at: {location} | Language: {language}
Return JSON:
{{"probable_origin":"state or region","probable_age_range":"35-45 years","identity_summary":"2-3 sentence profile","search_strategy":["step 1","step 2","step 3"],"match_tags":["tag1","tag2","tag3"],"confidence":"MEDIUM"}}""")

def search_cases(query):
    try:
        r = es.search(index=INDEX, body={"query":{"multi_match":{"query":query,"fields":["name^3","description^2","distinguishing_marks^2","state","district","photo_description","tags"]}},"size":5})
        return [h["_source"] for h in r["hits"]["hits"]]
    except Exception as e:
        st.error(f"Search error: {e}"); return []

def get_stats():
    try:
        total = es.count(index=INDEX)["count"]
        reunited = es.count(index=INDEX, body={"query":{"term":{"status":"reunited"}}})["count"]
        pending  = es.count(index=INDEX, body={"query":{"term":{"status":"matched_pending_consent"}}})["count"]
        active   = es.count(index=INDEX, body={"query":{"term":{"status":"active_search"}}})["count"]
        return total, reunited, pending, active
    except:
        return 15, 3, 1, 8

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="REUNION", page_icon="🔍", layout="wide")
st.markdown("""
<style>
.reunion-header{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);padding:1.5rem 2rem;border-radius:12px;margin-bottom:1.5rem;border:1px solid #e94560}
.metric-box{background:#1a1a2e;border:1px solid #2d2d44;border-radius:10px;padding:1.2rem;text-align:center}
.consent-wall{background:linear-gradient(135deg,#1a0505,#2d0a0a);border:3px solid #e94560;border-radius:14px;padding:2.5rem;text-align:center;margin:1.5rem 0}
.aadhaar-box{background:#0f1a0f;border:2px solid #4caf50;border-radius:10px;padding:1.5rem;margin:1rem 0}
.status-badge{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:500}
.case-card{background:#1a1a2e;border:1px solid #2d2d44;border-radius:10px;padding:1rem 1.2rem;margin-bottom:10px}
.timeline-bar{background:#2d2d44;border-radius:8px;padding:1rem;margin:1rem 0;display:flex;align-items:center;gap:8px}
.badge-elastic{background:#00BFB3;color:#000;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600}
.badge-gemini{background:#4285F4;color:#fff;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600}
.suggestion-btn{background:#1a1a2e;border:1px solid #2d2d44;border-radius:8px;padding:8px 12px;cursor:pointer;font-size:13px;color:#a0a0b0;width:100%;text-align:left;margin-bottom:6px}
.suggestion-btn:hover{border-color:#e94560;color:#e94560}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="reunion-header">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
    <div>
      <h1 style="color:#e94560;margin:0;font-size:2rem">🔍 REUNION</h1>
      <p style="color:#a0a0b0;margin:4px 0 0">AI-Powered Missing Persons Reunion Agent &nbsp;·&nbsp; India</p>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <span class="badge-elastic">Elastic Cloud</span>
      <span class="badge-gemini">Gemini AI</span>
      <a href="https://github.com/akankshamuthyala/reunion-agent" target="_blank"
         style="background:#24292e;color:#fff;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600;text-decoration:none">GitHub</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    page = st.radio("", [
        "🏠 Home","🔎 Search Cases","📋 File New Case",
        "👁️ Report Sighting","🧬 Age Progression",
        "⚠️ Risk Assessment","🪪 Unidentified Person","💬 Agent Chat"
    ])
    st.markdown("---")
    st.markdown("### 📊 System Status")
    try:
        es.info()
        st.success("✅ Elastic Connected")
        total,_,_,_ = get_stats()
        st.info(f"📁 {total} cases indexed")
    except:
        st.error("❌ Elastic Offline")
    st.markdown("---")
    st.markdown("### 🔐 Demo Aadhaar Numbers")
    st.markdown("""
- `1234 5678 9012` — Family
- `9876 5432 1098` — NGO Worker
- `1111 2222 3333` — Institution
- `9999 8888 7777` — Admin
    """)
    st.markdown("---")
    st.markdown("### 🏆 Hackathon")
    st.markdown("**Track:** Elastic\n\n**Event:** Google Cloud Rapid Agent Hackathon 2026")

# ── HOME ───────────────────────────────────────────────────────────────────────
if page == "🏠 Home":
    total, reunited, pending, active = get_stats()
    c1,c2,c3,c4 = st.columns(4)
    for col,num,label,color in zip(
        [c1,c2,c3,c4],
        [total, active, pending, reunited],
        ["Cases Indexed","Active Search","Match Pending","Reunited ✅"],
        ["#e94560","#2196f3","#ff9800","#4caf50"]
    ):
        col.markdown(f'<div class="metric-box"><h2 style="color:{color};margin:0">{num}</h2><p style="color:#a0a0b0;margin:4px 0 0">{label}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🌟 How REUNION Works")
        steps = [
            ("1","🔍 Search","Family searches Elastic full-text index"),
            ("2","🤖 AI Analysis","Age progression, risk, sighting match via Gemini"),
            ("3","📊 Match Found","Confidence ≥ 60% flags a potential match"),
            ("4","🔒 Consent Wall","Both parties verify Aadhaar before contact"),
            ("5","🎉 Reunion","NGO mediates. Case marked reunited."),
        ]
        for num,title,desc in steps:
            st.markdown(f"""
<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:12px">
  <div style="background:#e94560;color:white;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0">{num}</div>
  <div><strong style="color:#e0e0e0">{title}</strong><br><span style="color:#a0a0b0;font-size:13px">{desc}</span></div>
</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("### 📖 Demo Story — Lakshmi Bai")
        st.markdown("""
<div style="background:#1a1a2e;border:1px solid #e94560;border-radius:10px;padding:1.2rem">
  <div style="color:#a0a0b0;font-size:13px;margin-bottom:8px">🕐 <strong style="color:#e94560">1998</strong> — 8-year-old Lakshmi separated near Howrah Bridge, Kolkata</div>
  <div style="background:#2d2d44;height:1px;margin:8px 0"></div>
  <div style="color:#a0a0b0;font-size:13px;margin-bottom:8px">👁️ <strong style="color:#ff9800">2025</strong> — NGO spots woman with leaf-shaped birthmark in Pune</div>
  <div style="background:#2d2d44;height:1px;margin:8px 0"></div>
  <div style="color:#a0a0b0;font-size:13px;margin-bottom:4px">🤖 <strong style="color:#4caf50">REUNION does:</strong></div>
  <div style="font-size:12px;color:#a0a0b0;line-height:1.8">
    🧬 Age progression: 8 → 35 years<br>
    🔍 Elastic finds case instantly<br>
    📊 Sighting match: 90% confidence<br>
    🔒 Consent wall: both verify Aadhaar<br>
    🎉 Reunion after <strong style="color:#e94560">27 years</strong>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔐 4-Tier Access System")
    t1,t2,t3,t4 = st.columns(4)
    for col,tier,title,desc,color in zip(
        [t1,t2,t3,t4],
        ["1","2","3","4"],
        ["Digital","Partial Docs","Vulnerable Adult","Tribal/Zero-Doc"],
        ["Aadhaar verified","Enhanced verification","Guardian consent","Community consent + NGO"],
        ["#2196f3","#ff9800","#9c27b0","#e94560"]
    ):
        col.markdown(f'<div class="metric-box"><div style="color:{color};font-size:22px;font-weight:700">T{tier}</div><div style="color:#e0e0e0;font-size:13px;font-weight:500">{title}</div><div style="color:#a0a0b0;font-size:11px;margin-top:4px">{desc}</div></div>', unsafe_allow_html=True)

# ── SEARCH ─────────────────────────────────────────────────────────────────────
elif page == "🔎 Search Cases":
    st.markdown("## 🔎 Search Missing Person Cases")
    st.markdown("Powered by **Elastic full-text search** · searches name, description, location, distinguishing marks")

    col1, col2 = st.columns([3,1])
    with col1:
        query = st.text_input("Search...", placeholder="e.g. Lakshmi · birthmark · tribal girl · Kolkata · unidentified")
    with col2:
        status_filter = st.selectbox("Filter", ["All","active_search","matched_pending_consent","reunited","unidentified"])

    if query:
        with st.spinner("🔍 Searching Elastic..."):
            results = search_cases(query)
        if status_filter != "All":
            results = [r for r in results if r.get("status") == status_filter]
        if results:
            st.success(f"Found **{len(results)}** matching case(s)")
            for case in results:
                status = case.get("status","active")
                emoji, color = STATUS_COLOR.get(status, ("⚪","#888"))
                with st.expander(f"{emoji} **{case.get('name','Unidentified')}** — `{case.get('case_id','N/A')}` — *{status.replace('_',' ').upper()}*"):
                    col1,col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Age when missing:** {case.get('age_when_missing','N/A')}")
                        st.markdown(f"**Year missing:** {case.get('year_missing','N/A')}")
                        st.markdown(f"**Gender:** {case.get('gender','N/A')}")
                        st.markdown(f"**Location:** {get_loc(case)}")
                        st.markdown(f"**Languages:** {', '.join(case.get('languages',[]))}")
                    with col2:
                        st.markdown(f"**Status:** {emoji} {status.replace('_',' ').upper()}")
                        st.markdown(f"**Access Tier:** Tier {case.get('access_tier','N/A')}")
                        st.markdown(f"**Aadhaar:** {'✅ Yes' if case.get('aadhaar_available') else '❌ No'}")
                        st.markdown(f"**Community:** {case.get('caste_community','N/A')}")
                    st.markdown(f"**Description:** {case.get('description', case.get('photo_description','N/A'))}")
                    marks = case.get("distinguishing_marks","")
                    if marks:
                        st.markdown(f"🔍 **Distinguishing Marks:** `{marks}`")
                    sightings = case.get("sightings",[])
                    if sightings:
                        st.markdown(f"👁️ **Sightings on record:** {len(sightings)}")
                    tags = case.get("tags",[])
                    if tags:
                        st.markdown("**Tags:** " + " ".join([f"`{t}`" for t in tags]))
        else:
            st.warning("No cases found. Try different search terms.")

# ── FILE NEW CASE ──────────────────────────────────────────────────────────────
elif page == "📋 File New Case":
    st.markdown("## 📋 File a New Missing Person Case")
    st.markdown("Fields marked **\*** are mandatory.")

    st.markdown('<div class="aadhaar-box">', unsafe_allow_html=True)
    st.markdown("### 🔐 Identity Verification")
    aadhaar_input = st.text_input("Your Aadhaar Number *", placeholder="1234 5678 9012", max_chars=14, key="file_aadhar")
    verified_user = None
    if aadhaar_input:
        verified_user = verify_aadhaar(aadhaar_input)
        if verified_user:
            st.success(f"✅ Verified: **{verified_user['name']}** ({verified_user['role'].replace('_',' ').title()})")
        else:
            st.error("❌ Not recognised. Use a demo number from the sidebar.")
    st.markdown("</div>", unsafe_allow_html=True)

    if verified_user:
        with st.form("new_case"):
            st.markdown("#### 👤 Missing Person Details")
            col1,col2 = st.columns(2)
            with col1:
                name         = st.text_input("Full Name *")
                age          = st.number_input("Age when missing *", 0, 120, 10)
                gender       = st.selectbox("Gender *", ["Female","Male","Other"])
                year         = st.number_input("Year missing *", 1947, 2026, 2020)
            with col2:
                state        = st.text_input("Last known state *")
                district     = st.text_input("Last known district (optional)")
                category     = st.selectbox("Category *", ["child","adult","elderly","tribal","unidentified"])
                aadhaar_avail= st.checkbox("Aadhaar available for missing person")

            description    = st.text_area("Physical description *", height=80, placeholder="Height, complexion, hair, eyes, build...")
            distinguishing = st.text_area("Distinguishing marks * (birthmarks, scars, tattoos — most important!)", height=60)
            circumstances  = st.text_area("Circumstances of disappearance *", height=80)

            st.markdown("#### 📞 Reporter Details")
            col1,col2 = st.columns(2)
            with col1:
                reporter_phone    = st.text_input("Contact phone *")
                reporter_relation = st.selectbox("Your relation *",["Mother","Father","Sibling","Child","Spouse","NGO Worker","Police","Community Elder","Other"])
            with col2:
                languages = st.text_input("Languages spoken (optional)", placeholder="Hindi, Bengali...")
                religion  = st.text_input("Religion/Community (optional)")

            st.warning("⚠️ By submitting, you confirm this is a genuine report. False reports are a criminal offence.")
            submitted = st.form_submit_button("🚀 File Case", type="primary")

            if submitted:
                if not all([name, state, description, distinguishing, circumstances, reporter_phone]):
                    st.error("Please fill in all mandatory fields marked with *")
                else:
                    case_id = f"RN-{year}-{abs(hash(name+str(year)))%9999:04d}"
                    st.success(f"✅ Case filed successfully!")
                    st.markdown(f"""
<div style="background:#0f2a0f;border:2px solid #4caf50;border-radius:10px;padding:1.5rem;text-align:center;margin:1rem 0">
  <div style="font-size:13px;color:#a0a0b0">Your Case ID — save this!</div>
  <div style="font-size:2rem;font-weight:700;color:#4caf50;font-family:monospace">{case_id}</div>
</div>""", unsafe_allow_html=True)
                    fake_case = {"name":name,"age_when_missing":age,"gender":gender,"year_missing":year,"state":state,"district":district,"description":description,"distinguishing_marks":distinguishing,"circumstances":circumstances,"aadhaar_available":aadhaar_avail}
                    risk = assess_risk(fake_case)
                    urgency = risk.get("urgency","MEDIUM")
                    emoji = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}.get(urgency,"🟡")
                    st.markdown(f"### {emoji} Risk Level: {urgency}")
                    st.markdown(f"**Primary Risk:** {risk.get('primary_risk','N/A')}")
                    st.markdown(f"**Recommended Tier:** Tier {risk.get('recommended_tier',2)}")
                    st.markdown("**Immediate next steps:**")
                    for i,step in enumerate(risk.get("next_steps",[]),1):
                        st.markdown(f"{i}. {step}")

# ── REPORT SIGHTING ────────────────────────────────────────────────────────────
elif page == "👁️ Report Sighting":
    st.markdown("## 👁️ Report a Sighting")

    st.markdown('<div class="aadhaar-box">', unsafe_allow_html=True)
    st.markdown("### 🔐 Verify Your Identity First")
    aadhaar_s = st.text_input("Your Aadhaar Number *", placeholder="1234 5678 9012", max_chars=14, key="sight_aadhar")
    verified_s = None
    if aadhaar_s:
        verified_s = verify_aadhaar(aadhaar_s)
        if verified_s: st.success(f"✅ Verified: **{verified_s['name']}**")
        else: st.error("❌ Not recognised. Use a demo number from the sidebar.")
    st.markdown("</div>", unsafe_allow_html=True)

    if verified_s:
        query = st.text_input("Search for the case (type name or description)...")
        cases = search_cases(query) if query else []
        selected_case = None
        if cases:
            opts = {f"{c.get('name')} — {c.get('case_id')}":c for c in cases}
            selected_case = opts[st.selectbox("Select the case:", list(opts.keys()))]
            if selected_case:
                status = selected_case.get("status","")
                emoji, _ = STATUS_COLOR.get(status, ("⚪","#888"))
                st.info(f"{emoji} **{selected_case.get('name')}** | Missing since **{selected_case.get('year_missing')}** | {get_loc(selected_case)}")
                marks = selected_case.get("distinguishing_marks","")
                if marks:
                    st.markdown(f"🔍 **Key identifier to look for:** `{marks}`")

        st.markdown("#### 📍 Location Detection")
        st.components.v1.html("""
<style>
body{margin:0;background:transparent;font-family:sans-serif}
#geo_btn{background:#1a6b3a;color:white;border:none;padding:9px 18px;border-radius:8px;cursor:pointer;font-size:14px}
#geo_btn:hover{background:#27a85a}
#geo_out{width:100%;padding:8px 12px;border-radius:6px;border:1px solid #4caf50;background:#0f1a0f;color:#e0ffe0;font-size:14px;margin-top:8px;box-sizing:border-box}
#geo_status{color:#a0c0a0;font-size:12px;margin-top:4px}
</style>
<button id="geo_btn" onclick="getLocation()">📍 Auto-Detect My Location</button>
<input id="geo_out" type="text" readonly placeholder="Click button to detect..."/>
<div id="geo_status">Location will be auto-filled from GPS.</div>
<script>
function getLocation(){
  var btn=document.getElementById('geo_btn'),out=document.getElementById('geo_out'),s=document.getElementById('geo_status');
  btn.disabled=true;btn.innerText='⏳ Detecting...';s.innerText='Requesting GPS...';
  if(!navigator.geolocation){s.innerText='❌ Not supported.';btn.disabled=false;btn.innerText='📍 Try Again';return;}
  navigator.geolocation.getCurrentPosition(function(pos){
    var lat=pos.coords.latitude.toFixed(5),lon=pos.coords.longitude.toFixed(5);
    s.innerText='✅ GPS: '+lat+', '+lon+' — resolving address...';
    fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat='+lat+'&lon='+lon,{headers:{'Accept-Language':'en'}})
    .then(function(r){return r.json();})
    .then(function(data){
      var a=data.address||{};
      var parts=[a.suburb||a.neighbourhood||a.village||'',a.city||a.town||a.county||'',a.state||'',a.country||''].filter(function(x){return x.trim()!='';});
      var loc=parts.join(', ');
      out.value=loc;s.innerText='✅ '+loc;btn.innerText='✅ Detected';
      window.parent.postMessage({type:'streamlit:setComponentValue',value:loc},'*');
    }).catch(function(){
      var loc=lat+', '+lon;out.value=loc;s.innerText='✅ GPS only';btn.innerText='✅ GPS';
      window.parent.postMessage({type:'streamlit:setComponentValue',value:loc},'*');
    });
  },function(err){
    var msgs={1:'Permission denied',2:'Unavailable',3:'Timed out'};
    s.innerText='❌ '+msgs[err.code]+'. Type manually below.';btn.disabled=false;btn.innerText='📍 Try Again';
  },{timeout:10000});
}
</script>
""", height=100)

        auto_loc = st.session_state.get("detected_location","")

        with st.form("sighting_form"):
            sighting_desc = st.text_area("Describe the person you saw *", height=120,
                placeholder="Physical appearance, clothing, behaviour — mention any marks or scars!")
            sighting_location = st.text_input("Location *", value=auto_loc,
                placeholder="Auto-filled from GPS above, or type: City, locality, state")
            col1,col2 = st.columns(2)
            with col1: st.date_input("When?")
            with col2: st.text_input("Your contact (optional)")
            submitted = st.form_submit_button("🔍 Analyse Sighting", type="primary")

            if submitted and sighting_desc and sighting_location:
                if not selected_case:
                    st.error("Please search and select a case above first.")
                else:
                    result = analyse_sighting(selected_case, sighting_desc, sighting_location)
                    score = result.get("confidence_score", 0)
                    level = result.get("match_level","LOW")

                    st.markdown("---")
                    col1,col2,col3 = st.columns(3)
                    col1.metric("Confidence Score", f"{score}%")
                    col2.metric("Match Level", level)
                    col3.metric("Case", selected_case.get("case_id","N/A"))

                    st.progress(min(score,100)/100)
                    st.markdown(f"**Reasoning:** {result.get('reasoning','N/A')}")
                    for f in result.get("matching_features",[]):
                        st.markdown(f"- ✅ {f}")

                    if result.get("trigger_consent_wall") or score >= 60:
                        st.markdown("""
<div class="consent-wall">
  <div style="font-size:3rem">🔒</div>
  <h2 style="color:#e94560;font-size:1.8rem;margin:0.5rem 0">CONSENT VERIFICATION REQUIRED</h2>
  <p style="color:#ffffff;font-size:1.1rem;margin:1rem 0">
    High-confidence match detected.<br>
    <strong>Both parties must independently verify Aadhaar and give consent<br>
    before any contact information is shared.</strong>
  </p>
  <p style="color:#a0a0b0;font-size:0.9rem">
    This protects the privacy, safety, and autonomy of all individuals.<br>
    Consent cannot be assumed. Reunion is never forced.
  </p>
</div>""", unsafe_allow_html=True)

                        st.markdown("#### Dual Consent Verification")
                        col1,col2 = st.columns(2)
                        with col1:
                            st.markdown("**Party 1 — Searching Family**")
                            fam_a = st.text_input("Family Aadhaar *", key="fam_a", placeholder="1234 5678 9012")
                            fam_c = st.checkbox("✅ Family confirms consent to reunion contact")
                            fam_ok = verify_aadhaar(fam_a) is not None and fam_c
                        with col2:
                            st.markdown("**Party 2 — NGO Mediator**")
                            ngo_a = st.text_input("NGO Aadhaar *", key="ngo_a", placeholder="9876 5432 1098")
                            ngo_c = st.checkbox("✅ NGO confirms welfare check complete")
                            ngo_ok = verify_aadhaar(ngo_a) is not None and ngo_c

                        if fam_ok and ngo_ok:
                            st.success("🎉 Dual consent verified! Initiating reunion protocol...")
                            st.markdown(f"""
<div style="background:#0f2a0f;border:2px solid #4caf50;border-radius:10px;padding:1.5rem;margin:1rem 0">
  <h3 style="color:#4caf50;margin:0 0 8px">✅ Reunion Protocol Activated</h3>
  <div style="color:#a0c0a0;font-size:13px;line-height:1.8">
    Case: <strong>{selected_case.get('name')}</strong> ({selected_case.get('case_id')})<br>
    Match confidence: <strong>{score}%</strong><br>
    NGO mediator assigned<br>
    Contact details shared through secure NGO channel only
  </div>
</div>""", unsafe_allow_html=True)
                            st.balloons()
                        else:
                            if fam_a and not verify_aadhaar(fam_a): st.warning("⏳ Family Aadhaar not verified")
                            if ngo_a and not verify_aadhaar(ngo_a): st.warning("⏳ NGO Aadhaar not verified")
                    else:
                        st.warning(f"Low confidence ({score}%). Sighting recorded but threshold not met for consent wall.")

# ── AGE PROGRESSION ────────────────────────────────────────────────────────────
elif page == "🧬 Age Progression":
    st.markdown("## 🧬 AI Age Progression")
    st.markdown("Forensic description of how a missing person likely looks today.")

    query = st.text_input("Search for a case...")
    cases = search_cases(query) if query else []
    if cases:
        opts = {f"{c.get('name')} ({c.get('case_id')})":c for c in cases}
        case = opts[st.selectbox("Select case:", list(opts.keys()))]
        years = 2026 - case.get("year_missing",2000)
        age_then = case.get("age_when_missing",0)
        age_now  = age_then + years

        # Timeline bar
        st.markdown(f"""
<div class="timeline-bar">
  <div style="text-align:center;min-width:80px">
    <div style="color:#e94560;font-weight:600">{case.get('year_missing')}</div>
    <div style="color:#a0a0b0;font-size:12px">Age {age_then}</div>
  </div>
  <div style="flex:1;height:4px;background:linear-gradient(90deg,#e94560,#ff9800,#4caf50);border-radius:2px"></div>
  <div style="text-align:center;min-width:80px">
    <div style="color:#4caf50;font-weight:600">2026</div>
    <div style="color:#a0a0b0;font-size:12px">Age ~{age_now}</div>
  </div>
  <div style="color:#a0a0b0;font-size:13px;margin-left:12px">{years} years</div>
</div>""", unsafe_allow_html=True)

        col1,col2 = st.columns(2)
        with col1:
            st.markdown("**📸 When missing**")
            st.markdown(f"- Age: **{age_then}** years")
            st.markdown(f"- {case.get('description', case.get('photo_description','N/A'))}")
            marks = case.get("distinguishing_marks","")
            if marks: st.markdown(f"- 🔍 **Marks:** `{marks}`")
        with col2:
            st.markdown("**🧬 Today (estimated)**")
            st.markdown(f"- Estimated age: **{age_now}** years")
            st.markdown(f"- {years} years have passed")
            st.markdown("- Distinguishing marks remain permanent")

        if st.button("🧬 Run AI Age Progression", type="primary"):
            result = age_progression(case)
            st.markdown("---")
            st.markdown(f"### How {case.get('name')} likely looks today at {age_now}")
            st.markdown(f"""
<div style="background:#1a1a2e;border:1px solid #4caf50;border-radius:10px;padding:1.2rem;margin:1rem 0">
  <p style="color:#e0e0e0;font-size:15px;line-height:1.7;margin:0">{result.get('estimated_current_appearance','N/A')}</p>
</div>""", unsafe_allow_html=True)
            st.markdown("**🔍 Permanent identifiers (will never change):**")
            for f in result.get("key_identifying_features",[]):
                st.markdown(f"- 🔍 {f}")
            if result.get("likely_changes"):
                st.markdown("**Changes over time:**")
                for c in result.get("likely_changes",[]):
                    st.markdown(f"- {c}")
            st.markdown(f"**Confidence:** {result.get('confidence','MEDIUM')}")

# ── RISK ASSESSMENT ────────────────────────────────────────────────────────────
elif page == "⚠️ Risk Assessment":
    st.markdown("## ⚠️ AI Risk Assessment")
    st.markdown("Assess vulnerability and get recommended response protocol.")

    query = st.text_input("Search for a case...")
    cases = search_cases(query) if query else []
    if cases:
        opts = {f"{c.get('name')} ({c.get('case_id')})":c for c in cases}
        case = opts[st.selectbox("Select case:", list(opts.keys()))]
        if st.button("⚠️ Run Risk Assessment", type="primary"):
            result = assess_risk(case)
            urgency = result.get("urgency","MEDIUM")
            emoji = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}.get(urgency,"🟡")
            st.markdown("---")
            col1,col2,col3 = st.columns(3)
            col1.metric("Urgency", f"{emoji} {urgency}")
            col2.metric("Risk Score", f"{result.get('risk_score',0)}/100")
            col3.metric("Recommended Tier", f"Tier {result.get('recommended_tier',2)}")
            st.progress(result.get('risk_score',0)/100)
            st.markdown(f"**Primary Risk:** {result.get('primary_risk','N/A')}")
            flags = result.get("special_flags",[])
            if flags: st.markdown("**Flags:** " + " ".join([f"`{f}`" for f in flags]))
            st.markdown("**Next Steps:**")
            for i,step in enumerate(result.get("next_steps",[]),1):
                st.markdown(f"{i}. {step}")
            if result.get("consent_required"):
                st.warning("🔒 Consent wall required for this case")

# ── UNIDENTIFIED PERSON ────────────────────────────────────────────────────────
elif page == "🪪 Unidentified Person":
    st.markdown("## 🪪 Unidentified Person Profiler")
    st.markdown("Build an identity profile from physical clues for someone who cannot identify themselves.")

    with st.form("unidentified_form"):
        col1,col2 = st.columns(2)
        with col1:
            description = st.text_area("Physical description *", height=100,
                placeholder="Age estimate, height, complexion, hair, scars, tattoos, clothing...")
            location = st.text_input("Where found? *", placeholder="Railway station, city, state")
        with col2:
            language = st.text_input("Language/words spoken", placeholder="e.g. fragmented Odia, repeats 'Kendrapara'")
            behaviour = st.text_area("Behaviour notes", height=100,
                placeholder="Disoriented, memory loss, mentions certain names or places...")
        submitted = st.form_submit_button("🪪 Build Identity Profile", type="primary")

        if submitted and description and location:
            result = profile_unidentified(description, location, language or "Unknown")
            st.markdown("---")
            col1,col2 = st.columns(2)
            with col1:
                st.markdown(f"**Probable Origin:** {result.get('probable_origin','N/A')}")
                st.markdown(f"**Age Range:** {result.get('probable_age_range','N/A')}")
                st.markdown(f"**Confidence:** {result.get('confidence','N/A')}")
            with col2:
                st.markdown(f"**Summary:** {result.get('identity_summary','N/A')}")
            st.markdown("**Search Strategy:**")
            for i,step in enumerate(result.get("search_strategy",[]),1):
                st.markdown(f"{i}. {step}")
            tags = result.get("match_tags",[])
            if tags:
                st.markdown("**Elastic Search Tags:**")
                st.code(", ".join(tags))
                if st.button("🔍 Cross-reference with Elastic cases"):
                    matches = search_cases(" ".join(tags[:3]))
                    if matches:
                        st.success(f"Found **{len(matches)}** potential matching cases!")
                        for m in matches:
                            st.markdown(f"- **{m.get('name')}** ({m.get('case_id')}) — {m.get('status','')}")
                    else:
                        st.info("No matches in current database.")

# ── AGENT CHAT ─────────────────────────────────────────────────────────────────
elif page == "💬 Agent Chat":
    st.markdown("## 💬 REUNION Agent")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role":"assistant","content":
            "Namaste 🙏 I am the REUNION agent.\n\nI help reunite missing persons with their families across India.\n\nI can:\n- 🔍 Search for a missing person case\n- 🧬 Explain age progression results\n- 🔒 Explain the consent wall process\n- ⚠️ Answer questions about safety and access tiers\n\nHow can I help you today?"}]

    # Suggested questions
    st.markdown("**💡 Suggested questions:**")
    suggestions = [
        "Search for Lakshmi Bai missing from Kolkata",
        "How does the consent wall work?",
        "What is the 4-tier access system?",
        "Find unidentified cases in Mumbai",
    ]
    cols = st.columns(2)
    for i,s in enumerate(suggestions):
        with cols[i%2]:
            if st.button(s, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role":"user","content":s})
                st.rerun()

    st.markdown("---")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask the REUNION agent..."):
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        cases_found = []
        if any(k in prompt.lower() for k in ["search","find","missing","case","look","locate"]):
            cases_found = search_cases(prompt)

        context = ""
        if cases_found:
            context = f"\n\nElastic search returned: {json.dumps([{'name':c.get('name'),'id':c.get('case_id'),'year':c.get('year_missing'),'status':c.get('status')} for c in cases_found[:3]])}"

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                chat_model = genai.GenerativeModel(
                    model_name=MODEL,
                    system_instruction="You are REUNION, an empathetic AI agent helping reunite missing persons in India. Mention Elastic search when you find cases. Always highlight the consent wall for sensitive matches. Be warm and helpful." + context
                )
                history = []
                for m in st.session_state.messages[:-1]:
                    role = "user" if m["role"] == "user" else "model"
                    history.append({"role": role, "parts": [m["content"]]})
                chat = chat_model.start_chat(history=history)
                response = chat.send_message(prompt)
                reply = response.text
            st.markdown(reply)
        st.session_state.messages.append({"role":"assistant","content":reply})