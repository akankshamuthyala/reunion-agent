"""
REUNION — Elastic setup and demo data loader
Run once: python elastic_setup.py

Requirements: pip install elasticsearch python-dotenv

Env vars (.env file):
  ELASTIC_URL=https://your-deployment.es.region.cloud.es.io
  ELASTIC_API_KEY=your_api_key_here
"""

import json
import os
import sys
import argparse
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

ELASTIC_URL = os.getenv("ELASTIC_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
INDEX_NAME = "reunion_cases"

# ── Serverless-compatible index mapping (no shards/replicas) ──────────────────
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "case_id":             {"type": "keyword"},
            "name":                {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "aliases":             {"type": "text"},
            "age_when_missing":    {"type": "integer"},
            "date_of_birth":       {"type": "keyword"},
            "year_missing":        {"type": "integer"},
            "date_missing":        {"type": "keyword"},
            "gender":              {"type": "keyword"},
            "description":         {"type": "text"},
            "photo_description":   {"type": "text"},
            "distinguishing_marks":{"type": "text"},
            "last_known_location": {"type": "text"},
            "location_coordinates":{"type": "geo_point"},
            "state":               {"type": "keyword"},
            "district":            {"type": "keyword"},
            "status":              {"type": "keyword"},
            "access_tier":         {"type": "integer"},
            "reporter_name":       {"type": "text"},
            "reporter_contact":    {"type": "keyword", "index": False},
            "reporter_relation":   {"type": "keyword"},
            "case_notes":          {"type": "text", "index": False},
            "consent_given":       {"type": "boolean"},
            "consent_notes":       {"type": "keyword", "index": False},
            "languages":           {"type": "keyword"},
            "religion":            {"type": "keyword"},
            "caste_community":     {"type": "keyword"},
            "aadhaar_available":   {"type": "boolean"},
            "institution_involved":{"type": "boolean"},
            "institution_name":    {"type": "keyword"},
            "sightings": {
                "type": "nested",
                "properties": {
                    "sighting_id":   {"type": "keyword"},
                    "date":          {"type": "keyword"},
                    "location":      {"type": "text"},
                    "description":   {"type": "text"},
                    "submitted_by":  {"type": "keyword"},
                    "confidence":    {"type": "float"}
                }
            },
            "tags":                {"type": "keyword"},
            "created_at":          {"type": "date"},
            "updated_at":          {"type": "date"}
        }
    }
}

DEMO_CASES = [
  {
    "case_id": "RN-1998-0001",
    "name": "Lakshmi Bai",
    "aliases": ["Laxmi", "Lakshmi"],
    "age_when_missing": 8,
    "date_of_birth": "1990-03-14",
    "year_missing": 1998,
    "date_missing": "1998-06-12",
    "gender": "Female",
    "description": "Eight-year-old girl last seen near Howrah Bridge, Kolkata. Wearing a red salwar kameez. Spoke Bengali and some Hindi. Was travelling with her mother who was separated in the crowd during a festival.",
    "photo_description": "Small girl, dark complexion, black hair in two plaits, prominent dimples when smiling, slightly large front teeth.",
    "distinguishing_marks": "Birthmark shaped like a leaf on left shoulder blade. Small scar on right knee from a childhood fall.",
    "last_known_location": "Howrah Bridge, Kolkata, West Bengal",
    "location_coordinates": {"lat": 22.5851, "lon": 88.3468},
    "state": "West Bengal",
    "district": "Howrah",
    "status": "matched_pending_consent",
    "access_tier": 2,
    "reporter_name": "Savitri Bai",
    "reporter_contact": "+91-9800000001",
    "reporter_relation": "Mother",
    "case_notes": "Mother searched for 27 years. Possible match identified via NGO network in Pune, 2025.",
    "consent_given": False,
    "consent_notes": "Awaiting contact with potential match — consent wall active",
    "languages": ["Bengali", "Hindi"],
    "religion": "Hindu",
    "caste_community": "OBC",
    "aadhaar_available": False,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [
      {
        "sighting_id": "S-2025-0042",
        "date": "2025-01-15",
        "location": "Pune, Maharashtra",
        "description": "Woman in her mid-30s with leaf-shaped birthmark on left shoulder, matching dimples. Works at a textile factory. Does not know her birth family.",
        "submitted_by": "NGO_PuneCare",
        "confidence": 0.91
      }
    ],
    "tags": ["long-duration", "festival-separation", "high-confidence-match", "consent-wall-demo"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  },
  {
    "case_id": "RN-2020-0291",
    "name": "Anjali Singh",
    "aliases": ["Anju"],
    "age_when_missing": 34,
    "date_of_birth": "1986-11-02",
    "year_missing": 2020,
    "date_missing": "2020-03-28",
    "gender": "Female",
    "description": "Adult woman with depression who went missing during COVID-19 lockdown. Last seen leaving her apartment in Gurgaon. Family suspects she may have been admitted to a psychiatric facility.",
    "photo_description": "Medium height, wheatish complexion, short hair, usually wears glasses.",
    "distinguishing_marks": "Tattoo of a lotus on right wrist. Surgical scar on lower abdomen.",
    "last_known_location": "Sector 56, Gurgaon, Haryana",
    "location_coordinates": {"lat": 28.4089, "lon": 77.0423},
    "state": "Haryana",
    "district": "Gurugram",
    "status": "active_search",
    "access_tier": 1,
    "reporter_name": "Rajesh Singh",
    "reporter_contact": "+91-9800000002",
    "reporter_relation": "Husband",
    "case_notes": "Mental health history documented. Possible institutional admission.",
    "consent_given": True,
    "consent_notes": "Family consent on file",
    "languages": ["Hindi", "English"],
    "religion": "Hindu",
    "caste_community": "General",
    "aadhaar_available": True,
    "institution_involved": True,
    "institution_name": "Unknown — checking NIMHANS and state hospital records",
    "sightings": [],
    "tags": ["institution-search", "mental-health", "covid-lockdown", "aadhaar-linked"],
    "created_at": "2020-04-05T00:00:00Z",
    "updated_at": "2024-06-01T00:00:00Z"
  },
  {
    "case_id": "RN-2018-0356",
    "name": "Unidentified Male",
    "aliases": [],
    "age_when_missing": None,
    "date_of_birth": None,
    "year_missing": 2018,
    "date_missing": "2018-09-04",
    "gender": "Male",
    "description": "Unidentified adult male found at Dadar railway station, Mumbai. Estimated age 40-50. Disoriented, possibly with memory loss or cognitive impairment. No ID. Speaks fragmented Marathi and Kannada.",
    "photo_description": "Heavyset man, salt-and-pepper hair, full beard, dark complexion, approximately 5ft 8in.",
    "distinguishing_marks": "Missing tip of left index finger. Traditional tattoo in Kannada script on right forearm — appears to be a name. Deep scar across left cheek.",
    "last_known_location": "Dadar Railway Station, Mumbai, Maharashtra",
    "location_coordinates": {"lat": 19.0183, "lon": 72.8418},
    "state": "Maharashtra",
    "district": "Mumbai",
    "status": "unidentified",
    "access_tier": 2,
    "reporter_name": "Railway Police Dadar",
    "reporter_contact": "022-24150001",
    "reporter_relation": "Authority",
    "case_notes": "Currently in care of Snehi NGO shelter. Responds to name 'Ramu' but unsure if real name. Tattoo text being analysed.",
    "consent_given": False,
    "consent_notes": "Subject cannot give consent — guardian consent from NGO obtained",
    "languages": ["Marathi (fragmented)", "Kannada (fragmented)"],
    "religion": "Unknown",
    "caste_community": "Unknown",
    "aadhaar_available": False,
    "institution_involved": True,
    "institution_name": "Snehi NGO Shelter, Dadar",
    "sightings": [],
    "tags": ["unidentified", "railway-found", "cognitive-impairment", "profiler-demo"],
    "created_at": "2018-09-05T00:00:00Z",
    "updated_at": "2024-12-01T00:00:00Z"
  },
  {
    "case_id": "RN-2010-0033",
    "name": "Mohan Das",
    "aliases": ["Mohan", "Mohandu"],
    "age_when_missing": 12,
    "date_of_birth": "1998-07-20",
    "year_missing": 2010,
    "date_missing": "2010-11-03",
    "gender": "Male",
    "description": "Twelve-year-old boy who ran away from home after a dispute. Was located in Chennai in 2023 through the REUNION agent — now reunited with family.",
    "photo_description": "Tall for his age, very dark complexion, gap between front teeth, right ear slightly cauliflowered from childhood injury.",
    "distinguishing_marks": "Cauliflower right ear. Small burn scar on left palm.",
    "last_known_location": "Tirunelveli, Tamil Nadu",
    "location_coordinates": {"lat": 8.7139, "lon": 77.7567},
    "state": "Tamil Nadu",
    "district": "Tirunelveli",
    "status": "reunited",
    "access_tier": 1,
    "reporter_name": "Kamala Das",
    "reporter_contact": "+91-9800000003",
    "reporter_relation": "Mother",
    "case_notes": "Reunited 14 March 2023. Both parties consented. Case closed.",
    "consent_given": True,
    "consent_notes": "Full consent both parties. Reunion verified.",
    "languages": ["Tamil", "Malayalam"],
    "religion": "Hindu",
    "caste_community": "SC",
    "aadhaar_available": True,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [
      {
        "sighting_id": "S-2023-0001",
        "date": "2023-02-10",
        "location": "Chennai, Tamil Nadu",
        "description": "Man in late twenties working at auto-repair shop. Cauliflower right ear confirmed. Contacted by REUNION agent.",
        "submitted_by": "REUNION_Agent",
        "confidence": 0.96
      }
    ],
    "tags": ["reunited", "happy-path", "runaway", "completed-case"],
    "created_at": "2010-11-10T00:00:00Z",
    "updated_at": "2023-03-14T00:00:00Z"
  },
  {
    "case_id": "RN-2015-0088",
    "name": "Priya Oraon",
    "aliases": ["Priya"],
    "age_when_missing": 16,
    "date_of_birth": "1999-02-28",
    "year_missing": 2015,
    "date_missing": "2015-04-17",
    "gender": "Female",
    "description": "Teenage girl from Oraon tribal community in Jharkhand. Went missing after being recruited by a labour contractor promising factory work in another state. Suspected trafficking.",
    "photo_description": "Short, slim build, traditional tribal tattoos on chin and forehead, dark complexion.",
    "distinguishing_marks": "Traditional Oraon facial tattoos — three dots on chin, line marking on forehead. Speaks Kurukh as first language.",
    "last_known_location": "Ranchi District, Jharkhand",
    "location_coordinates": {"lat": 23.3441, "lon": 85.3096},
    "state": "Jharkhand",
    "district": "Ranchi",
    "status": "active_search",
    "access_tier": 4,
    "reporter_name": "Village Elder — Gram Sabha, Tamad Block",
    "reporter_contact": "Via NGO intermediary only",
    "reporter_relation": "Community",
    "case_notes": "No Aadhaar. No birth certificate. Identity established via community testimony. Tribal council involved.",
    "consent_given": True,
    "consent_notes": "Community consent via Gram Sabha resolution",
    "languages": ["Kurukh", "Hindi (basic)"],
    "religion": "Sarna",
    "caste_community": "Oraon (ST)",
    "aadhaar_available": False,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["tribal", "tier-4", "suspected-trafficking", "no-aadhaar", "zero-document"],
    "created_at": "2015-05-01T00:00:00Z",
    "updated_at": "2024-08-01T00:00:00Z"
  },
  {
    "case_id": "RN-2016-0144",
    "name": "Sunder Munda",
    "aliases": ["Sunder"],
    "age_when_missing": 10,
    "date_of_birth": "2006-01-15",
    "year_missing": 2016,
    "date_missing": "2016-08-22",
    "gender": "Male",
    "description": "Boy from Munda tribal community who went missing near Chaibasa. Family has no formal documents. Identity established through community records and school register.",
    "photo_description": "Lean boy, medium complexion, prominent cheekbones typical of Munda community, short cropped hair.",
    "distinguishing_marks": "Distinctive tribal bead bracelet was always worn — family kept an identical one. Smallpox vaccination scar on upper left arm.",
    "last_known_location": "Chaibasa, West Singhbhum, Jharkhand",
    "location_coordinates": {"lat": 22.5563, "lon": 85.8006},
    "state": "Jharkhand",
    "district": "West Singhbhum",
    "status": "active_search",
    "access_tier": 4,
    "reporter_name": "Budhan Munda",
    "reporter_contact": "Via CRY NGO intermediary",
    "reporter_relation": "Father",
    "case_notes": "Zero formal documentation. School register used as primary identity proof.",
    "consent_given": True,
    "consent_notes": "Father consent verified via NGO",
    "languages": ["Mundari", "Hindi"],
    "religion": "Sarna",
    "caste_community": "Munda (ST)",
    "aadhaar_available": False,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["tribal", "tier-4", "munda-community", "no-aadhaar", "child-missing"],
    "created_at": "2016-09-01T00:00:00Z",
    "updated_at": "2024-07-01T00:00:00Z"
  },
  {
    "case_id": "RN-2017-0209",
    "name": "Champa Santhali",
    "aliases": ["Champa"],
    "age_when_missing": 14,
    "date_of_birth": "2003-06-10",
    "year_missing": 2017,
    "date_missing": "2017-02-03",
    "gender": "Female",
    "description": "Teenage girl from Santhali community. Disappeared during seasonal migration with family to a brick kiln. Family returned without her — kiln contractor claims she left voluntarily.",
    "photo_description": "Tall for her age, light complexion for her community, long hair kept in a braid, always wore silver anklets.",
    "distinguishing_marks": "Distinctive silver anklets with bells. Scar from a burn on right forearm from brick kiln work. Traditional Santhali flower tattoo on right calf.",
    "last_known_location": "Brick kiln near Asansol, West Bengal",
    "location_coordinates": {"lat": 23.6834, "lon": 86.9567},
    "state": "West Bengal",
    "district": "Paschim Bardhaman",
    "status": "active_search",
    "access_tier": 4,
    "reporter_name": "Doman Soren",
    "reporter_contact": "Via Bandhan NGO intermediary",
    "reporter_relation": "Father",
    "case_notes": "Suspected bonded labour or trafficking from kiln. Contractor uncooperative.",
    "consent_given": True,
    "consent_notes": "Family consent. NGO co-signatory.",
    "languages": ["Santali", "Bengali (basic)"],
    "religion": "Sarna",
    "caste_community": "Santhali (ST)",
    "aadhaar_available": False,
    "institution_involved": True,
    "institution_name": "Brick kiln, Asansol — name withheld",
    "sightings": [],
    "tags": ["tribal", "tier-4", "bonded-labour", "kiln-disappearance", "santhali"],
    "created_at": "2017-03-01T00:00:00Z",
    "updated_at": "2024-09-01T00:00:00Z"
  },
  {
    "case_id": "RN-2019-0418",
    "name": "Ravi Kumar",
    "aliases": ["Ravi"],
    "age_when_missing": 7,
    "date_of_birth": "2012-04-05",
    "year_missing": 2019,
    "date_missing": "2019-10-14",
    "gender": "Male",
    "description": "Seven-year-old boy went missing during Dussehra fair in Varanasi. Was with grandparents who were separated in the crowd. Has a distinctive stutter.",
    "photo_description": "Chubby boy, fair complexion, large expressive eyes, wearing a yellow kurta on the day of disappearance.",
    "distinguishing_marks": "Pronounced stutter. Small haemangioma (red birthmark) below right ear. Dimple on left cheek only.",
    "last_known_location": "Dashashwamedh Ghat, Varanasi, Uttar Pradesh",
    "location_coordinates": {"lat": 25.3109, "lon": 83.0107},
    "state": "Uttar Pradesh",
    "district": "Varanasi",
    "status": "active_search",
    "access_tier": 2,
    "reporter_name": "Suresh Kumar",
    "reporter_contact": "+91-9800000004",
    "reporter_relation": "Father",
    "case_notes": "Festival crowd separation. CCTV footage reviewed — lost near chai stall at 7:43 PM.",
    "consent_given": True,
    "consent_notes": "Parent consent on file",
    "languages": ["Hindi", "Bhojpuri"],
    "religion": "Hindu",
    "caste_community": "OBC",
    "aadhaar_available": False,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["child", "festival-separation", "varanasi", "distinctive-stutter"],
    "created_at": "2019-10-15T00:00:00Z",
    "updated_at": "2024-03-01T00:00:00Z"
  },
  {
    "case_id": "RN-2021-0532",
    "name": "Meena Devi",
    "aliases": ["Meena"],
    "age_when_missing": 45,
    "date_of_birth": "1976-08-19",
    "year_missing": 2021,
    "date_missing": "2021-07-11",
    "gender": "Female",
    "description": "Middle-aged woman with early-onset dementia who wandered away from home in Jaipur. Cannot reliably communicate her own name or address. Likely confused and frightened.",
    "photo_description": "Short, slightly overweight, grey streaks in black hair, usually wears a blue or green saree.",
    "distinguishing_marks": "Dementia medical bracelet (may have been removed). Gold nose ring with a small ruby. Scar from appendix surgery.",
    "last_known_location": "Johari Bazaar, Jaipur, Rajasthan",
    "location_coordinates": {"lat": 26.9260, "lon": 75.8235},
    "state": "Rajasthan",
    "district": "Jaipur",
    "status": "active_search",
    "access_tier": 3,
    "reporter_name": "Deepak Devi",
    "reporter_contact": "+91-9800000005",
    "reporter_relation": "Son",
    "case_notes": "Dementia diagnosis on record. Wandering risk very high. Son checks hospitals weekly.",
    "consent_given": True,
    "consent_notes": "Son has medical power of attorney — consent valid",
    "languages": ["Hindi", "Rajasthani"],
    "religion": "Hindu",
    "caste_community": "General",
    "aadhaar_available": True,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [
      {
        "sighting_id": "S-2022-0011",
        "date": "2022-03-04",
        "location": "Old Age Home, Ajmer, Rajasthan",
        "description": "Elderly woman matching description admitted. Has gold nose ring. Cannot state name. Medical staff noted she sometimes says 'Jaipur' and 'Deepak'.",
        "submitted_by": "AjmerCare_NGO",
        "confidence": 0.74
      }
    ],
    "tags": ["dementia", "elderly", "wandering", "medical-power-of-attorney"],
    "created_at": "2021-07-12T00:00:00Z",
    "updated_at": "2022-03-04T00:00:00Z"
  },
  {
    "case_id": "RN-2022-0601",
    "name": "Arjun Sharma",
    "aliases": ["Arjun"],
    "age_when_missing": 17,
    "date_of_birth": "2005-12-01",
    "year_missing": 2022,
    "date_missing": "2022-05-09",
    "gender": "Male",
    "description": "Seventeen-year-old student who disappeared after his Class 12 board exam results. Family suspects he may have been distressed over results. No prior history of running away.",
    "photo_description": "Tall, slim, short hair, wears spectacles, often seen with a red backpack.",
    "distinguishing_marks": "Wears thick-framed glasses. Mole above left eyebrow. Plays guitar — calluses on left fingertips.",
    "last_known_location": "Andheri East, Mumbai, Maharashtra",
    "location_coordinates": {"lat": 19.1136, "lon": 72.8697},
    "state": "Maharashtra",
    "district": "Mumbai",
    "status": "active_search",
    "access_tier": 1,
    "reporter_name": "Vikram Sharma",
    "reporter_contact": "+91-9800000006",
    "reporter_relation": "Father",
    "case_notes": "Last seen at CSMT railway station. Exam stress suspected. iCall counsellor alerted.",
    "consent_given": True,
    "consent_notes": "Parent consent",
    "languages": ["Hindi", "English", "Marathi"],
    "religion": "Hindu",
    "caste_community": "General",
    "aadhaar_available": True,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["teen", "exam-stress", "recent", "tier-1", "mental-health-flag"],
    "created_at": "2022-05-10T00:00:00Z",
    "updated_at": "2024-11-01T00:00:00Z"
  },
  {
    "case_id": "RN-2023-0744",
    "name": "Fatima Begum",
    "aliases": ["Fatima"],
    "age_when_missing": 28,
    "date_of_birth": "1995-03-22",
    "year_missing": 2023,
    "date_missing": "2023-01-18",
    "gender": "Female",
    "description": "Young woman who went missing after a domestic dispute. Family has filed an FIR. She had spoken to a friend about leaving the city but destination unknown.",
    "photo_description": "Medium height, slender, usually wears hijab, speaks Urdu fluently.",
    "distinguishing_marks": "Henna tattoo patterns often on hands. Small diamond nose stud. Speaks with a slight Hyderabadi accent.",
    "last_known_location": "Charminar area, Hyderabad, Telangana",
    "location_coordinates": {"lat": 17.3616, "lon": 78.4747},
    "state": "Telangana",
    "district": "Hyderabad",
    "status": "active_search",
    "access_tier": 2,
    "reporter_name": "Rashida Begum",
    "reporter_contact": "+91-9800000007",
    "reporter_relation": "Mother",
    "case_notes": "Domestic situation complex. Welfare check required before any contact. She may not want to be found — autonomy protocol active.",
    "consent_given": False,
    "consent_notes": "Autonomy flag — she is an adult. Contact only if she consents. Consent wall mandatory.",
    "languages": ["Urdu", "Telugu", "Hindi"],
    "religion": "Islam",
    "caste_community": "OBC",
    "aadhaar_available": True,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["domestic-dispute", "adult-autonomy", "consent-wall", "welfare-check-first"],
    "created_at": "2023-01-20T00:00:00Z",
    "updated_at": "2024-02-01T00:00:00Z"
  },
  {
    "case_id": "RN-2023-0891",
    "name": "Gopal Yadav",
    "aliases": ["Gopal"],
    "age_when_missing": 62,
    "date_of_birth": "1961-09-07",
    "year_missing": 2023,
    "date_missing": "2023-11-27",
    "gender": "Male",
    "description": "Elderly man with Parkinson's disease who wandered from his son's home in Patna. May be confused and unable to state his address. Requires daily medication.",
    "photo_description": "Thin elderly man, white hair, walks with a slight tremor, often wears a dhoti and white kurta.",
    "distinguishing_marks": "Visible hand tremor from Parkinson's. Prominent vein on right temple. Missing two teeth on lower right.",
    "last_known_location": "Boring Road, Patna, Bihar",
    "location_coordinates": {"lat": 25.6093, "lon": 85.1376},
    "state": "Bihar",
    "district": "Patna",
    "status": "active_search",
    "access_tier": 3,
    "reporter_name": "Anil Yadav",
    "reporter_contact": "+91-9800000008",
    "reporter_relation": "Son",
    "case_notes": "Requires Parkinson's medication urgently. Check hospitals and dharmshalas first.",
    "consent_given": True,
    "consent_notes": "Son has healthcare POA",
    "languages": ["Hindi", "Bhojpuri", "Maithili"],
    "religion": "Hindu",
    "caste_community": "OBC",
    "aadhaar_available": True,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["elderly", "parkinsons", "medical-urgent", "wandering"],
    "created_at": "2023-11-28T00:00:00Z",
    "updated_at": "2024-01-15T00:00:00Z"
  },
  {
    "case_id": "RN-2024-1001",
    "name": "Kavya Reddy",
    "aliases": ["Kavya"],
    "age_when_missing": 9,
    "date_of_birth": "2015-06-14",
    "year_missing": 2024,
    "date_missing": "2024-04-02",
    "gender": "Female",
    "description": "Nine-year-old girl who went missing from her school in Bengaluru. Last seen at the school gate. School bus records show she did not board. CCTV shows an unknown auto-rickshaw.",
    "photo_description": "Bright-eyed girl, plaited hair with red ribbons, wearing school uniform — navy blue skirt and white shirt.",
    "distinguishing_marks": "Red ribbons in hair. School backpack with cartoon dinosaur. Small gap between her two front teeth.",
    "last_known_location": "DPS School Gate, Whitefield, Bengaluru",
    "location_coordinates": {"lat": 12.9719, "lon": 77.7499},
    "state": "Karnataka",
    "district": "Bengaluru Urban",
    "status": "active_search",
    "access_tier": 1,
    "reporter_name": "Suresh Reddy",
    "reporter_contact": "+91-9800000009",
    "reporter_relation": "Father",
    "case_notes": "Police FIR filed same day. Auto-rickshaw partial number plate: KA-05. Urgent.",
    "consent_given": True,
    "consent_notes": "Parent consent",
    "languages": ["Kannada", "Telugu", "English"],
    "religion": "Hindu",
    "caste_community": "OBC",
    "aadhaar_available": False,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["child", "school-gate", "urgent", "police-case", "recent-2024"],
    "created_at": "2024-04-02T00:00:00Z",
    "updated_at": "2024-04-05T00:00:00Z"
  },
  {
    "case_id": "RN-2024-1089",
    "name": "Unidentified Female",
    "aliases": [],
    "age_when_missing": None,
    "date_of_birth": None,
    "year_missing": 2024,
    "date_missing": "2024-06-15",
    "gender": "Female",
    "description": "Unidentified young woman found at New Delhi Railway Station. Estimated age 20-25. Speaks fragmented Malayalam and English. Disoriented, possible memory loss or trauma. Was carrying a college-style bag.",
    "photo_description": "Young woman, medium height, curly dark hair, wearing jeans and a blue kurta, college bag with a university sticker (sticker partially torn).",
    "distinguishing_marks": "Partial university sticker on bag — letters visible: '...AIT' or '...FAIT'. Small cross tattoo on right ankle. Speaks with Kerala accent.",
    "last_known_location": "New Delhi Railway Station, New Delhi",
    "location_coordinates": {"lat": 28.6428, "lon": 77.2197},
    "state": "Delhi",
    "district": "Central Delhi",
    "status": "unidentified",
    "access_tier": 2,
    "reporter_name": "GRP Delhi — Constable Rao",
    "reporter_contact": "011-23340000",
    "reporter_relation": "Authority",
    "case_notes": "In safe shelter. University sticker being investigated. Kerala accent suggests South Indian origin.",
    "consent_given": False,
    "consent_notes": "Cannot fully consent — trauma state. NGO guardian consent in place.",
    "languages": ["Malayalam (fragmented)", "English (partial)"],
    "religion": "Christian (probable)",
    "caste_community": "Unknown",
    "aadhaar_available": False,
    "institution_involved": True,
    "institution_name": "Shakti Shalini Shelter, New Delhi",
    "sightings": [],
    "tags": ["unidentified", "delhi-railway", "kerala-origin", "trauma", "profiler-demo"],
    "created_at": "2024-06-16T00:00:00Z",
    "updated_at": "2024-06-20T00:00:00Z"
  },
  {
    "case_id": "RN-2024-1201",
    "name": "Imran Sheikh",
    "aliases": ["Imran"],
    "age_when_missing": 14,
    "date_of_birth": "2010-02-17",
    "year_missing": 2024,
    "date_missing": "2024-09-30",
    "gender": "Male",
    "description": "Fourteen-year-old boy from a low-income family in Dharavi, Mumbai. Went missing after being approached by someone offering a phone repair apprenticeship in another city. Suspected child labour recruitment.",
    "photo_description": "Lean boy, very dark complexion, close-cropped hair, usually wears a blue t-shirt, always carries a small screwdriver set.",
    "distinguishing_marks": "Always carries a small screwdriver in his pocket — family identifying object. Chipped front tooth. Small burn mark on right thumb from soldering.",
    "last_known_location": "Dharavi, Mumbai, Maharashtra",
    "location_coordinates": {"lat": 19.0380, "lon": 72.8543},
    "state": "Maharashtra",
    "district": "Mumbai",
    "status": "active_search",
    "access_tier": 2,
    "reporter_name": "Salma Sheikh",
    "reporter_contact": "+91-9800000010",
    "reporter_relation": "Mother",
    "case_notes": "Suspected child labour trafficking. Bachpan Bachao Andolan alerted.",
    "consent_given": True,
    "consent_notes": "Parent consent",
    "languages": ["Hindi", "Marathi", "Urdu"],
    "religion": "Islam",
    "caste_community": "OBC",
    "aadhaar_available": False,
    "institution_involved": False,
    "institution_name": "",
    "sightings": [],
    "tags": ["child", "labour-trafficking", "dharavi", "recent-2024", "tier-2"],
    "created_at": "2024-10-01T00:00:00Z",
    "updated_at": "2024-10-05T00:00:00Z"
  }
]


def connect():
    if not ELASTIC_URL or not ELASTIC_API_KEY:
        print("❌  Missing ELASTIC_URL or ELASTIC_API_KEY in .env")
        sys.exit(1)
    es = Elasticsearch(ELASTIC_URL, api_key=ELASTIC_API_KEY)
    info = es.info()
    print(f"✅  Connected to Elasticsearch: {info['version']['number']}")
    return es


def create_index(es):
    if es.indices.exists(index=INDEX_NAME):
        print(f"⚠️   Index '{INDEX_NAME}' already exists — skipping creation")
        return
    # Serverless-compatible: mappings only, no settings block
    es.indices.create(index=INDEX_NAME, mappings=INDEX_MAPPING["mappings"])
    print(f"✅  Index '{INDEX_NAME}' created")


def bulk_index(es):
    actions = [
        {"_index": INDEX_NAME, "_id": case["case_id"], "_source": case}
        for case in DEMO_CASES
    ]
    success, errors = helpers.bulk(es, actions)
    print(f"✅  Indexed {success} cases")
    if errors:
        print(f"⚠️   Errors: {errors}")


def verify(es):
    es.indices.refresh(index=INDEX_NAME)
    count = es.count(index=INDEX_NAME)["count"]
    print(f"✅  Index contains {count} documents")


def run_sample_queries(es):
    print("\n── Sample queries ──────────────────────────────────────")

    # 1. Full text search
    r = es.search(index=INDEX_NAME, query={"match": {"description": "birthmark Kolkata"}})
    print(f"\n🔍  'birthmark Kolkata' → {r['hits']['total']['value']} hit(s)")
    for h in r["hits"]["hits"]:
        print(f"    {h['_source']['case_id']} — {h['_source']['name']} ({h['_source']['status']})")

    # 2. Filter by status
    r = es.search(index=INDEX_NAME, query={"term": {"status": "matched_pending_consent"}})
    print(f"\n🔍  status=matched_pending_consent → {r['hits']['total']['value']} hit(s)")
    for h in r["hits"]["hits"]:
        print(f"    {h['_source']['case_id']} — {h['_source']['name']}")

    # 3. Tribal / Tier 4 cases
    r = es.search(index=INDEX_NAME, query={"term": {"access_tier": 4}})
    print(f"\n🔍  access_tier=4 (tribal, zero-document) → {r['hits']['total']['value']} hit(s)")
    for h in r["hits"]["hits"]:
        print(f"    {h['_source']['case_id']} — {h['_source']['name']} ({h['_source']['caste_community']})")

    # 4. Unidentified persons
    r = es.search(index=INDEX_NAME, query={"term": {"status": "unidentified"}})
    print(f"\n🔍  status=unidentified → {r['hits']['total']['value']} hit(s)")
    for h in r["hits"]["hits"]:
        print(f"    {h['_source']['case_id']} — {h['_source']['name']}")

    # 5. Reunited cases
    r = es.search(index=INDEX_NAME, query={"term": {"status": "reunited"}})
    print(f"\n🔍  status=reunited (completed cases) → {r['hits']['total']['value']} hit(s)")
    for h in r["hits"]["hits"]:
        print(f"    {h['_source']['case_id']} — {h['_source']['name']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", action="store_true", help="Run sample search queries after setup")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate the index")
    args = parser.parse_args()

    print("🚀  REUNION — Elastic index setup")
    es = connect()

    if args.reset and es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"🗑️   Deleted existing index '{INDEX_NAME}'")

    create_index(es)
    bulk_index(es)
    verify(es)

    if args.queries:
        run_sample_queries(es)

    print("\n🎉  Setup complete! Your reunion_cases index is ready.\n")


if __name__ == "__main__":
    main()