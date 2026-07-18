"""
Test photo duplicate/fraud detection:
  - Same image uploaded twice → should flag "possible_duplicate_submission"
  - Slightly cropped/resized copy → should still flag via pHash
  - Two genuinely different images → should NOT flag
"""
import io
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from storage import compute_phash, hamming_distance, PHASH_HAMMING_THRESHOLD


def make_test_image(draw_type: str = "solid", size=(200, 200)):
    """Create an in-memory test image simulating a complaint photo.

    draw_type:
      'pothole'  — gray circle on dark background (simulates a pothole photo)
      'garbage'  — scattered colored dots on gray (simulates garbage heap)
      'street'   — dark circles on gray (simulates street light at night)
      'solid'    — simple solid color (for edge case testing)
    """
    from PIL import Image, ImageDraw
    if draw_type == "solid":
        img = Image.new("RGB", size, (100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    img = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(img)
    if draw_type == "pothole":
        draw.ellipse([30, 30, size[0]-30, size[1]-30], fill=(80, 80, 80), outline=(150, 150, 150), width=4)
        for _ in range(10):
            x, y = __import__('random').randint(40, size[0]-40), __import__('random').randint(40, size[1]-40)
            draw.ellipse([x-3, y-3, x+3, y+3], fill=(200, 200, 200))
    elif draw_type == "garbage":
        import random
        for _ in range(80):
            x, y = random.randint(0, size[0]), random.randint(0, size[1])
            c = (random.randint(50, 255), random.randint(30, 200), random.randint(20, 150))
            r = random.randint(2, 6)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=c)
    elif draw_type == "street":
        draw.ellipse([60, 60, 140, 140], fill=(255, 255, 200), outline=(200, 200, 100), width=3)
        draw.rectangle([95, 140, 105, 200], fill=(60, 60, 60))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_cropped_resized(base_data: bytes):
    """Create a slightly cropped variant.
    Simulates a user cropping ~2% off each edge — realistic for re-framing.
    """
    from PIL import Image
    img = Image.open(io.BytesIO(base_data))
    w, h = img.size
    pct = 0.02
    cropped = img.crop((int(w*pct), int(h*pct), int(w*(1-pct)), int(h*(1-pct))))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return buf.getvalue()


def make_recompressed(base_data: bytes, quality: int = 50):
    """Re-compress image at lower JPEG quality."""
    from PIL import Image
    img = Image.open(io.BytesIO(base_data))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


passed = 0
failed = 0


PASS_SYM = "[PASS]"
FAIL_SYM = "[FAIL]"

def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        print(f"  {PASS_SYM} {name}")
        passed += 1
    else:
        print(f"  {FAIL_SYM} {name} -- {detail}")
        failed += 1


print("=" * 60)
print("PHOTO DUPLICATE DETECTION — TEST SUITE")
print("=" * 60)

# ── Test 1: Same image twice ────────────────────────────────────────────
print("\n[Test 1] Same image uploaded twice")
img_a = make_test_image("pothole", (200, 200))
hash_a1 = compute_phash(img_a)
hash_a2 = compute_phash(img_a)
check("Non-empty hash", bool(hash_a1), f"got empty hash")
check("Identical hashes for same bytes", hash_a1 == hash_a2,
      f"{hash_a1} != {hash_a2}")
check("Same image -> Hamming distance = 0",
      hamming_distance(hash_a1, hash_a2) == 0,
      f"distance = {hamming_distance(hash_a1, hash_a2)}")

# ── Test 2: Cropped/resized copy ────────────────────────────────────────
print("\n[Test 2] Cropped and resized copy (simulates same pothole, different angle/crop)")
img_b = make_test_image("pothole", (300, 300))
img_b_variant = make_cropped_resized(img_b)
hash_b1 = compute_phash(img_b)
hash_b2 = compute_phash(img_b_variant)
dist = hamming_distance(hash_b1, hash_b2)
check("Cropped variant has non-empty hash", bool(hash_b2), "got empty hash")
check(f"Cropped variant within threshold ({dist} <= {PHASH_HAMMING_THRESHOLD})",
      dist <= PHASH_HAMMING_THRESHOLD,
      f"distance {dist} > threshold {PHASH_HAMMING_THRESHOLD}")

# ── Test 3: Re-compressed (lower quality JPEG) ──────────────────────────
print("\n[Test 3] Re-compressed at lower quality (simulates re-compressed upload)")
img_c = make_test_image("pothole", (250, 250))
img_c_jpeg = make_recompressed(img_c, quality=30)
hash_c1 = compute_phash(img_c)
hash_c2 = compute_phash(img_c_jpeg)
dist = hamming_distance(hash_c1, hash_c2)
check("Re-compressed variant has non-empty hash", bool(hash_c2), "got empty hash")
check(f"Re-compressed within threshold ({dist} <= {PHASH_HAMMING_THRESHOLD})",
      dist <= PHASH_HAMMING_THRESHOLD,
      f"distance {dist} > threshold {PHASH_HAMMING_THRESHOLD}")

# ── Test 4: Different images -> should NOT match ────────────────────────
print("\n[Test 4] Two genuinely different complaint photos (pothole vs garbage)")
img_d1 = make_test_image("pothole", (200, 200))
img_d2 = make_test_image("garbage", (200, 200))
hash_d1 = compute_phash(img_d1)
hash_d2 = compute_phash(img_d2)
dist = hamming_distance(hash_d1, hash_d2)
check("Different photos have different hashes", hash_d1 != hash_d2,
      f"hashes identical: {hash_d1}")
check(f"Different photos exceed threshold ({dist} > {PHASH_HAMMING_THRESHOLD})",
      dist > PHASH_HAMMING_THRESHOLD,
      f"distance {dist} <= threshold {PHASH_HAMMING_THRESHOLD} - false positive!")

# ── Test 5: More distinct content ──────────────────────────────────────
print("\n[Test 5] Street light photo vs garbage photo")
img_e1 = make_test_image("street", (200, 200))
img_e2 = make_test_image("garbage", (200, 200))
hash_e1 = compute_phash(img_e1)
hash_e2 = compute_phash(img_e2)
dist = hamming_distance(hash_e1, hash_e2)
check("Different content has different hashes",
      hash_e1 != hash_e2, f"identical: {hash_e1}")
check("Different content exceeds threshold",
      dist > PHASH_HAMMING_THRESHOLD,
      f"distance {dist}")

# ── Test 6: Empty / invalid input ──────────────────────────────────────
print("\n[Test 6] Edge cases")
hash_empty = compute_phash(b"")
check("Empty bytes returns empty string", hash_empty == "", f"got non-empty: {hash_empty}")
hash_invalid = compute_phash(b"not an image at all!!!!")
check("Invalid bytes → empty hash", hash_invalid == "", f"got non-empty: {hash_invalid}")

# ── Summary ─────────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed:
    print("SOME TESTS FAILED — review details above")
    sys.exit(1)
else:
    print("ALL TESTS PASSED ✅")
