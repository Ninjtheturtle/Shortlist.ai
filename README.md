# 🧠 Shortlist.ai

**Shortlist.ai** is a fully automated AI hiring pipeline that ranks resumes by meaning, conducts voice interviews using LLMs, and generates a recruiter-ready shortlist—all without manual screening.

---

## ⚙️ Architecture Overview

**Shortlist.ai** is built as a modular, cloud-ready system:

- **Backend**: Python Flask REST API containerized with Docker, using Supabase for user auth and Postgres data storage
- **LLM Integration**: Gemini Pro used for transcript analysis, follow-up generation, and candidate scoring
- **Voice Interface**: Real-time bidirectional interviews conducted via Twilio Voice
- **Semantic Engine**: Embedding-based resume–JD matching using cosine similarity on vector representations
- **Dashboard**: Recruiter-facing React frontend to display shortlists, interview transcripts, and scores (in progress)

---

## 🧠 Core AI Modules

- **Semantic Matching**: Transforms resumes and job descriptions into embeddings and selects top matches by vector similarity
- **AI Interviewer**: Voice calls generate job-specific, adaptive follow-up questions using LLM prompt chaining
- **Scoring Algorithm**: Combines similarity score, LLM-assessed verbal response quality, and background check results into a 10-point scale

---

## 🔐 Compliance & Data Governance

- **GDPR**: All user data is encrypted at rest and processed with opt-in consent. Deletion and access logs are audit-tracked.
- **FCRA**: Integrated background check workflows follow U.S. federal compliance standards including adverse action protocol
- **Security**: Access control enforced via Supabase RLS. All endpoints secured with token-based auth. Audit logs enabled for traceability.

---

## 📈 Deployment & Scalability

- **Containers**: Dockerized backend with Flask and NGINX/Gunicorn for horizontal scalability
- **Database**: Supabase/Postgres with real-time update triggers
- **Modular Scaling**: Services designed for incremental rollout (resume parsing, scoring, voice interviews)

---

## 💼 Recruiter Workflow

1. Upload job description → vector embedding created
2. Resume batch ingested → top 10 candidates selected via semantic filtering
3. Voice interviews scheduled → AI conducts interview with LLM prompts
4. Responses analyzed → candidates scored and ranked
5. Recruiter receives dashboard of top candidates with transcript & score

---

## 🚀 MVP Status

The MVP includes:
- Resume–JD semantic matcher
- Voice interview system with adaptive follow-ups
- LLM scoring + ranking engine
- Self-serve recruiter dashboard (in development)

---

## 📌 Roadmap

- [x] Core LLM integration + scoring
- [x] Voice infrastructure (Twilio)
- [ ] Frontend dashboard (React)
- [ ] Analytics module for hiring bias tracking
- [ ] SOC 2 preparation

---
