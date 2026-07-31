"""End-to-end verification: DuplicateDetector (ONNX) on the 50-pair benchmark
with startup timing. Uses the real production class and real fastembed model."""
import os
import sys
import time
from pathlib import Path

os.environ["GIIPS_TANGLISH_MODEL"] = "0"

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
sys.path.insert(0, str(Path(__file__).parent.parent))

import psutil

proc = psutil.Process(os.getpid())
baseline = proc.memory_info().rss / 1024 / 1024
print(f"Baseline RSS: {baseline:.1f} MB")

from benchmark_tanglish import PAIRS
from duplicate_detection.engine import DuplicateDetector, DUP_CONF_THRESHOLD
from duplicate_detection.engine import _FallbackDuplicateDetector

print(f"Threshold under test: {DUP_CONF_THRESHOLD}")

# ── Jaccard path timing (old default) ───────────────────────────────
t0 = time.time()
jaccard_det = _FallbackDuplicateDetector()
jaccard_ctor = time.time() - t0
t0 = time.time()
j_scores = []
for title_a, title_b, is_dup, cat, same_loc in PAIRS:
    a = {"title": title_a, "description": "", "lat": 11.0168, "lon": 76.9558, "category": cat}
    b = {"title": title_b, "description": "", "lat": 11.0168, "lon": 76.9558, "category": cat}
    _, conf = jaccard_det.detect_duplicates(a, [b])
    j_scores.append((is_dup, conf))
jaccard_time = time.time() - t0

def f1(scores, thresh):
    tp = sum(1 for gt, s in scores if gt and s > thresh)
    fp = sum(1 for gt, s in scores if not gt and s > thresh)
    fn = sum(1 for gt, s in scores if gt and s <= thresh)
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0, prec, rec, tp, fp, fn

jf1, jp, jr, *_ = f1(j_scores, DUP_CONF_THRESHOLD)
print(f"\nJaccard: ctor {jaccard_ctor*1000:.1f}ms, 50 detects {jaccard_time*1000:.0f}ms, "
      f"F1@{DUP_CONF_THRESHOLD}={jf1:.3f} (P={jp:.3f} R={jr:.3f})")

# ── ONNX path timing ────────────────────────────────────────────────
t0 = time.time()
det = DuplicateDetector()
onnx_ctor = time.time() - t0
print(f"DuplicateDetector() ctor (ONNX): {onnx_ctor*1000:.1f}ms")

candidates_pool = [{
    "title": t, "description": "", "lat": 11.0168, "lon": 76.9558,
    "category": c, "incident_id": f"inc-{i}",
} for i, (t, _, _, c, _) in enumerate(PAIRS)]

# cold: first detect triggers model load
t0 = time.time()
det.detect_duplicates(candidates_pool[0], candidates_pool[:10])
cold_secs = time.time() - t0
after_cold = proc.memory_info().rss / 1024 / 1024
print(f"First detect (cold model load): {cold_secs:.1f}s | RSS now {after_cold:.1f} MB "
      f"(+{after_cold - baseline:.0f} vs baseline)")

# warm: full benchmark through the real class
t0 = time.time()
scores = []
for title_a, title_b, is_dup, cat, same_loc in PAIRS:
    a = {"title": title_a, "description": "", "lat": 11.0168, "lon": 76.9558, "category": cat}
    b = {"title": title_b, "description": "", "lat": 11.0168, "lon": 76.9558, "category": cat}
    _, conf = det.detect_duplicates(a, [b])
    scores.append((is_dup, conf))
warm_time = time.time() - t0

f1_onnx, p, r, tp, fp, fn = f1(scores, DUP_CONF_THRESHOLD)
print(f"50 detects (warm): {warm_time*1000:.0f}ms total, {warm_time/50*1000:.0f}ms each")
print(f"ONNX F1@{DUP_CONF_THRESHOLD}={f1_onnx:.3f} (P={p:.3f} R={r:.3f} TP={tp} FP={fp} FN={fn})")

final = proc.memory_info().rss / 1024 / 1024
print(f"\nFinal RSS: {final:.1f} MB")
print(f"Framework+model delta: {after_cold - baseline:.0f} MB (includes benchmark data)")
print(f"Startup tradeoff: Jaccard near-instant vs ONNX cold load {cold_secs:.1f}s (cached model)")
