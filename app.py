import os
import json
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from elasticsearch import Elasticsearch

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
es = Elasticsearch(os.getenv("ELASTIC_URL"), api_key=os.getenv("ELASTIC_API_KEY"))

MODEL = "llama-3.3-70b-versatile"
INDEX = "reunion_cases"

# ── Demo Aadhaar numbers (for prototype / hackathon demo) ─────────────────────
VALID_AADHAAR = {
    "123456789012": {"role": "family",      "name": "Savitri Bai",        "access_tier": 2},
    "987654321098": {"role": "ngo_worker",  "name": "Priya NGO Worker",   "access_tier": 3},
    "111122223333": {"role": "institution", "name": "Dr. Rajan (NIMHANS)", "access_tier": 3},
    "444455556666": {"role": "family",      "name": "Ramesh Kumar",        "access_tier": 2},
    "999988887777": {"role": "admin",       "name": "REUNION Admin",       "access_tier": 4},
}

REQUIRED_FIELDS = {
    "name": "Full Name",
    "age_when_missing": "Age when missing",
    "gender": "Gender",
    "year_missing": "Year missing",
    "state": "Last known state",
    "description": "Physical description",
    "circumstances": "Circumstances of disappearance",
    "reporter_name": "Your name (reporter)",
    "reporter_phone": "Contact phone",
    "reporter_relation": "Your relation to missing person",
}

OPTIONAL_FIELDS = ["district", "aadhaar_available", "category", "languages", "religion"]


def verify_aadhaar(number: str):
    clean = number.replace("-", "").replace(" ", "")
    return VALID_AADHAAR.get(clean)


def get_location_str(case, default="Unknown"):
    loc = case.get("last_known_location", {})
    if isinstance(loc, dict):
        return f"{loc.get('district', default)}, {loc.get('state', default)}"
    st_val = case.get("state", "")
    dist_val = case.get("district", "")
    if st_val or dist_val:
        return f"{dist_val}, {st_val}".strip(", ")
    return str(loc) if loc else default


def ask_ai(prompt: str) -> dict:
    response = groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are an expert AI assistant for REUNION, a missing persons "
                "reunion system in India. Always respond with valid JSON only. "
                "No markdown, no explanation, just the JSON object."
            )},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"raw_response": text, "parse_error": True}


def age_progression(case: dict) -> dict:
    years = 2025 - case.get("year_missing", 2000)
    age_then = case.get("age_when_missing", 0)
    age_now = age_then + years
    marks = case.get("distinguishing_marks", "")
    prompt = f"""Forensic age progression specialist. Missing person case:
Name: {case.get('name')} | Age then: {age_then} | Year missing: {case.get('year_missing')} | Age now: {age_now}
Description: {case.get('description', case.get('physical_description', 'N/A'))}
Distinguishing marks: {marks}
Return JSON:
{{
  "estimated_current_appearance": "2-3 sentence detailed description of how they look today",
  "key_identifying_features": ["permanent feature 1", "permanent feature 2", "permanent feature 3"],
  "likely_changes": ["change 1", "change 2"],
  "age_now": {age_now},
  "confidence": "HIGH"
}}"""
    result = ask_ai(prompt)
    result["name"] = case.get("name")
    result["age_now"] = age_now
    result["years_elapsed"] = years
    return result


def analyse_sighting(case: dict, sighting_desc: str, sighting_location: str) -> dict:
    marks = case.get("distinguishing_marks", "")
    prompt = f"""Missing persons sighting analyst. Does this sighting match the case?
MISSING PERSON: {case.get('name')}, missing {case.get('year_missing')}, age then: {case.get('age_when_missing')}
Description: {case.get('description', case.get('physical_description', 'N/A'))}
Distinguishing marks: {marks}
SIGHTING: Location: {sighting_location} | Description: {sighting_desc}
Return JSON:
{{
  "confidence_score": 85,
  "match_level": "HIGH",
  "matching_features": ["feature 1", "feature 2"],
  "reasoning": "2 sentence explanation",
  "trigger_consent_wall": true
}}
trigger_consent_wall must be true if confidence_score >= 60."""
    return ask_ai(prompt)


def assess_risk(case: dict) -> dict:
    years = 2025 - case.get("year_missing", 2000)
    prompt = f"""Risk assessment for missing persons case in India.
Name: {case.get('name')} | Age: {case.get('age_when_missing')} | Gender: {case.get('gender', 'Unknown')}
Missing: {years} years | State: {case.get('state', case.get('last_known_location', {}).get('state', 'Unknown') if isinstance(case.get('last_known_location'), dict) else 'Unknown')}
Aadhaar: {case.get('aadhaar_available', False)} | Circumstances: {case.get('circumstances_of_disappearance', case.get('circumstances', 'Unknown'))}
Return JSON:
{{
  "urgency": "HIGH",
  "risk_score": 75,
  "primary_risk": "brief description",
  "recommended_tier": 2,
  "next_steps": ["step 1", "step 2", "step 3"],
  "consent_required": true,
  "special_flags": ["flag1"]
}}"""
    return ask_ai(prompt)


def profile_unidentified(description: str, location: str, language: str) -> dict:
    prompt = f"""Forensic identity profiler for unidentified person found in India.
Description: {description} | Found at: {location} | Language spoken: {language}
Return JSON:
{{
  "probable_origin": "state or region with reasoning",
  "probable_age_range": "35-45 years",
  "identity_summary": "2-3 sentence profile",
  "search_strategy": ["step 1", "step 2", "step 3"],
  "match_tags": ["tag1", "tag2", "tag3"],
  "confidence": "MEDIUM"
}}"""
    return ask_ai(prompt)


def search_cases(query: str) -> list:
    try:
        resp = es.search(index=INDEX, body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "description^2", "distinguishing_marks^2",
                               "state", "district", "photo_description", "tags"],
                }
            },
            "size": 5,
        })
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception as e:
        st.error(f"Search error: {e}")
        return []


# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="REUNION", page_icon="🔍", layout="wide")

st.markdown("""
<style>
body { background: #0d0d1a; }
.reunion-header {
    background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
    padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;
    border: 1px solid #e94560;
}
.metric-box {
    background: #1a1a2e; border: 1px solid #2d2d44;
    border-radius: 10px; padding: 1.2rem; text-align: center;
}
.consent-wall {
    background: linear-gradient(135deg, #1a0505, #2d0a0a);
    border: 3px solid #e94560; border-radius: 14px;
    padding: 2.5rem; text-align: center; margin: 1.5rem 0;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{border-color:#e94560} 50%{border-color:#ff8a80} }
.aadhaar-box {
    background: #0f1a0f; border: 2px solid #4caf50;
    border-radius: 10px; padding: 1.5rem; margin: 1rem 0;
}
.warning-box {
    background: #1a1000; border: 1px solid #ff9800;
    border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="reunion-header">
    <h1 style="color:#e94560;margin:0;font-size:2.2rem;">🔍 REUNION</h1>
    <p style="color:#a0a0b0;margin:0.5rem 0 0 0;font-size:1rem;">
    AI-Powered Missing Persons Reunion Agent &nbsp;·&nbsp; Elastic Search &nbsp;·&nbsp; Groq AI &nbsp;·&nbsp; India
    </p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    page = st.radio("", [
        "🏠 Home", "🔎 Search Cases", "📋 File New Case",
        "👁️ Report Sighting", "🧬 Age Progression",
        "⚠️ Risk Assessment", "🪪 Unidentified Person", "💬 Agent Chat"
    ])
    st.markdown("---")
    st.markdown("### 📊 System Status")
    try:
        es.info()
        st.success("✅ Elastic Connected")
        count = es.count(index=INDEX)["count"]
        st.info(f"📁 {count} cases indexed")
    except Exception:
        st.error("❌ Elastic Offline")
    st.markdown("---")
    st.markdown("### 🔐 Demo Aadhaar Numbers")
    st.markdown("""
    Use these to test access:
    - `1234 5678 9012` — Family
    - `9876 5432 1098` — NGO Worker  
    - `1111 2222 3333` — Institution
    - `9999 8888 7777` — Admin
    """)

# ── HOME ───────────────────────────────────────────────────────────────────────
if page == "🏠 Home":
    col1, col2, col3, col4 = st.columns(4)
    for col, num, label, color in zip(
        [col1, col2, col3, col4],
        ["15", "4", "1", "3"],
        ["Cases Indexed", "AI Tools Active", "Pending Match", "Reunited"],
        ["#e94560", "#4caf50", "#ff9800", "#2196f3"]
    ):
        col.markdown(f'<div class="metric-box"><h2 style="color:{color}">{num}</h2><p style="color:#a0a0b0">{label}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🌟 How REUNION Works")
        st.markdown("""
**1. File or Search** — Family files a case or searches Elastic full-text index.

**2. AI Analysis** — Age progression, risk assessment, and sighting match run automatically.

**3. Match Found** — When confidence ≥ 60%, system flags a potential match.

**4. 🔒 Consent Wall** — Before ANY contact info is shared, both parties verify Aadhaar & consent.

**5. Safe Reunion** — NGO or institution mediates. Case marked reunited.
        """)
    with col2:
        st.markdown("### 📖 Demo Story — Lakshmi Bai")
        st.info("""
**1998** — 8-year-old Lakshmi is separated from her mother near Howrah Bridge, Kolkata during a festival.

**2025** — An NGO worker in Pune spots a woman with a leaf-shaped birthmark on her left shoulder.

**REUNION does:**
- 🧬 Age progression: 8 → 35 years old
- 🔍 Elastic search: finds the case instantly  
- 📊 Sighting match: 90% confidence
- 🔒 Consent wall: both parties verify Aadhaar
- 🎉 Reunion initiated after 27 years
        """)

    st.markdown("---")
    st.markdown("### 🔐 Security Layers")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Tier 1 — Digital**\nAadhaar verified, standard consent flow.")
    with c2:
        st.markdown("**Tier 2 — Partial Docs**\nEnhanced verification before contact.")
    with c3:
        st.markdown("**Tier 4 — Tribal/Zero-Doc**\nCommunity consent + NGO witness required.")

# ── SEARCH ─────────────────────────────────────────────────────────────────────
elif page == "🔎 Search Cases":
    st.markdown("## 🔎 Search Missing Person Cases")
    st.markdown("Powered by **Elastic full-text search** across all 15 cases")

    query = st.text_input("Search by name, location, description, distinguishing marks...",
                          placeholder="e.g. Lakshmi, birthmark, tribal girl, Kolkata")
    if query:
        with st.spinner("🔍 Searching Elastic..."):
            results = search_cases(query)
        if results:
            st.success(f"Found **{len(results)}** matching case(s)")
            for case in results:
                status = case.get("status", "active")
                color = {"reunited": "green", "matched_pending_consent": "orange",
                         "active_search": "blue", "unidentified": "red"}.get(status, "grey")
                with st.expander(f"📁 {case.get('name', 'Unidentified')} — {case.get('case_id', 'N/A')} | :{color}[{status.upper()}]"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Age when missing:** {case.get('age_when_missing', 'N/A')}")
                        st.markdown(f"**Year missing:** {case.get('year_missing', 'N/A')}")
                        st.markdown(f"**Gender:** {case.get('gender', 'N/A')}")
                        st.markdown(f"**Location:** {get_location_str(case)}")
                    with col2:
                        st.markdown(f"**Status:** {status.upper()}")
                        st.markdown(f"**Access Tier:** Tier {case.get('access_tier', 'N/A')}")
                        st.markdown(f"**Aadhaar:** {'✅ Yes' if case.get('aadhaar_available') else '❌ No'}")
                        st.markdown(f"**Languages:** {', '.join(case.get('languages', []))}")
                    st.markdown(f"**Description:** {case.get('description', 'N/A')}")
                    marks = case.get("distinguishing_marks", "")
                    if marks:
                        st.markdown(f"**🔍 Distinguishing Marks:** {marks}")
                    tags = case.get("tags", [])
                    if tags:
                        st.markdown("**Tags:** " + " ".join([f"`{t}`" for t in tags]))
        else:
            st.warning("No cases found. Try different search terms.")

# ── FILE NEW CASE ──────────────────────────────────────────────────────────────
elif page == "📋 File New Case":
    st.markdown("## 📋 File a New Missing Person Case")
    st.markdown("Fields marked **\*** are mandatory.")

    # Aadhaar verification gate
    st.markdown('<div class="aadhaar-box">', unsafe_allow_html=True)
    st.markdown("### 🔐 Identity Verification Required")
    st.markdown("Enter your Aadhaar number to file a case. This prevents misuse and links you as the verified reporter.")
    aadhaar_input = st.text_input("Aadhaar Number *", placeholder="1234 5678 9012", max_chars=14)
    verified_user = None
    if aadhaar_input:
        verified_user = verify_aadhaar(aadhaar_input)
        if verified_user:
            st.success(f"✅ Verified: {verified_user['name']} ({verified_user['role'].replace('_', ' ').title()})")
        else:
            st.error("❌ Aadhaar not recognised. Use a demo number from the sidebar.")
    st.markdown("</div>", unsafe_allow_html=True)

    if verified_user:
        with st.form("new_case"):
            st.markdown("#### 👤 Missing Person Details")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *")
                age = st.number_input("Age when missing *", 0, 120, 10)
                gender = st.selectbox("Gender *", ["Female", "Male", "Other"])
                year = st.number_input("Year missing *", 1947, 2025, 2020)
            with col2:
                state = st.text_input("Last known state *")
                district = st.text_input("Last known district (optional)")
                category = st.selectbox("Category *", ["child", "adult", "elderly", "tribal", "unidentified"])
                aadhaar_avail = st.checkbox("Aadhaar available for missing person")

            description = st.text_area("Physical description *", height=80,
                                       placeholder="Height, complexion, hair, eyes, build...")
            distinguishing = st.text_area("Distinguishing marks * (birthmarks, scars, tattoos)",
                                          height=60, placeholder="Very important for matching!")
            circumstances = st.text_area("Circumstances of disappearance *", height=80,
                                         placeholder="When, where, how they went missing...")

            st.markdown("#### 📞 Reporter Details")
            col1, col2 = st.columns(2)
            with col1:
                reporter_phone = st.text_input("Contact phone *")
                reporter_relation = st.selectbox("Your relation *",
                    ["Mother", "Father", "Sibling", "Child", "Spouse", "NGO Worker",
                     "Police", "Community Elder", "Other"])
            with col2:
                languages = st.text_input("Languages spoken (optional)", placeholder="Hindi, Bengali...")
                religion = st.text_input("Religion/Community (optional)")

            st.markdown('<div class="warning-box">⚠️ By submitting, you confirm this is a genuine missing persons report. False reports are a criminal offence.</div>', unsafe_allow_html=True)

            submitted = st.form_submit_button("🚀 File Case", type="primary")

            if submitted:
                missing = [REQUIRED_FIELDS[f] for f in ["name", "state", "description", "circumstances"]
                           if not [name, state, description, circumstances][["name", "state", "description", "circumstances"].index(f)]]
                if missing:
                    st.error(f"Please fill in: {', '.join(missing)}")
                else:
                    case_id = f"RN-{year}-{abs(hash(name + str(year))) % 9999:04d}"
                    st.success(f"✅ Case filed successfully!")
                    st.info(f"**Case ID:** `{case_id}` — save this for updates.")
                    fake_case = {
                        "name": name, "age_when_missing": age, "gender": gender,
                        "year_missing": year, "state": state, "district": district,
                        "description": description, "distinguishing_marks": distinguishing,
                        "circumstances": circumstances, "aadhaar_available": aadhaar_avail,
                        "reporter_name": verified_user["name"], "reporter_relation": reporter_relation,
                    }
                    with st.spinner("Running AI risk assessment..."):
                        risk = assess_risk(fake_case)
                    urgency = risk.get("urgency", "MEDIUM")
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(urgency, "🟡")
                    st.markdown(f"### {emoji} Risk Assessment: {urgency}")
                    st.markdown(f"**Primary Risk:** {risk.get('primary_risk', 'N/A')}")
                    st.markdown(f"**Recommended Tier:** Tier {risk.get('recommended_tier', 2)}")
                    st.markdown("**Next Steps:**")
                    for s in risk.get("next_steps", []):
                        st.markdown(f"- {s}")

# ── REPORT SIGHTING ────────────────────────────────────────────────────────────
elif page == "👁️ Report Sighting":
    st.markdown("## 👁️ Report a Sighting")
    st.markdown("Spotted someone who might be a missing person? Report it here. Aadhaar verification required.")

    st.markdown('<div class="aadhaar-box">', unsafe_allow_html=True)
    st.markdown("### 🔐 Verify Your Identity")
    aadhaar_s = st.text_input("Your Aadhaar Number *", placeholder="1234 5678 9012", max_chars=14, key="sight_aadhar")
    verified_s = None
    if aadhaar_s:
        verified_s = verify_aadhaar(aadhaar_s)
        if verified_s:
            st.success(f"✅ Verified: {verified_s['name']}")
        else:
            st.error("❌ Not recognised. Use a demo number from the sidebar.")
    st.markdown("</div>", unsafe_allow_html=True)

    if verified_s:
        query = st.text_input("Search for the case (name, location, description)...")
        cases = search_cases(query) if query else []
        selected_case = None
        if cases:
            opts = {f"{c.get('name')} — {c.get('case_id')}": c for c in cases}
            selected_case = opts[st.selectbox("Select the case this sighting relates to:", list(opts.keys()))]
            if selected_case:
                st.info(f"📁 Case: **{selected_case.get('name')}** | Missing since **{selected_case.get('year_missing')}** | Status: **{selected_case.get('status','').upper()}**")

        # ── Auto-detect location via browser GPS ──────────────────────────────
        st.markdown("#### 📍 Location Detection")
        st.components.v1.html("""
<div style="font-family:sans-serif;">
  <button onclick="getLocation()" style="
    background:#1a6b3a; color:white; border:none; padding:10px 20px;
    border-radius:8px; cursor:pointer; font-size:14px; margin-bottom:8px;">
    📍 Auto-Detect My Location
  </button>
  <div id="loc_status" style="color:#a0a0b0; font-size:13px; margin-top:6px;"></div>
  <input id="loc_output" type="text" placeholder="Location will appear here..."
    style="width:100%; padding:8px; border-radius:6px; border:1px solid #444;
    background:#1a1a2e; color:white; margin-top:6px; font-size:14px;"
    oninput="sendToStreamlit(this.value)" />
</div>
<script>
function getLocation() {
  var s = document.getElementById('loc_status');
  var inp = document.getElementById('loc_output');
  s.innerText = '⏳ Detecting location...';
  if (!navigator.geolocation) {
    s.innerText = '❌ Geolocation not supported by your browser.';
    return;
  }
  navigator.geolocation.getCurrentPosition(function(pos) {
    var lat = pos.coords.latitude.toFixed(5);
    var lon = pos.coords.longitude.toFixed(5);
    s.innerText = '✅ GPS: ' + lat + ', ' + lon + ' — Resolving address...';
    fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat=' + lat + '&lon=' + lon)
      .then(r => r.json())
      .then(data => {
        var addr = data.address || {};
        var parts = [
          addr.suburb || addr.neighbourhood || addr.village || '',
          addr.city || addr.town || addr.county || '',
          addr.state || '',
          addr.country || ''
        ].filter(Boolean);
        var loc = parts.join(', ');
        inp.value = loc;
        s.innerText = '✅ Location detected: ' + loc;
        sendToStreamlit(loc);
      })
      .catch(function() {
        var loc = 'GPS: ' + lat + ', ' + lon;
        inp.value = loc;
        s.innerText = '✅ ' + loc + ' (address lookup failed)';
        sendToStreamlit(loc);
      });
  }, function(err) {
    var msgs = {1:'Permission denied', 2:'Position unavailable', 3:'Timed out'};
    s.innerText = '❌ ' + (msgs[err.code] || 'Error') + '. Please type location manually.';
  });
}
function sendToStreamlit(val) {
  // store in sessionStorage so Streamlit can read it on next rerun
  window.sessionStorage.setItem('auto_location', val);
}
</script>
""", height=130)

        # Read auto-detected location from session or let user type manually
        auto_loc = st.session_state.get("auto_location", "")
        sighting_location_default = auto_loc if auto_loc else ""

        with st.form("sighting_form"):
            st.markdown("#### 📝 Sighting Details")
            sighting_desc = st.text_area("Describe the person you saw *", height=120,
                                         placeholder="Physical appearance, clothing, behaviour, any marks...")
            sighting_location = st.text_input(
                "Location *",
                value=sighting_location_default,
                placeholder="Auto-detected above, or type: City, locality, state"
            )
            col1, col2 = st.columns(2)
            with col1:
                sighting_date = st.date_input("When?")
            with col2:
                st.text_input("Your contact (optional)")

            submitted = st.form_submit_button("🔍 Analyse Sighting", type="primary")

            if submitted and sighting_desc and sighting_location:
                if not selected_case:
                    st.error("Please search for and select a case above first.")
                else:
                    with st.spinner("AI analysing potential match..."):
                        result = analyse_sighting(selected_case, sighting_desc, sighting_location)

                    score = result.get("confidence_score", 0)
                    level = result.get("match_level", "LOW")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Confidence", f"{score}%")
                    col2.metric("Match Level", level)
                    col3.metric("Case", selected_case.get("case_id", "N/A"))

                    st.markdown(f"**Reasoning:** {result.get('reasoning', 'N/A')}")
                    features = result.get("matching_features", [])
                    if features:
                        for f in features:
                            st.markdown(f"- ✅ {f}")

                    if result.get("trigger_consent_wall") or score >= 60:
                        st.markdown("""
<div class="consent-wall">
    <h2 style="color:#e94560;font-size:1.8rem;">🔒 CONSENT VERIFICATION REQUIRED</h2>
    <p style="color:#ffffff;font-size:1.1rem;margin:1rem 0;">
        High-confidence match detected.<br>
        <strong>Both parties must independently verify Aadhaar and consent<br>
        before any contact information is shared.</strong>
    </p>
    <p style="color:#a0a0b0;font-size:0.9rem;">
        This protects the privacy, safety, and autonomy of all individuals involved.<br>
        Consent cannot be assumed. Reunion is never forced.
    </p>
</div>
                        """, unsafe_allow_html=True)

                        st.markdown("#### Consent Verification")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Party 1 — Searching Family**")
                            fam_aadhaar = st.text_input("Family Aadhaar *", key="fam_a", placeholder="1234 5678 9012")
                            fam_consent = st.checkbox("I confirm I consent to reunion contact")
                            fam_ok = verify_aadhaar(fam_aadhaar) is not None and fam_consent
                        with col2:
                            st.markdown("**Party 2 — NGO / Mediator Verification**")
                            ngo_aadhaar = st.text_input("NGO Aadhaar *", key="ngo_a", placeholder="9876 5432 1098")
                            ngo_consent = st.checkbox("NGO confirms welfare check complete")
                            ngo_ok = verify_aadhaar(ngo_aadhaar) is not None and ngo_consent

                        if fam_ok and ngo_ok:
                            st.success("🎉 Dual consent verified! Initiating reunion protocol...")
                            st.markdown(f"""
**✅ Reunion Protocol Activated**
- Case: {selected_case.get('name')} ({selected_case.get('case_id')})
- Match confidence: {score}%
- NGO mediator assigned
- Contact details will be shared through secure NGO channel only
- Both parties will be notified independently
                            """)
                            st.balloons()
                        elif fam_aadhaar or ngo_aadhaar:
                            if not fam_ok:
                                st.warning("⏳ Waiting for family Aadhaar verification and consent")
                            if not ngo_ok:
                                st.warning("⏳ Waiting for NGO verification")
                    else:
                        st.warning(f"Low confidence match ({score}%). Sighting recorded but does not meet the threshold for consent wall activation.")

# ── AGE PROGRESSION ────────────────────────────────────────────────────────────
elif page == "🧬 Age Progression":
    st.markdown("## 🧬 AI Age Progression")
    st.markdown("Generate a description of how a missing person likely looks today based on forensic aging principles.")

    query = st.text_input("Search for a case to run age progression on...")
    cases = search_cases(query) if query else []
    if cases:
        opts = {f"{c.get('name')} ({c.get('case_id')})": c for c in cases}
        case = opts[st.selectbox("Select case:", list(opts.keys()))]
        years = 2025 - case.get("year_missing", 2000)
        age_then = case.get("age_when_missing", 0)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📸 When Missing**")
            st.markdown(f"- Age: **{age_then}** years")
            st.markdown(f"- Year: **{case.get('year_missing')}**")
            st.markdown(f"- {case.get('description', case.get('photo_description', 'N/A'))}")
            marks = case.get("distinguishing_marks", "")
            if marks:
                st.markdown(f"- **Marks:** {marks}")
        with col2:
            st.markdown("**🧬 Today (estimated)**")
            st.markdown(f"- Estimated age: **{age_then + years}** years")
            st.markdown(f"- {years} years have passed")

        if st.button("🧬 Run AI Age Progression", type="primary"):
            with st.spinner("AI running forensic age progression..."):
                result = age_progression(case)
            st.markdown("---")
            st.markdown(f"### How {case.get('name')} likely looks today")
            st.markdown(f"**{result.get('estimated_current_appearance', 'N/A')}**")
            features = result.get("key_identifying_features", [])
            if features:
                st.markdown("**Permanent identifying features (won't change):**")
                for f in features:
                    st.markdown(f"- 🔍 {f}")
            changes = result.get("likely_changes", [])
            if changes:
                st.markdown("**Likely changes:**")
                for c in changes:
                    st.markdown(f"- {c}")
            st.markdown(f"**Confidence:** {result.get('confidence', 'MEDIUM')}")

# ── RISK ASSESSMENT ────────────────────────────────────────────────────────────
elif page == "⚠️ Risk Assessment":
    st.markdown("## ⚠️ AI Risk Assessment")
    st.markdown("Assess vulnerability level and get recommended response protocol.")

    query = st.text_input("Search for a case...")
    cases = search_cases(query) if query else []
    if cases:
        opts = {f"{c.get('name')} ({c.get('case_id')})": c for c in cases}
        case = opts[st.selectbox("Select case:", list(opts.keys()))]

        if st.button("⚠️ Run Risk Assessment", type="primary"):
            with st.spinner("Assessing risk factors..."):
                result = assess_risk(case)
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            urgency = result.get("urgency", "MEDIUM")
            emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(urgency, "🟡")
            col1.metric("Urgency", f"{emoji} {urgency}")
            col2.metric("Risk Score", f"{result.get('risk_score', 0)}/100")
            col3.metric("Recommended Tier", f"Tier {result.get('recommended_tier', 2)}")
            st.markdown(f"**Primary Risk:** {result.get('primary_risk', 'N/A')}")
            flags = result.get("special_flags", [])
            if flags:
                st.markdown("**Special Flags:** " + " ".join([f"`{f}`" for f in flags]))
            st.markdown("**Next Steps:**")
            for i, step in enumerate(result.get("next_steps", []), 1):
                st.markdown(f"{i}. {step}")
            if result.get("consent_required"):
                st.warning("🔒 Consent wall required for this case")

# ── UNIDENTIFIED PERSON ────────────────────────────────────────────────────────
elif page == "🪪 Unidentified Person":
    st.markdown("## 🪪 Unidentified Person Profiler")
    st.markdown("Found someone who doesn't know who they are? Build an identity profile from available clues.")

    with st.form("unidentified_form"):
        col1, col2 = st.columns(2)
        with col1:
            description = st.text_area("Physical description *", height=100,
                                       placeholder="Age estimate, height, build, complexion, hair, scars, tattoos...")
            location = st.text_input("Where found? *", placeholder="Railway station, city, state")
        with col2:
            language = st.text_input("Language/words spoken", placeholder="e.g. fragmented Odia, repeats 'Kendrapara'")
            behaviour = st.text_area("Behaviour notes", height=100,
                                     placeholder="Disoriented, memory loss, mentions certain names or places...")
        submitted = st.form_submit_button("🪪 Build Identity Profile", type="primary")

        if submitted and description and location:
            with st.spinner("Building forensic identity profile..."):
                result = profile_unidentified(description, location, language or "Unknown")
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Probable Origin:** {result.get('probable_origin', 'N/A')}")
                st.markdown(f"**Age Range:** {result.get('probable_age_range', 'N/A')}")
                st.markdown(f"**Profile Confidence:** {result.get('confidence', 'N/A')}")
            with col2:
                st.markdown(f"**Summary:** {result.get('identity_summary', 'N/A')}")
            st.markdown("**Search Strategy:**")
            for i, step in enumerate(result.get("search_strategy", []), 1):
                st.markdown(f"{i}. {step}")
            tags = result.get("match_tags", [])
            if tags:
                st.markdown("**Elastic Search Tags:**")
                st.code(", ".join(tags))
                if st.button("🔍 Cross-reference with Elastic cases"):
                    matches = search_cases(" ".join(tags[:3]))
                    if matches:
                        st.success(f"Found **{len(matches)}** potential matching cases!")
                        for m in matches:
                            st.markdown(f"- **{m.get('name')}** ({m.get('case_id')}) — {m.get('status', '')}")
                    else:
                        st.info("No matches in current database.")

# ── AGENT CHAT ─────────────────────────────────────────────────────────────────
elif page == "💬 Agent Chat":
    st.markdown("## 💬 REUNION Agent")
    st.markdown("Talk to the AI agent — search cases, ask about procedures, get help.")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": (
            "Namaste 🙏 I am the REUNION agent. I help reunite missing persons with their families in India.\n\n"
            "I can help you:\n- 🔍 Search for a missing person case\n- 🧬 Explain age progression\n"
            "- 🔒 Explain the consent wall process\n- ⚠️ Answer questions about filing a case\n\n"
            "How can I help you today?"
        )}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask the REUNION agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        cases_found = []
        if any(k in prompt.lower() for k in ["search", "find", "missing", "case", "look for", "locate"]):
            cases_found = search_cases(prompt)

        context = ""
        if cases_found:
            context = f"\n\nElastic search returned: {json.dumps([{'name': c.get('name'), 'id': c.get('case_id'), 'year': c.get('year_missing'), 'status': c.get('status')} for c in cases_found[:3]])}"

        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are REUNION, an empathetic AI agent helping reunite missing persons in India. "
                    "You explain processes clearly, mention the consent wall when relevant, and always prioritise "
                    "the safety and dignity of missing persons. Be warm and helpful." + context
                )},
                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            ]
        )
        reply = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)