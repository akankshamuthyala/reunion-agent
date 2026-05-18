# 🔍 REUNION — AI-Powered Missing Persons Reunion Agent

> Reuniting missing persons with their families using AI, ethical consent walls, and Elastic search.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://reunion-agent-cb8xctl8sy5arrhfykfaic.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 What is REUNION?

REUNION is an AI-powered missing persons reunion agent built for India. It helps families find missing loved ones using intelligent search, forensic age progression, and sighting matching — all protected by an ethical **consent wall** that ensures no contact information is shared without verified consent from both parties.

Every year, over 300,000 people go missing in India. Many are never found — not because the information doesn't exist, but because it's scattered, inaccessible, and unconnected. REUNION connects the dots.

---

## 🎯 The Demo Story

**1998** — 8-year-old Lakshmi Bai is separated from her mother near Howrah Bridge, Kolkata during a festival.

**2025** — An NGO worker in Pune spots a woman with a leaf-shaped birthmark on her left shoulder blade.

**REUNION does:**
- 🔍 Elastic search finds the case instantly
- 🧬 AI runs age progression: 8 → 35 years old
- 📊 Sighting match scores 90% confidence
- 🔒 Consent wall activates — both parties verify Aadhaar
- 🎉 Reunion initiated after 27 years

---

## ✨ Features

- **🔎 Elastic Full-Text Search** — Search 15+ cases by name, location, description, or distinguishing marks
- **🧬 AI Age Progression** — Forensic description of how a missing person looks today
- **👁️ Sighting Match Analysis** — AI scores sighting confidence and triggers consent wall at ≥60%
- **🔒 Consent Wall** — Dual Aadhaar verification required before any contact info is shared
- **⚠️ Risk Assessment** — AI flags urgency, trafficking risk, and recommended response tier
- **🪪 Unidentified Person Profiler** — Builds identity profile from fragments for unidentified persons
- **💬 Agent Chat** — Conversational AI agent with live Elastic search integration
- **📋 Case Filing** — Verified case filing with mandatory fields and AI risk assessment
- **📍 GPS Location Detection** — Auto-detects reporter location when filing sightings

---

## 🏗️ Architecture
<img width="1360" height="1160" alt="architecture" src="https://github.com/user-attachments/assets/d8453a74-ccdc-437d-b0b5-b07fc6d58f6f" />

![REUNION Architecture](https://raw.githubusercontent.com/akankshamuthyala/reunion-agent/main/architecture.png)

## 🔐 4-Tier Access System

| Tier | Who | How |
|------|-----|-----|
| Tier 1 | Aadhaar-verified individuals | Standard consent flow |
| Tier 2 | Partial documentation | Enhanced verification |
| Tier 3 | Vulnerable adults | Guardian consent required |
| Tier 4 | Tribal / zero-document | Community consent + NGO witness |

---

## 🤝 Elastic MCP Integration

REUNION uses **Elastic Cloud** as its core search and data layer:

- **Index**: `reunion_cases` — 15 carefully crafted demo cases covering child separation, tribal communities, unidentified persons, and reunited cases
- **Multi-field search**: searches across `name`, `description`, `distinguishing_marks`, `state`, `tags` with field boosting
- **Nested sightings**: each case stores sighting history as nested Elastic documents
- **Geo-point fields**: location coordinates for proximity-based search
- **Status filtering**: filter by `active_search`, `matched_pending_consent`, `reunited`, `unidentified`

The Elastic index is the single source of truth — the AI tools read from it, write sightings to it, and update case status through it.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Elastic Cloud account (free trial)
- Groq API key (free)

### Installation

```bash
git clone https://github.com/akankshamuthyala/reunion-agent.git
cd reunion-agent
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file:
```
ELASTIC_URL=https://your-deployment.es.region.cloud.es.io
ELASTIC_API_KEY=your_elastic_api_key
GROQ_API_KEY=your_groq_api_key
```

### Load Demo Data

```bash
python elastic_setup.py
```

This creates the `reunion_cases` index and loads 15 demo cases.

### Run the App

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🧪 Demo Aadhaar Numbers

Use these to test the consent wall and verification system:

| Number | Role |
|--------|------|
| `1234 5678 9012` | Family member |
| `9876 5432 1098` | NGO worker |
| `1111 2222 3333` | Institution staff |
| `9999 8888 7777` | Admin |

---

## 📁 Project Structure

```
reunion-agent/
├── app.py                  # Main Streamlit application
├── elastic_setup.py        # Elastic index setup and data loader
├── gemini_tools.py         # AI tool functions
├── reunion_demo_cases.json # 15 demo missing person cases
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 🎯 Hackathon Track

Submitted to: **Elastic Track** — REUNION-Hackathon (Google Cloud + Partners)

**Why Elastic?**
- Elastic is the core data and search layer
- Full-text search across case descriptions and distinguishing marks
- Nested document structure for sighting history
- Geo-point fields for location-based search
- The consent wall status is managed through Elastic case status fields

---

## 💡 5 Safety Layers

1. **Aadhaar Verification** — Identity verified before filing or reporting
2. **Consent Wall** — Both parties must consent before contact
3. **NGO Mediation** — Dual verification required (family + NGO)
4. **Access Tiers** — 4-tier system based on documentation availability
5. **Autonomy Protocol** — Adults can choose not to be found

---

## 🏆 Impact

- 300,000+ people go missing in India every year
- Tribal communities with zero documentation are the most vulnerable
- Long-duration cases (10+ years) have near-zero resolution rates
- REUNION's consent wall prevents re-traumatisation and misuse

---

## 👩‍💻 Built By

**Akanksha Muthyala**

Built with ❤️ for the REUNION Hackathon 2026

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
