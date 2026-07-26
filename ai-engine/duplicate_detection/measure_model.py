"""
Measure Morgan-Tanglish-v7 memory footprint and inference latency.
Reports whether it fits on Render's free tier (512 MB RAM).
"""

import sys
import time
import tracemalloc
from pathlib import Path

# Temporarily add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

TANGLISH_PAIRS = [
    # (text_a, text_b, expected_duplicate)
    ("machi road la periya kuzhi, vehicles ellam damage aagudhu",
     "bro road la valiya pothole, cars ellam kettu poguthu",
     True),
    ("street light eriyala, night la total darkness, vali kooda theriyala",
     "enna da street light off ah eruku, night la romba iruttu ah eruku, road eh theriyala",
     True),
    ("garbage van varala, 2 weeks ah garbage collect pannala, street la kuppa kuppa ah",
     "enna garbage collector varadha, 2 weeks ayiduchu trash ah collect pannama",
     True),
    ("water pipe leak agudhu, main road la vellam oothitu eruku",
     "tanni pipe vituduchi, road full ah water oothitu eruku waste ah",
     True),
    ("sewage blockage, sokka drain la sokka nikkuthu, road mela vandhuduchu",
     "drain block ah eruku, sewage water road la vandhu nikkuthu",
     True),
    # Distinct — different complaints
    ("pothole on the road near the school",
     "garbage not collected in our street",
     False),
    ("water supply problem, no water today",
     "no electricity in my area, power cut since morning",
     False),
    # Edge cases — same topic, different complaint
    ("street light broken at junction near bus stop",
     "new street light needed on Church Road, existing light too dim",
     True),
    # English-only (should still work — model covers both)
    ("Large pothole on the main road near the market",
     "A big pothole on the main road damaging vehicle tires",
     True),
    ("Garbage overflowing from the bin on the street corner",
     "Water pipe burst on the highway causing flooding",
     False),
]


def measure_model():
    print("=" * 70)
    print("Morgan-Tanglish-v7 — Memory & Latency Measurement")
    print("=" * 70)

    # Import dependencies
    from sentence_transformers import SentenceTransformer

    # Start memory tracking
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()

    print("\n[1/4] Loading model...")
    t0 = time.time()
    model = SentenceTransformer("vishnu-n/Morgan-Tanglish-v7")
    load_time = time.time() - t0
    after_load = tracemalloc.get_traced_memory()

    dim = model.get_sentence_embedding_dimension()
    max_seq = model.max_seq_length

    print(f"  Load time:     {load_time:.2f}s")
    print(f"  Embedding dim: {dim}")
    print(f"  Max seq len:   {max_seq}")
    print(f"  Memory (current): {after_load[0] / 1024 / 1024:.1f} MB")
    print(f"  Memory (peak):    {after_load[1] / 1024 / 1024:.1f} MB")

    print("\n[2/4] Single inference latency (warm-up)...")
    model.encode(["test"])
    latencies = []
    for i in range(10):
        t0 = time.time()
        model.encode(["machi road la periya kuzhi vehicles ellam damage aagudhu"])
        latencies.append((time.time() - t0) * 1000)
    avg_single = sum(latencies) / len(latencies)
    print(f"  Single inference: {avg_single:.1f} ms avg ({min(latencies):.1f} min, {max(latencies):.1f} max)")

    print("\n[3/4] Batch inference latency...")
    batch_texts = [p[0] for p in TANGLISH_PAIRS]
    t0 = time.time()
    for _ in range(5):
        model.encode(batch_texts)
    avg_batch = ((time.time() - t0) / 5) * 1000
    print(f"  Batch ({len(batch_texts)} texts, 5 runs): {avg_batch:.1f} ms avg")

    print("\n[4/4] Duplicate detection correctness...")
    from sklearn.metrics.pairwise import cosine_similarity
    correct = 0
    for i, (a, b, expected) in enumerate(TANGLISH_PAIRS):
        emb_a = model.encode([a])
        emb_b = model.encode([b])
        sim = cosine_similarity(emb_a, emb_b)[0][0]
        is_dup = sim > 0.65
        match = (is_dup == expected)
        if match:
            correct += 1
        status = "PASS" if match else "FAIL"
        dup_label = "DUP" if is_dup else "DIST"
        exp_label = "DUP" if expected else "DIST"
        print(f"  [{status}] {dup_label} (got) vs {exp_label} (exp) — sim={sim:.3f}")
        if not match:
            print(f"         A: {a[:60]}...")
            print(f"         B: {b[:60]}...")

    accuracy = correct / len(TANGLISH_PAIRS)
    print(f"\n  Duplicate detection accuracy: {correct}/{len(TANGLISH_PAIRS)} = {accuracy:.0%}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    mem_mb = after_load[0] / 1024 / 1024
    peak_mb = after_load[1] / 1024 / 1024
    print(f"  Memory (current): {mem_mb:.1f} MB")
    print(f"  Memory (peak):    {peak_mb:.1f} MB")
    print(f"  Single latency: {avg_single:.1f} ms")
    print(f"  Batch latency:  {avg_batch:.1f} ms (n={len(batch_texts)})")
    print(f"  Accuracy:       {accuracy:.0%}")

    RENDER_LIMIT = 512
    overhead_mb = 100  # estimate for FastAPI + Gunicorn + DB driver + Redis
    total_mb = mem_mb + overhead_mb
    print(f"\n  Render free tier RAM limit: {RENDER_LIMIT} MB")
    print(f"  Estimated total w/ app overhead: {total_mb:.0f} MB")
    if total_mb < RENDER_LIMIT:
        print(f"  ✅ FITS within {RENDER_LIMIT} MB limit ({(1 - total_mb/RENDER_LIMIT)*100:.0f}% headroom)")
    else:
        print(f"  ❌ EXCEEDS {RENDER_LIMIT} MB limit by {total_mb - RENDER_LIMIT:.0f} MB")

    tracemalloc.stop()


if __name__ == "__main__":
    measure_model()
