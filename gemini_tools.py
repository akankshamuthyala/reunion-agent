import os
import json
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

load_dotenv()

vertexai.init(project=os.getenv("GOOGLE_CLOUD_PROJECT"), location="us-central1")
model = GenerativeModel("gemini-2.0-flash-001")

# TOOL 1 — Age Progression

def age_progression(case: dict) -> dict:
    years_missing = 2025 - case.get("year_missing", 2000)
    age_then = case.get("age_when_missing", 0)
    age_now = age_then + years_missing

    prompt = f"""You are a forensic age progression specialist working on a missing persons case.

CASE DETAILS:
Name: {case.get('name', 'Unidentified')}
Age when missing: {age_then}
Year went missing: {case.get('year_missing')}
Estimated current age: {age_now}
Physical description: {case.get('physical_description', 'Not available')}
Distinguishing marks: {', '.join(case.get('distinguishing_marks', []))}
Location: {case.get('last_known_location', {}).get('district', 'Unknown')}, {case.get('last_known_location', {}).get('state', 'Unknown')}

Respond ONLY as a JSON object:
{{
  "estimated_current_appearance": "detailed paragraph",
  "facial_changes": "specific facial aging description",
  "retained_identifiers": ["features that won't change"],
  "distinguishing_marks_now": "how marks appear today",
  "confidence_level": "HIGH / MEDIUM / LOW",
  "confidence_reason": "why",
  "search_descriptors": ["searchable tags"]
}}"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"raw_response": text, "parse_error": True}
    result["case_id"] = case.get("case_id")
    result["age_then"] = age_then
    result["age_now"] = age_now
    return result


# TOOL 2 — Sighting Match Analyser

def analyse_sighting(case: dict, sighting: dict) -> dict:
    prompt = f"""You are a missing persons case analyst. A new sighting has been reported.

MISSING PERSON ON FILE:
Case ID: {case.get('case_id')}
Name: {case.get('name', 'Unidentified')}
Age when missing: {case.get('age_when_missing')}
Year missing: {case.get('year_missing')}
Physical description: {case.get('physical_description', 'Not available')}
Distinguishing marks: {', '.join(case.get('distinguishing_marks', []))}
Last known location: {case.get('last_known_location', {}).get('district', 'Unknown')}, {case.get('last_known_location', {}).get('state', 'Unknown')}

NEW SIGHTING REPORT:
Date: {sighting.get('date', 'Not specified')}
Location: {sighting.get('location', 'Not specified')}
Description: {sighting.get('description', 'No description')}
Reporter: {sighting.get('reporter_name', 'Anonymous')}
Notes: {sighting.get('notes', 'None')}

Respond ONLY as a JSON object:
{{
  "match_confidence": "HIGH / MEDIUM / LOW / NO_MATCH",
  "confidence_score": 0-100,
  "matching_features": ["list"],
  "conflicting_features": ["list"],
  "match_reasoning": "2-3 sentence explanation",
  "geographic_plausibility": "assessment",
  "recommended_action": "ESCALATE_TO_FIELDWORK / REQUEST_MORE_INFO / MARK_UNLIKELY / CLOSE_SIGHTING",
  "trigger_consent_wall": true or false,
  "consent_reason": "reason"
}}

trigger_consent_wall = true if confidence_score >= 60."""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"raw_response": text, "parse_error": True}
    result["case_id"] = case.get("case_id")
    return result


# TOOL 3 — Risk Assessment

def assess_risk(case: dict) -> dict:
    prompt = f"""You are a child protection and missing persons risk analyst in India.

CASE FILE:
Case ID: {case.get('case_id')}
Name: {case.get('name', 'Unidentified')}
Age when missing: {case.get('age_when_missing')}
Gender: {case.get('gender', 'Not specified')}
Year missing: {case.get('year_missing')}
Duration missing: {2025 - case.get('year_missing', 2000)} years
Circumstances: {case.get('circumstances_of_disappearance', 'Not available')}
State: {case.get('last_known_location', {}).get('state', 'Unknown')}
Aadhaar available: {case.get('aadhaar_available', False)}
Status: {case.get('status')}

Respond ONLY as a JSON object:
{{
  "urgency_level": "CRITICAL / HIGH / MEDIUM / LOW",
  "risk_score": 0-100,
  "primary_risk": "main threat",
  "risk_factors": ["list"],
  "protective_factors": ["list"],
  "recommended_response_tier": 1,
  "tier_reasoning": "why this tier",
  "access_level": "FAMILY_ONLY / NGO_VERIFIED / INSTITUTION_VERIFIED / PUBLIC",
  "recommended_actions": ["prioritised list"],
  "consent_wall_required": true,
  "special_flags": ["child, tribal, undocumented, etc"]
}}"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"raw_response": text, "parse_error": True}
    result["case_id"] = case.get("case_id")
    return result


# TOOL 4 — Unidentified Person Profiler

def profile_unidentified(fragments: dict) -> dict:
    prompt = f"""You are a forensic social worker building an identity profile for an unidentified person found in India.

AVAILABLE FRAGMENTS:
Estimated age: {fragments.get('age_estimate', 'Unknown')}
Gender: {fragments.get('gender', 'Unknown')}
Physical description: {fragments.get('physical_description', 'Not available')}
Language spoken: {fragments.get('language_spoken', 'Unknown')}
Location found: {fragments.get('location_found', 'Unknown')}
Distinguishing marks: {fragments.get('distinguishing_marks', 'None')}
Clothing: {fragments.get('clothing', 'Not recorded')}
Behaviour notes: {fragments.get('behaviour_notes', 'None')}
Medical notes: {fragments.get('medical_notes', 'None')}
Words mentioned: {fragments.get('words_mentioned', 'None')}

Respond ONLY as a JSON object:
{{
  "probable_age_range": "e.g. 35-45 years",
  "probable_origin_region": "most likely state/region with reasoning",
  "probable_language_group": "language/dialect group",
  "identity_profile_summary": "2-3 sentence profile",
  "likely_disappearance_scenario": "most probable reason",
  "search_strategy": ["ordered steps to find family"],
  "databases_to_check": ["TrackChild, state police portals, etc"],
  "match_descriptors": ["searchable tags for Elastic"],
  "confidence_in_profile": "HIGH / MEDIUM / LOW",
  "special_considerations": ["sensitivity flags"],
  "immediate_actions": ["urgent next steps"]
}}"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"raw_response": text, "parse_error": True}
    result["input_fragments"] = fragments
    return result


# TEST

if __name__ == "__main__":
    print("\n🧪  REUNION — Gemini Tools Test\n")

    lakshmi = {
        "case_id": "RN-1998-0001",
        "name": "Lakshmi Bai",
        "age_when_missing": 8,
        "gender": "Female",
        "year_missing": 1998,
        "physical_description": "Small girl, dark complexion, long black hair, thin build",
        "distinguishing_marks": ["crescent birthmark on left wrist", "dimple on right cheek"],
        "last_known_location": {"district": "Varanasi", "state": "Uttar Pradesh"},
        "circumstances_of_disappearance": "Separated during Kumbh Mela crowd surge",
        "aadhaar_available": False,
        "family_contact": {"name": "Ramesh Bai"},
        "status": "matched_pending_consent",
        "category": "child"
    }

    print("TOOL 1 — Age Progression")
    print(json.dumps(age_progression(lakshmi), indent=2))

    sighting = {
        "date": "2024-03-15",
        "location": "Pune, Maharashtra",
        "description": "Woman ~34 years, dark complexion, dimple on right cheek, small mark on left wrist, UP Hindi accent",
        "reporter_name": "Sister Maria, St. Catherine's Shelter"
    }
    print("\nTOOL 2 — Sighting Match")
    print(json.dumps(analyse_sighting(lakshmi, sighting), indent=2))

    print("\nTOOL 3 — Risk Assessment")
    print(json.dumps(assess_risk(lakshmi), indent=2))

    fragments = {
        "age_estimate": "35-45",
        "gender": "Male",
        "language_spoken": "Odia and broken Hindi",
        "location_found": "Mumbai Central Railway Station",
        "distinguishing_marks": "tribal tattoo on right forearm",
        "behaviour_notes": "Disoriented, repeating village name — sounds like Kendrapara"
    }
    print("\nTOOL 4 — Unidentified Person Profiler")
    print(json.dumps(profile_unidentified(fragments), indent=2))

    print("\n✅  All 4 tools tested!")