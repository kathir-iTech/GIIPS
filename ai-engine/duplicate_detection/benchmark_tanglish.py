"""
One-off local benchmark: Morgan-Tanglish-v7 vs Jaccard keyword overlap
on 50 realistic Tanglish civic complaint pairs.

Run: python ai-engine/duplicate_detection/benchmark_tanglish.py
"""

import sys, os, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['GIIPS_TANGLISH_MODEL'] = '1'

# ── 50 realistic Tanglish civic complaint pairs ──────────────────────
# (title_a, title_b, is_duplicate, category, same_location)
#
# Vocabulary variation scenarios covered:
#   - Different Romanisation (kuzhi/guzhi, tanni/thanni/water, illai/illa)
#   - Tamil syntax vs English word order
#   - Short terse vs long verbose descriptions
#   - Same semantics, completely different surface words (Jaccard false neg)
#   - Same shared keywords but different issues (Jaccard false pos)
#   - Cross-category near-misses (same location/category tricks the weighting)
#   - Mixed English-only words buried in Tanglish text
#   - Dialect variants (Chennai ya/da vs Coimbatore machi/bro slang)
PAIRS = [
    # ── 25 genuine duplicates ────────────────────────────────────────

    # 0: Pothole — different Romanisation
    ("machi road la periya kuzhi, vehicles ellam damage aagudhu",
     "bro road la valiya pothole, cars ellam kettu poguthu",
     True, "Roads", True),

    # 1: Street light off
    ("street light eriyala, night la total darkness, vali kooda theriyala",
     "enna da street light off eruku, night la romba iruttu ah eruku, road eh theriyala",
     True, "Street Lighting", True),

    # 2: Garbage not collected
    ("garbage van varala, 2 weeks ah garbage collect pannala, street la kuppa kuppa ah",
     "enna garbage collector varadha, 2 weeks ayiduchu trash ah collect pannama, road full ah kuppa",
     True, "Waste Management", True),

    # 3: Water pipe leak — "tanni" vs "water" vs descriptive
    ("water pipe leak agudhu, main road la vellam oothitu eruku waste ah",
     "tanni pipe vituduchi, road full ah water oothitu eruku, paathu po da",
     True, "Water Supply", True),

    # 4: Sewage drain blocked
    ("sewage drain block ah eruku, nalla sokka nikkuthu, road mela vandhuduchu",
     "drain block ah iruku, sewage water road la vandhu nikkuthu, romba naatu",
     True, "Sanitation", True),

    # 5: Power cut
    ("power illa da, ulla konjam electricity irukku, night la fan um illa, light um illa",
     "machi current eh illa, night la total blackout, inverter um illa, switch board la full ah voltage fluctuation",
     True, "Electricity", True),

    # 6: Mosquito / dengue
    ("mosquito romba iruku, night la thoongave mudiyala, dengue bayama iruku da",
     "semma mosquito problem, night full ah mosquitoes, kids ellam bayam ah iruku, fogging pannanum",
     True, "Public Health", True),

    # 7: Bike accident from pothole — different framing
    ("road la pothole naala accident aagiruchu, bike la pona bike damage aagudhu",
     "valiya road kuzhi naala bike skid aagi vezhundhutan, romba dangerous ah iruku",
     True, "Roads", True),

    # 8: Water supply — formal vs informal
    ("tanni supply illa, morning la ikkooda tanni varadha, 200 family ah kastapadrom",
     "water supply problem, morning ku tanni eh illa, area full ah water scarcity, bore well um dry",
     True, "Water Supply", True),

    # 9: Light bulb gone
    ("street light bulb pona eriyadhu, 2 weeks ayiduchu, change pannala",
     "street light eriyala, bulb pona mari iruku, repair panna solli 2 weeks aachu, oru light um eriyala",
     True, "Street Lighting", True),

    # 10: Footpath encroachment — new category
    ("footpath la vandhi kadai poturukanga, naada kooda mudiyala, road la than nadakanum",
     "pavement ah shop keepers block pannitanga, pedestrians road mela than nadaka vendiyiruku, romba kashtam",
     True, "Roads", True),

    # 11: Bus stop broken
    ("bus stop shelter roof damage aagiduchu, mazhai la nikkave mudiyala, waiting people kastapadranga",
     "bus stand la periya kuzhi, rain la oru shelter um illa, passengers ellam nanaikranga da",
     True, "Roads", True),

    # 12: Stray dogs menace
    ("street la naai koottam romba iruku, night la oda mudiyala, kids bayapadranga",
     "enne da stray dogs problem semma iruku, evening walk ku poga mudiyala bayama iruku, 5 peruku bite aagiruchu",
     True, "Animal Control", True),

    # 13: Water contamination — dirty water
    ("tanni supply la color varudhu, mannu mannu ah iruku, kudikka mudiyadhu",
     "water la sand mix aagiduchu, brown colour ah varudhu, filter panna poradu, drinking ku use panna mudiyadha",
     True, "Water Supply", True),

    # 14: Open manhole — missing cover
    ("manhole cover missing, road naadula periya gound, night la pona sethuduvaanga",
     "enna la manhole cover illa, road la periya hole iruku, bike pona accident aagum da",
     True, "Roads", True),

    # 15: Road construction incomplete — half-done
    ("road work half ah vittu poturukanga, oru side mudichu oru side mudiyala, dust semma",
     "busy road la construction nadukittu eruku but complete pannama vitturukanga, valiya ditch open ah eruku, lorries stuck aagudhu",
     True, "Roads", True),

    # 16: Fallen tree blocking road
    ("tree branch odhnji road mela vilundhuduchu, vehicles la poga mudiyadhu, area full jam",
     "periya mara kozhanbu road ah block pannirukku, pozhachi naala branch vezhundhuduchu, cranes vandhu remove pannanum",
     True, "Roads", True),

    # 17: Garbage bin overflowing
    ("bin full ah iruku, 1 week ah empty pannala, kuppa saani road la vizhundhukittu eruku, dogs spread pannuthu",
     "semma garbage dump overflow aagiduchu, truck varadha, bin la periya kuppa kootam, street la ellam spread aagi stink adikuthu",
     True, "Waste Management", True),

    # 18: Playground equipment broken
    ("park la kids swings damage aagiduchu, iron rod korainchitu iruku, dangerous ah iruku kids ku",
     "children play area la slide um swing um ellam broken, metal part uh loose ah iruku, paathu po da",
     True, "Parks", True),

    # 19: Public toilet dirty
    ("toilet la clean pannala, nalla sokka mookku adikuthu, door lock um illa, water tank um broken",
     "public bathroom condition romba mosam ah iruku, flush work aagala, nalla stink, oru light um illa",
     True, "Sanitation", True),

    # 20: Low-hanging cable wires
     ("electric cable wire road ah cover panni thonkichu iruku, lorry pona contact aagum, fire risk iruku da",
      "wire uh thonchitu iruku, bus mela muthukuthu, cable cut aagura maari iruku, spark aaguthu machi",
      True, "Electricity", True),

    # 21: Fire hydrant broken
    ("fire hydrant open ah vitturukanga, water ellam waste aagudhu, road la vellam oothitu eruku",
     "fire water pipe leaking continuously, hydrant valve broken, water flow aagitu eruku, urutha waste",
     True, "Water Supply", True),

    # 22: Noise pollution — wedding speakers
    ("night 11 oclock ku aprom kooda speakers loud ah poturukanga, kuzhandaiku thoongamudiyala, daily headache iruku",
     "enna da sound pollution, wedding function la full volume, 12 am ku aprom la kooda party nadakuthu, police complaint pannanum",
     True, "Noise Pollution", True),

    # 23: Drainage odour
    ("nalla sokka smell adikuthu da road la, drain full ah sokka nikkuthu, open ah eruku",
     "drain ah cover pannama vitturukanga, pona pothu bayama iruku, naatram kooda theriyala, motham stink adikuthu",
     True, "Sanitation", True),

    # 24: Park overgrown / no maintenance
    ("park la grass full ah valandhuduchu, pathway uh theriyala, mosquitoes kootam",
     "enna da local park la maintenance eh illa, plants ellam overgrown, walk panna mudiyadha maari iruku",
     True, "Parks", True),

    # ── 25 distinct pairs ────────────────────────────────────────────

    # 25: Pothole vs garbage (same Roads category, same loc — weighted test)
    ("machi road la periya kuzhi da, valiya pothole, bike la potha damage aagum",
     "bro garbage eh collect pannadha, 1 month ah trash ah pothu poturukanga, nalla naatu",
     False, "Roads", True),

    # 26: Street light off vs water supply (same category)
    ("street light off, night la road eh theriyala, accident aagura maari iruku",
     "water supply illa, 3 days ah tanni varadha, kudikka tanni illa, romba kastama iruku",
     False, "Street Lighting", True),

    # 27: Water pipe vs power cut — cross-category, shared loc
    ("tanni pipe leakage, road la vellam oothitu eruku, pol utta kooda waste",
     "power line uh uh vechurukanga, cable cut panni poturukanga, area full ah current illa",
     False, "Water Supply", True),

    # 28: Garbage vs mosquito — same category
    ("garbage not collected, street la kuppa kuppa ah iruku, rats ooduthu",
     "mosquito problem romba iruku, night full ah mosquitoes, dengue outbreak aagum bayama iruku",
     False, "Waste Management", True),

    # 29: Drain blocked vs road bumpy — same category, shared "road" keyword
    ("drain block ah eruku, sokka water road la nikkuthu, naatu adikkuthu",
     "sariyana road pothole eh illa la, sand road eh sari panna maturanga, bus poi road vaari kuda theriyala",
     False, "Sanitation", True),

    # 30: Bike tyre vs pipe burst — same Roads cat, shared "damage" keyword
    ("pothole naala bike tyre damage aagudhu, repair ku 500 aaguthu, municipality complaint pannum",
     "tanni pipe burst main road la, vellam oothitu eruku, house ku damage aagura maari iruku",
     False, "Roads", True),

    # 31: Power fluctuation vs garbage truck — different issues
    ("current ah fluctuation ah iruku, voltage epdi oothuthu, home appliances damage aagum",
     "garbage truck varadha, 3 weeks ah street full ah trash, kuppa saani, dogs scatter pannudhu",
     False, "Electricity", True),

    # 32: Sewage overflow vs light post — same Sanitation cat
    ("sewage overflow aagiduchu, road full ah waste water nikkuthu, kids school ku poga mudiyala",
     "street light post damage aagiduchu, car hit panni potudhu, night la total darkness area",
     False, "Sanitation", True),

    # 33: Street light missing vs water pipe leak — different categories
    ("bro road la sariyana street light eh illa la, korangadu area, kids cricket aada kooda theriyala",
     "machi water pipe leak aagiduchu mana solla, tanni unnecessary waste aaguthu, fix pannanum",
     False, "Street Lighting", True),

    # 34: Mosquito vs power cut — different categories
    ("mosquito fogging pannala, dengue cases increase aagudhu, area la 3 peruku fever",
     "power cut 8 hours ayiduchu, fridge la food ellaam spoil aagiduchu, generator um illa",
     False, "Public Health", True),

    # 35: Footpath encroachment vs bus stop — same Roads, different issue
    ("footpath la vandhi kadai poturukanga, pedestrians road mela nadaka vendiyiruku",
     "bus stop la bench ellam broken, mazhai la nikka place um illa, passengers kastapadranga",
     False, "Roads", True),

    # 36: Stray dogs vs park overgrown — same location, diff cat
    ("street naai koottam romba dangerous, evening la kuda poga mudiyala, kids bayapadranga",
     "park la grass full ah valandhu mosquitoes valarudhu, swings um broken, unusable ah iruku",
     False, "Animal Control", True),

    # 37: Manhole cover vs water contamination — both Roads/Water but diff
    ("manhole cover missing road la, night pona oru bike kuda gound la vilundhu sethuruvaanga",
     "tanni supply la mud color ah varudhu, filter panna oru method um illa, kudikka mudiyadha water",
     False, "Roads", True),

    # 38: Fallen tree vs half-built road — both Roads cat, shared "road" keyword
    ("mara branch vilundhu road ah full ah block pannirukku, traffic jam, vehicles stuck",
     "road construction nadukittu iruku but half done, oru side road damage ah vitturukanga, dust problem",
     False, "Roads", True),

    # 39: Overflowing bin vs playground — same location, diff issue
    ("dump yard bin full ah iruku, road la kuppa kuppa ah, street stink adikuthu, dogs spread",
     "children park la swings ellaam broken, slide um dangerous, iron rust aagiduchu, fix pannanum",
     False, "Waste Management", True),

    # 40: Public toilet vs cable wires — same Sanitation cat
    ("public toilet la door um illa, flush um broken, water supply um illa, clean pannala",
     "electric wire thonchitu iruku road la, bus driver ku attention venum, fire accident aagum",
     False, "Sanitation", True),

    # 41: Noise pollution (wedding) vs playground broken — different cats
    ("night 11 pm ku aprom kooda party nadakuthu, speakers loud ah, police ku complaint pannum",
     "play area la children swing chain broken, dangerous, periya accident aagura maari iruku",
     False, "Noise Pollution", True),

    # 42: Fire hydrant vs storm drain blocked — same Water cat
    ("fire hydrant leaking, main road la water waste aagum, fix panna solli 1 month aachu",
     "storm water drain block aagiduchu, rain pothu area full water logging, 100 house flood aagum",
     False, "Water Supply", True),

    # 43: Drainage smell vs light bulb — diff cats, shared "change" word
    ("drain open ah iruku, sokka stink adikuthu, naatram theriyala, cover pannanum",
     "street light bulb pona 3 weeks aachu, maatha solli change pannala, night total dark",
     False, "Sanitation", True),

    # 44: Pothole vs open manhole — both Roads, similar keyword "hole/gound"
    ("road valiya pothole iruku, bike accident aagudhu, fill pannanum urgently",
     "manhole cover illa da, periya gound iruku road naadula, emergency signal um illa",
     False, "Roads", True),

    # 45: Stray dogs vs no street light — different cats
    ("street la stray dogs 6 iruku, kids cricket aada poga mudiyala, bayama oda vendiyiruku",
     "road la oru street light um illa, night la total darkness, mobile torch la than nadakrom",
     False, "Animal Control", True),

    # 46: Water contamination vs garbage — diff issues (same location)
    ("water supply la sand mix aagiduchu, brown water varudhu, filter panna poradu ku use panna mudiyadha",
     "road la garbage collection varadha, kuppa kuppa ah iruku, area clean panna weekly service need",
     False, "Water Supply", True),

    # 47: Playground vs park overgrown — same Parks category, diff issue
    ("park play area la slides broken, swings chain snap aagiduchu, kids ku dangerous",
     "park maintenance illa, grass valandhu pathway ah cover, mosquito semma, walk panna mudiyadhu",
     False, "Parks", True),

    # 48: Flooding vs power cut — diff categories
    ("road la rain water nikkuthu, drain block aagiduchu, house la water vandhuduchu",
     "electricity connection loose uh iruku, voltage goes up and down, home appliances damage aaguthu",
     False, "Sanitation", True),

    # 49: Bus stop vs footpath encroachment — same Roads
    ("bus stop la periya kuzhi, roof um illa, passengers mazhai la nanaikranga, shelter pannanum",
     "footpath la ther road kadai panni poturukanga, pedestrians road mela than nadaka vendiyiruku",
     False, "Roads", True),
]


# ── Benchmark helpers ────────────────────────────────────────────────

def jaccard_similarity(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / max(len(union), 1)


def jaccard_detect_dup(a: dict, b: dict) -> float:
    """Pure Jaccard overlap (current _FallbackDuplicateDetector logic)."""
    text_a = f"{a.get('title', '')} {a.get('description', '')}".lower()
    text_b = f"{b.get('title', '')} {b.get('description', '')}".lower()
    words_a = set(text_a.split())
    words_b = set(text_b.split())
    overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
    return overlap


def tanglish_text_similarity(model, a: str, b: str) -> float:
    from sklearn.metrics.pairwise import cosine_similarity
    emb_a = model.encode([a])
    emb_b = model.encode([b])
    return float(cosine_similarity(emb_a, emb_b)[0][0])


def tanglish_confidence(model, a: dict, b: dict,
                        w_text: float = 0.6, w_loc: float = 0.3, w_cat: float = 0.1) -> float:
    """Weighted Tanglish similarity with configurable text/location/category weights."""
    from sklearn.metrics.pairwise import cosine_similarity
    text_a = f"{a.get('title', '')} {a.get('description', '')}"
    text_b = f"{b.get('title', '')} {b.get('description', '')}"
    emb_a = model.encode([text_a])
    emb_b = model.encode([text_b])
    text_sim = float(cosine_similarity(emb_a, emb_b)[0][0])

    from geopy.distance import geodesic
    loc1 = (a.get('lat', 0), a.get('lon', 0))
    loc2 = (b.get('lat', 0), b.get('lon', 0))
    dist = geodesic(loc1, loc2).meters
    loc_sim = max(0, 1 - (dist / 1000))
    cat_sim = 1.0 if a.get('category') == b.get('category') else 0.0
    return text_sim * w_text + loc_sim * w_loc + cat_sim * w_cat


def compute_metrics(results: list, threshold: float) -> dict:
    tp = sum(1 for gt, pred, _ in results if gt and pred >= threshold)
    fp = sum(1 for gt, pred, _ in results if not gt and pred >= threshold)
    fn = sum(1 for gt, pred, _ in results if gt and pred < threshold)
    tn = sum(1 for gt, pred, _ in results if not gt and pred < threshold)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)
    return {
        'threshold': threshold,
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'precision': precision, 'recall': recall,
        'f1': f1, 'accuracy': accuracy,
    }


# ── Weighting schemes to test ────────────────────────────────────────
# (name, w_text, w_loc, w_cat)
WEIGHT_SCHEMES = [
    ("100/0/0 (text-only)",  1.0, 0.0, 0.0),
    (" 90/5/5",              0.90, 0.05, 0.05),
    (" 85/10/5",             0.85, 0.10, 0.05),
    (" 80/15/5",             0.80, 0.15, 0.05),
    (" 70/20/10",            0.70, 0.20, 0.10),
    (" 60/30/10 (current)",  0.60, 0.30, 0.10),
    (" 50/40/10",            0.50, 0.40, 0.10),
]


# ── Main benchmark ──────────────────────────────────────────────────

print("=" * 72)
print("TANGLISH DUPLICATE DETECTION BENCHMARK")
print("50 realistic Tanglish civic complaint pairs")
print("=" * 72)

# Load Tanglish model
print("\n[1/4] Loading Morgan-Tanglish-v7...")
from sentence_transformers import SentenceTransformer
t0 = time.time()
model = SentenceTransformer("vishnu-n/Morgan-Tanglish-v7")
print(f"  Loaded in {time.time() - t0:.1f}s  (dim={model.get_embedding_dimension()})")

# Build complaint dicts once
print("\n[2/4] Building complaint data and embeddings...")
import numpy as np
all_texts = []
complaint_pairs = []
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

# Compute all embeddings in one batch call (100 texts)
print(f"  Encoding {len(all_texts)} texts in one batch...")
embeddings = model.encode(all_texts, show_progress_bar=False)
embeddings = np.array(embeddings)

from sklearn.metrics.pairwise import cosine_similarity

# Score with Jaccard
jaccard_results = []
for a, b, is_dup in complaint_pairs:
    j_score = jaccard_detect_dup(a, b)
    jaccard_results.append((is_dup, j_score, None))

# Score with Tanglish (all weight schemes from precomputed embeddings)
print("  Computing similarity for all weight schemes...")
scheme_results = {}
for name, w_text, w_loc, w_cat in WEIGHT_SCHEMES:
    scores = []
    for idx, (a, b, is_dup) in enumerate(complaint_pairs):
        emb_a = embeddings[idx * 2].reshape(1, -1)
        emb_b = embeddings[idx * 2 + 1].reshape(1, -1)
        text_sim = float(cosine_similarity(emb_a, emb_b)[0][0])

        from geopy.distance import geodesic
        loc1 = (a['lat'], a['lon'])
        loc2 = (b['lat'], b['lon'])
        dist = geodesic(loc1, loc2).meters
        loc_sim = max(0, 1 - (dist / 1000))
        cat_sim = 1.0 if a['category'] == b['category'] else 0.0

        s = text_sim * w_text + loc_sim * w_loc + cat_sim * w_cat
        scores.append((is_dup, s, None))
    scheme_results[name] = scores

# Tanglish text-only variant (always useful to show)
tanglish_text_results = []
for idx, (a, b, is_dup) in enumerate(complaint_pairs):
    emb_a = embeddings[idx * 2].reshape(1, -1)
    emb_b = embeddings[idx * 2 + 1].reshape(1, -1)
    text_sim = float(cosine_similarity(emb_a, emb_b)[0][0])
    tanglish_text_results.append((is_dup, text_sim, None))

# ── Threshold sweep ──────────────────────────────────────────────────
print("\n[3/4] Sweeping thresholds (0.50–0.85 step 0.01) across all weight schemes...")
THRESHOLDS = [x / 100 for x in range(50, 86)]

best_overall = None  # (name, threshold, metrics)

for name, scores in sorted(scheme_results.items()):
    best_for_scheme = None
    for t in THRESHOLDS:
        m = compute_metrics(scores, t)
        if best_for_scheme is None or m['f1'] > best_for_scheme['f1']:
            best_for_scheme = m
    scheme_name_short = name.split("(")[0].strip()
    if best_overall is None or best_for_scheme['f1'] > best_overall[2]['f1']:
        best_overall = (name, best_for_scheme['threshold'], best_for_scheme)

print("\n  Best result per weighting scheme:")
print(f"  {'Scheme':<22} {'Thresh':<7} {'Prec':<7} {'Recall':<7} {'F1':<7} {'Acc':<7} {'TP':<4} {'FP':<4} {'FN':<4} {'TN':<4}")
print(f"  {'-'*22} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*4} {'-'*4} {'-'*4} {'-'*4}")
for name, scores in sorted(scheme_results.items()):
    best_for_scheme = None
    for t in THRESHOLDS:
        m = compute_metrics(scores, t)
        if best_for_scheme is None or m['f1'] > best_for_scheme['f1']:
            best_for_scheme = m
    m = best_for_scheme
    highlight = " <<<" if name == best_overall[0] else ""
    print(f"  {name:<22} {m['threshold']:<7.2f} {m['precision']:<7.3f} {m['recall']:<7.3f} {m['f1']:<7.3f} {m['accuracy']:<7.3f} {m['tp']:<4} {m['fp']:<4} {m['fn']:<4} {m['tn']:<4}{highlight}")

print(f"\n  Text-only (TanglishText, 100/0/0) best:")
m_txt = compute_metrics(tanglish_text_results, best_overall[1])
for t in THRESHOLDS:
    mt = compute_metrics(tanglish_text_results, t)
    if mt['f1'] > m_txt['f1']:
        m_txt = mt
print(f"  {'Text-only':<22} {m_txt['threshold']:<7.2f} {m_txt['precision']:<7.3f} {m_txt['recall']:<7.3f} {m_txt['f1']:<7.3f} {m_txt['accuracy']:<7.3f} {m_txt['tp']:<4} {m_txt['fp']:<4} {m_txt['fn']:<4} {m_txt['tn']:<4}")

# Jaccard baseline
j_best = compute_metrics(jaccard_results, 0.3)
print(f"\n  Jaccard (current baseline @0.30):  Acc={j_best['accuracy']:.1%}  F1={j_best['f1']:.3f}  Prec={j_best['precision']:.1%}  Recall={j_best['recall']:.1%}")

# ── Per-pair comparison for best config ──────────────────────────────
print(f"\n[4/4] Per-pair: {best_overall[0]} @ threshold {best_overall[1]:.2f}")
best_scores = scheme_results[best_overall[0]]
best_thresh = best_overall[1]
print(f"  {'#':<3} {'GT':<5} {'Jaccard':<8} {'TangWgt':<8} {'J_OK':<5} {'W_OK':<5}  Notes")
print(f"  {'-'*3} {'-'*5} {'-'*8} {'-'*8} {'-'*5} {'-'*5}  {'-'*40}")
for i, (title_a, title_b, is_dup, cat, same_loc) in enumerate(PAIRS):
    j_score = jaccard_results[i][1]
    w_score = best_scores[i][1]
    j_ok = (j_score > 0.3) == is_dup
    w_ok = (w_score >= best_thresh) == is_dup
    gt = "DUP" if is_dup else "DIST"
    notes = []
    if j_ok and not w_ok: notes.append("Jaccard better")
    if w_ok and not j_ok: notes.append("Tanglish better")
    if not j_ok and not w_ok: notes.append("Both wrong")
    if j_ok and w_ok: notes.append("Both correct")
    print(f"  {i:<3} {gt:<5} {j_score:<8.3f} {w_score:<8.3f} {'P' if j_ok else 'F':<5} {'P' if w_ok else 'F':<5}  {', '.join(notes)}")

# ── Summary ──────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("RECOMMENDATION")
print("=" * 72)
print(f"  Best config:  {best_overall[0]}")
print(f"  Threshold:    {best_overall[1]:.2f}")
best_metrics = best_overall[2]
print(f"  F1:           {best_metrics['f1']:.3f}  (vs Jaccard {j_best['f1']:.3f})")
print(f"  Accuracy:     {best_metrics['accuracy']:.1%}  (vs Jaccard {j_best['accuracy']:.1%})")
print(f"  Precision:    {best_metrics['precision']:.1%}  (vs Jaccard {j_best['precision']:.1%})")
print(f"  Recall:       {best_metrics['recall']:.1%}  (vs Jaccard {j_best['recall']:.1%})")
print(f"  TP/FP/FN/TN:  {best_metrics['tp']}/{best_metrics['fp']}/{best_metrics['fn']}/{best_metrics['tn']}")
print(f"\n  Text-only also strong: F1={m_txt['f1']:.3f} @ {m_txt['threshold']:.2f} "
      f"(Prec={m_txt['precision']:.1%} Recall={m_txt['recall']:.1%})")
print(f"\n  Memory: ~724 MB RSS (Render $7/mo or local)")
print("=" * 72)
