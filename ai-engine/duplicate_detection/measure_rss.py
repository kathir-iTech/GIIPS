"""Measure actual RSS memory of Morgan-Tanglish-v7 using psutil."""
import os
import sys
import time
import psutil
import numpy as np

# Record baseline
proc = psutil.Process(os.getpid())
baseline = proc.memory_info().rss / 1024 / 1024
print(f"Baseline RSS (before import): {baseline:.1f} MB")

from sentence_transformers import SentenceTransformer

after_import = proc.memory_info().rss / 1024 / 1024
print(f"After sentence-transformers import: {after_import:.1f} MB (+{after_import - baseline:.1f})")

t0 = time.time()
model = SentenceTransformer("vishnu-n/Morgan-Tanglish-v7")
load_time = time.time() - t0

after_load = proc.memory_info().rss / 1024 / 1024
model_mem = after_load - baseline
print(f"After model load: {after_load:.1f} MB (+{after_load - after_import:.1f})")
print(f"Total model memory (RSS delta): {model_mem:.1f} MB")
print(f"Load time: {load_time:.1f}s")

# Warm up
model.encode(["test"])

# Measure single latency
latencies = []
for _ in range(20):
    t0 = time.time()
    model.encode(["machi road la periya kuzhi vehicles ellam damage aagudhu"])
    latencies.append((time.time() - t0) * 1000)
print(f"Single inference: {np.mean(latencies):.1f}ms avg ({min(latencies):.1f}min / {max(latencies):.1f}max)")

pairs = [
    ("machi road la periya kuzhi, vehicles ellam damage aagudhu",
     "bro road la valiya pothole, cars ellam kettu poguthu"),
    ("street light eriyala, night la total darkness",
     "enna da street light off eruku, night la romba iruttu"),
    ("garbage van varala, 2 weeks ah garbage collect pannala",
     "enna garbage collector varadha, 2 weeks ayiduchu trash ah collect pannama"),
    ("water pipe leak agudhu, main road la vellam",
     "tanni pipe vituduchi, road full ah water"),
    ("pothole on the road near the school",
     "garbage not collected in our street"),
    ("water supply problem, no water today",
     "no electricity, power cut since morning"),
]

from sklearn.metrics.pairwise import cosine_similarity
for a, b in pairs:
    ea = model.encode([a]); eb = model.encode([b])
    sim = cosine_similarity(ea, eb)[0][0]
    lbl = "DUP" if sim > 0.65 else "DIST"
    print(f"  {lbl} sim={sim:.3f}  | {a[:50]}")

after_all = proc.memory_info().rss / 1024 / 1024
print(f"\nFinal RSS: {after_all:.1f} MB")
print(f"\n-- RECOMMENDATION --")
print(f"Model uses ~{model_mem:.0f} MB RSS.")
print(f"Estimate app overhead: ~100 MB (uvicorn + db + redis)")
print(f"Total: ~{model_mem + 100:.0f} MB vs Render free tier 512 MB limit")
if model_mem + 100 < 512:
    print(f"FITS ({model_mem + 100} < 512)")
else:
    print(f"OVER LIMIT by {model_mem + 100 - 512} MB")
