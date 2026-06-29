# JUDGE_QUESTIONS.md

## Technical Judge Questions & Answers

### Q1: How do you handle cases where two complaints sound similar but are about different incidents?
**A**: We use semantic similarity thresholding. The model is trained to recognize nuanced differences. If the similarity score is below the strict threshold, they are kept as separate incidents.

### Q2: What if the AI classifies a complaint incorrectly?
**A**: Our system supports human-in-the-loop overrides. The incident UI allows officers to reclassify the incident, which can be fed back into the model to improve future accuracy.

### Q3: How is the priority score calculated? Is it transparent?
**A**: Yes. The score is a weighted sum of cluster size, age, category risk, and location proximity. The dashboard provides a breakdown of these factors so officials understand *why* an incident is ranked high.

### Q4: How does this scale to a million complaints?
**A**: Our backend uses FastAPI for high-throughput asynchronous processing and FAISS (Facebook AI Similarity Search) or optimized vector indexing for efficient semantic lookups, ensuring sub-second response times even at high scale.

### Q5: Why SQLite? Isn't it slow?
**A**: For a municipality-level prototype, SQLite is sufficient and highly portable. However, the architecture is fully ORM-compliant (SQLAlchemy), making it easy to migrate to PostgreSQL for enterprise production deployment.

*(... and so on ...)*
