# Code-Mixed Tamil-English Classifier for Civic Complaints — Research Report

## Current State

TF-IDF + Logistic Regression trained on English-only NYC 311 data (7 categories), with a Tamil Unicode keyword fallback for pure-Tamil-script input. Covers 0 code-mixed Tanglish.

## Verified Real Models on Hugging Face

### 1. Morgan-Tanglish-v7 — [vishnu-n/Morgan-Tanglish-v7](https://huggingface.co/vishnu-n/Morgan-Tanglish-v7)

| Property | Value |
|---|---|
| **Pipeline** | Sentence Similarity |
| **Library** | sentence-transformers |
| **Params** | 0.1B (118M) |
| **Base model** | paraphrase-multilingual-MiniLM-L12-v2 |
| **License** | Apache 2.0 |
| **Downloads** | 242/mo |
| **Zenodo DOI** | [10.5281/zenodo.20792177](https://doi.org/10.5281/zenodo.20792177) |
| **Training data** | [Tanglish-Corpus-185k](https://huggingface.co/datasets/vishnu-n/Tanglish-Corpus-185k) (186k sentences) |
| **Eval benchmark** | [TanglishSTS](https://huggingface.co/datasets/vishnu-n/TanglishSTS) (325 human-annotated pairs) |
| **Live demo** | [Morgan-Tanglish-Demo](https://huggingface.co/spaces/vishnu-n/Morgan-Tanglish-Demo) |

**Self-reported Spearman:** 0.87 on TanglishSTS. Trained on DravidianCodeMix + YouTube + Reddit Tanglish data using CachedMultipleNegativesRankingLoss + CoSENTLoss.

**Adaptability for civic classification:** This is a sentence embedding model, not a classifier. It can be used as a feature extractor — replace the current TF-IDF vectorizer. You'd train a lightweight classifier (LogisticRegression or MLP) on top of its 384-d embeddings. Best candidate among Tanglish-specific models because it's the only one designed for general-purpose semantic understanding (not hate/offensive detection).

**Limitation per model card:** Formal Tamil native script — use IndicSBERT. Optimised for 6–50 word social media text.

### 2. EmmanuelJoshua/Tanglish-HateSpeech-Model — [link](https://huggingface.co/EmmanuelJoshua/Tanglish-HateSpeech-Model)

| Property | Value |
|---|---|
| **Pipeline** | Text Classification |
| **Params** | 0.3B |
| **Base** | XLM-RoBERTa (architecture inferred from tags) |
| **License** | None specified |
| **Downloads** | 4/mo |
| **arXiv** | 1910.09700 |

**Assessment:** Model card is nearly blank — no class labels, no accuracy/F1, no training data description. Appears to be a hate speech classifier for Tanglish. **Not suitable for civic complaint classification** — it's purpose-built for hate speech detection, its output labels are offensive/non-offensive categories rather than civic departments, and the lack of documentation makes it impossible to assess quality.

### 3. Aru-Niya/tanglish-offensive-lora — [link](https://huggingface.co/Aru-Niya/tanglish-offensive-lora)

| Property | Value |
|---|---|
| **Pipeline** | Text Generation (LoRA adapter) |
| **Base** | Qwen2.5-3B-Instruct |
| **License** | Not specified |
| **Downloads** | 38/mo |
| **Training data** | DravidianCodeMix Tamil-English (44k YouTube comments) |
| **Classes** | 6-class offensive language |
| **Weighted F1** | 0.648 |
| **Macro F1** | 0.252 |

**Assessment:** 6-class offensive language classification. Not suitable for civic categories but demonstrates that DravidianCodeMix data works for Tanglish fine-tuning. Same dataset could be re-annotated for civic categories or used as a starting point.

### 4. seanbenhur/tanglish-offensive-language-identification — [link](https://huggingface.co/seanbenhur/tanglish-offensive-language-identification)

| Property | Value |
|---|---|
| **Pipeline** | Text Classification |
| **Library** | Transformers + ONNX |
| **Base** | BERT (multilingual) |
| **License** | Apache 2.0 |
| **Downloads** | 11/mo |

**Assessment:** Minimal model card ("Coming soon"). Offensive language identification for Tanglish tagged with DravidianCodeMix. Not usable for civic classification without documentation.

### 5. l3cube-pune/tamil-topic-all-doc — [link](https://huggingface.co/l3cube-pune/tamil-topic-all-doc)

| Property | Value |
|---|---|
| **Pipeline** | Text Classification |
| **Params** | 0.2B |
| **Base** | l3cube-pune/tamil-sentence-bert-nli (IndicSBERT) |
| **License** | CC-BY-4.0 |
| **Downloads** | 4/mo |
| **Training data** | L3Cube-IndicNews Corpus |
| **Paper** | [arxiv:2401.02254](https://arxiv.org/abs/2401.02254) |

**Assessment:** Tamil document topic classification for news (sports, business, entertainment, etc.). Trained on formal Tamil script, **not** code-mixed Tanglish. Shows L3Cube-Pune can produce functional Tamil text classifiers — a useful reference but the topic categories don't map to civic complaints and it doesn't handle Romanised Tamil.

### 6. google/muril-base-cased — [link](https://huggingface.co/google/muril-base-cased)

| Property | Value |
|---|---|
| **Pipeline** | Fill-Mask (MLM) |
| **Library** | Transformers (PyTorch, TF, JAX) |
| **Params** | BERT-base |
| **License** | Apache 2.0 |
| **Downloads** | 55k/mo |
| **Languages** | 17 Indian languages including Tamil |
| **Paper** | [arxiv:2103.10730](https://arxiv.org/abs/2103.10730) |

**Tamil transliteration support — verified by published benchmarks:**
- PANX transliterated Tamil F1: 7.00 (vs mBERT 1.04)
- UDPOS transliterated Tamil F1: 58.40 (vs mBERT 24.02)
- XNLI transliterated Hindi accuracy: 68.24 (vs mBERT 39.60)

**Assessment:** The only major model with explicit transliterated Tamil benchmarks published by Google. Pre-trained on transliterated data using the Dakshina dataset. Strong candidate — can be fine-tuned for sequence classification on Tanglish. 61 fine-tuned models exist on Hugging Face. Needs labeled Tanglish complaint data.

### 7. ai4bharat/indic-bert — [link](https://huggingface.co/ai4bharat/indic-bert)

| Property | Value |
|---|---|
| **Pipeline** | Feature Extraction |
| **Architecture** | ALBERT |
| **License** | MIT |
| **Downloads** | 9.9k/mo |
| **Languages** | 12 Indian languages (Tamil included) |
| **Paper** | Findings of EMNLP 2020 |
| **Parameters** | Much fewer than mBERT/XLM-R (ALBERT) |

**Assessment:** Lightweight (ALBERT architecture) but not specifically trained on transliterated/code-mixed data. Has 40 fine-tuned models. Better for formal Tamil script than Tanglish. Less suitable than MuRIL for code-mixed scenarios.

### 8. sugiv/qwen3-8b-tanglish — [link](https://huggingface.co/sugiv/qwen3-8b-tanglish)

| Property | Value |
|---|---|
| **Pipeline** | Text Generation |
| **Params** | 8B |
| **Base** | Qwen3-8B |
| **License** | Apache 2.0 |
| **Downloads** | 112/mo |
| **Training data** | [sugiv/tanglish-pairs-v1](https://huggingface.co/datasets/sugiv/tanglish-pairs-v1) (81k SFT examples) |
| **Cost** | ~$13.36 for training |
| **Metrics** | Single-turn Tanglish authenticity +1.33, helpfulness +1.0 over base |

**Assessment:** Conversational LLM for Tanglish, not a classifier. Too large (8B) for the current backend. Shows the ecosystem maturity — if an 8B Tanglish LLM exists, there's enough data and interest for Tanglish NLP.

## Recommendations

### Approach A — Use Morgan-Tanglish-v7 as Feature Extractor (Quickest)

Replace TF-IDF vectorizer in `classification/train.py` with SentenceTransformer embeddings from Morgan-Tanglish-v7. Keep the LogisticRegression head. This requires:

- ~500 labeled Tanglish civic complaint examples
- Training data: translate existing English complaints to Tanglish via IndicTrans, then augment with real Tanglish social media data
- Compute: CPU only, ~5 min to extract 384-d embeddings for 1k texts

### Approach B — Fine-tune MuRIL for Sequence Classification (Best quality)

Use `google/muril-base-cased` with a classification head. Best transliteration support among major models. Requires more data (~2000 samples) and GPU (T4, ~2-3 hours).

### Approach C — Hybrid Pipeline (Recommended)

Classification pipeline:
1. Script detection (existing `is_tamil_text` function)
2. If pure English → existing TF-IDF classifier
3. If pure Tamil Unicode → existing keyword fallback (or upgrade to l3cube-pune/tamil-topic-all-doc if topics align)
4. If code-mixed Tanglish → Morgan-Tanglish-v7 embeddings + LogisticRegression head

This minimises risk: existing flows stay unchanged, Tanglish handling is additive.

### Data Acquisition

- Convert existing complaint history to Tanglish using IndicTrans transliteration mode
- Augment with DravidianCodeMix dataset (44k Tamil-English YouTube comments from Chakravarthi et al. 2021, verified via Aru-Niya model card)
- Manually annotate 200-500 real Tanglish complaints from GIIPS users
- Synthetic: use sugiv/qwen3-8b-tanglish to generate Tanglish complaint variants from English seed texts

## Data Sources Verified

| Dataset | Source | Size | Tanglish? |
|---|---|---|---|
| DravidianCodeMix | YouTube comments, Chakravarthi et al. 2021 | ~44k Tamil-English | Yes (used by 3 models above) |
| Tanglish-Corpus-185k | [vishnu-n/Tanglish-Corpus-185k](https://huggingface.co/datasets/vishnu-n/Tanglish-Corpus-185k) | 186k sentences | Yes |
| L3Cube-IndicNews | [github.com/l3cube-pune/indic-nlp](https://github.com/l3cube-pune/indic-nlp) | Document-level | No (formal Tamil) |
| sugiv/tanglish-pairs-v1 | [sugiv/tanglish-pairs-v1](https://huggingface.co/datasets/sugiv/tanglish-pairs-v1) | 81k SFT pairs | Yes |

## Key References

- [Morgan-Tanglish-v7](https://huggingface.co/vishnu-n/Morgan-Tanglish-v7) — Vishnu N, 2026, Apache 2.0, Zenodo DOI: 10.5281/zenodo.20792177
- [MuRIL](https://huggingface.co/google/muril-base-cased) — Khanuja et al., 2021, arXiv:2103.10730
- [IndicBERT](https://huggingface.co/ai4bharat/indic-bert) — Kakwani et al., 2020, Findings of EMNLP, MIT License
- [L3Cube-IndicNews](https://arxiv.org/abs/2401.02254) — Mirashi et al., 2024
- [DravidianCodeMix](https://github.com/bharathichezhiyan/DravidianCodeMix-Dataset) — Chakravarthi et al., 2021, FIRE Shared Task
