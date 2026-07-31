"""
Benchmark paraphrase-MiniLM-L3-v2 for duplicate detection:
memory usage (RSS deltas) + F1 on the same 50-pair benchmark used for
Morgan-Tanglish-v7 (benchmark_tanglish.py).

Run: python ai-engine/duplicate_detection/benchmark_minilm.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
sys.path.insert(0, str(Path(__file__).parent.parent))

import psutil
import numpy as np

proc = psutil.Process(os.getpid())
baseline = proc.memory_info().rss / 1024 / 1024
print(f"Baseline RSS (interpreter only): {baseline:.1f} MB")

from benchmark_tanglish import PAIRS, jaccard_detect_dup, compute_metrics, WEIGHT_SCHEMES

after_bench_import = proc.memory_info().rss / 1024 / 1024
print(f"After stdlib imports: {after_bench_import:.1f} MB (+{after_bench_import - baseline:.1f})")

t0 = time.time()
from sentence_transformers import SentenceTransformer
import_secs = time.time() - t0
after_st = proc.memory_info().rss / 1024 / 1024
print(f"After sentence-transformers import: {after_st:.1f} MB (+{after_st - after_bench_import:.1f}, {import_secs:.1f}s)")

t0 = time.time()
model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
load_secs = time.time() - t0
after_load = proc.memory_info().rss / 1024 / 1024
model_mem = after_load - after_st
print(f"After model load: {after_load:.1f} MB (+{model_mem:.1f}, {load_secs:.1f}s)")
print(f"  TOTAL framework+model RSS delta: {after_load - after_bench_import:.1f} MB")

print(f"\nModel: dim={model.get_embedding_dimension()}, max_seq_len={model.max_seq_length}")

# ── Build complaint dicts (same as benchmark_tanglish) ──────────────
complaint_pairs = []
all_texts = []
for title_a, title_b, is_dup, cat, same_loc in PAIRS:
    lat_a = lat_b = 11.0168
    lon_a = lon_b = 76.9558
    if not same_loc:
        lat_b = 11.0200
        lon_b = 76.9600
    a = {"title": title_a, "description": "", "lat": lat_a, "lon": lon_a, "category": cat}
    b = {"title": title_b, "description": "", "lat": lat_b, "lon": lon_b, "category": cat}
    complaint_pairs.append((a, b, is_dup))
    all_texts.append(title_a)
    all_texts.append(title_b)

# ── Latency measurement (single-pair encode) ────────────────────────
t0 = time.time()
model.encode(["test sentence"])
warm = time.time() - t0
latencies = []
for _ in range(10):
    t0 = time.time()
    model.encode([all_texts[0]])
    latencies.append((time.time() - t0) * 1000)
print(f"\nLatency: warm-up {warm*1000:.0f}ms, single-text avg {np.mean(latencies):.0f}ms")

# ── Batch encode all 100 texts ───────────────────────────────────────
t0 = time.time()
embeddings = np.array(model.encode(all_texts, show_progress_bar=False))
batch_secs = time.time() - t0
after_encode = proc.memory_info().rss / 1024 / 1024
print(f"Batch encode 100 texts: {batch_secs:.1f}s, RSS now {after_encode:.1f} MB (+{after_encode - after_load:.1f})")

from sklearn.metrics.pairwise import cosine_similarity
from geopy.distance import geodesic

# ── Scores ───────────────────────────────────────────────────────────
jaccard_results = []
for a, b, is_dup in complaint_pairs:
    jaccard_results.append((is_dup, jaccard_detect_dup(a, b), None))

text_scores = []
for idx, (a, b, is_dup) in enumerate(complaint_pairs):
    ea = embeddings[idx * 2].reshape(1, -1)
    eb = embeddings[idx * 2 + 1].reshape(1, -1)
    sim = float(cosine_similarity(ea, eb)[0][0])
    text_scores.append((is_dup, sim, None))

scheme_results = {}
for name, w_text, w_loc, w_cat in WEIGHT_SCHEMES:
    scores = []
    for idx, (a, b, is_dup) in enumerate(complaint_pairs):
        ea = embeddings[idx * 2].reshape(1, -1)
        eb = embeddings[idx * 2 + 1].reshape(1, -1)
        text_sim = float(cosine_similarity(ea, eb)[0][0])
        loc1 = (a['lat'], a['lon'])
        loc2 = (b['lat'], b['lon'])
        dist = geodesic(loc1, loc2).meters
        loc_sim = max(0, 1 - (dist / 1000))
        cat_sim = 1.0 if a['category'] == b['category'] else 0.0
        s = text_sim * w_text + loc_sim * w_loc + cat_sim * w_cat
        scores.append((is_dup, s, None))
    scheme_results[name] = scores

# ── Threshold sweep ──────────────────────────────────────────────────
THRESHOLDS = [x / 100 for x in range(20, 96)]

def best_metrics(results):
    best = None
    for t in THRESHOLDS:
        m = compute_metrics(results, t)
        if best is None or m['f1'] > best['f1']:
            best = m
    return best

j_best = best_metrics(jaccard_results)
t_best = best_metrics(text_scores)

print(f"\n{'Scheme':<24} {'Thresh':<7} {'Prec':<7} {'Recall':<7} {'F1':<7} {'Acc':<7} {'TP':<4} {'FP':<4} {'FN':<4} {'TN':<4}")
print(f"{'-'*24} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*4} {'-'*4} {'-'*4} {'-'*4}")
print(f"{'Jaccard (current)':<24} {j_best['threshold']:<7.2f} {j_best['precision']:<7.3f} {j_best['recall']:<7.3f} {j_best['f1']:<7.3f} {j_best['accuracy']:<7.3f} {j_best['tp']:<4} {j_best['fp']:<4} {j_best['fn']:<4} {j_best['tn']:<4}")
print(f"{'MiniLM text-only':<24} {t_best['threshold']:<7.2f} {t_best['precision']:<7.3f} {t_best['recall']:<7.3f} {t_best['f1']:<7.3f} {t_best['accuracy']:<7.3f} {t_best['tp']:<4} {t_best['fp']:<4} {t_best['fn']:<4} {t_best['tn']:<4}")
for name, scores in sorted(scheme_results.items()):
    m = best_metrics(scores)
    print(f"{name:<24} {m['threshold']:<7.2f} {m['precision']:<7.3f} {m['recall']:<7.3f} {m['f1']:<7.3f} {m['accuracy']:<7.3f} {m['tp']:<4} {m['fp']:<4} {m['fn']:<4} {m['tn']:<4}")

# Per-pair diff for best text-only
print("\nPer-pair text-only cosine (thresh %.2f):" % t_best['threshold'])
for i, (title_a, title_b, is_dup, cat, same_loc) in enumerate(PAIRS):
    j_score = jaccard_results[i][1]
    m_score = text_scores[i][1]
    j_ok = (j_score >= j_best['threshold']) == is_dup
    m_ok = (m_score >= t_best['threshold']) == is_dup
    gt = "DUP" if is_dup else "DIST"
    notes = []
    if j_ok and not m_ok: notes.append("Jaccard better")
    if m_ok and not j_ok: notes.append("MiniLM better")
    if not j_ok and not m_ok: notes.append("Both wrong")
    if j_ok and m_ok: notes.append("Both correct")
    print(f"  {i:<3} {gt:<5} J={j_score:<6.3f} M={m_score:<6.3f} {'P' if j_ok else 'F':<2} {'P' if m_ok else 'F':<2} {', '.join(notes)}")

# ── Final memory summary ─────────────────────────────────────────────
final = proc.memory_info().rss / 1024 / 1024
print(f"\nFinal RSS: {final:.1f} MB")
print(f"\n-- MEMORY SUMMARY (vs Render free tier 512 MB) --")
print(f"Framework+model RSS delta (deps import + model): {after_load - after_bench_import:.0f} MB")
print(f"Full process RSS after encode: {final:.0f} MB")
app_overhead = 100
total = final + app_overhead
print(f"App estimate (uvicorn+db+redis on top of this): ~{app_overhead} MB")
print(f"Projected total: ~{total:.0f} MB vs 512 MB limit -> {'FITS' if total < 512 else 'OVER by %.0f MB' % (total - 512)}")
