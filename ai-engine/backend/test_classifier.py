import pytest

CATEGORY_KEYWORDS = {
    "Roads": ["pothole", "road", "street"],
    "Water Supply": ["water", "pipe", "leak"],
    "Waste Management": ["garbage", "waste", "trash"],
    "Sanitation": ["sewage", "drain", "blockage"],
    "Street Lighting": ["light", "lamp", "bulb"],
    "Electricity": ["power", "voltage", "transformer"],
    "Public Health": ["health", "mosquito", "dengue"],
}

TEST_TEXTS = {
    "Roads": "A large pothole on the main road near the market entrance is damaging vehicle tires every day.",
    "Water Supply": "The water supply pipe has been leaking for a week with no supply reaching our street.",
    "Waste Management": "Garbage collection has not happened in two weeks and trash is piling up on the street.",
    "Sanitation": "The sewage drain is completely blocked causing overflow of dirty water on the road.",
    "Street Lighting": "The street light near the junction has been flickering for days and is now completely dark.",
    "Electricity": "Power transformer is sparking dangerously after heavy rains and the voltage keeps fluctuating.",
    "Public Health": "Stagnant water is breeding mosquitoes everywhere and there is a risk of dengue outbreak.",
}


class TestClassifier:

    def test_all_seven_categories_return_prediction(self, client):
        for category, text in TEST_TEXTS.items():
            resp = client.post("/classify", json={"text": text})
            assert resp.status_code == 200, f"{category}: {resp.text[:200]}"
            data = resp.json()
            assert data["predicted_category"] == category, (
                f"Expected {category}, got {data['predicted_category']} "
                f"for text: {text[:60]}..."
            )
            assert 0 < data["confidence"] <= 1.0
            assert data["method"] in ("ml_model", "heuristic_fallback", "tamil_keyword_fallback")
            assert len(data["top_predictions"]) >= 1

    def test_classifier_returns_reasonable_confidence(self, client):
        for category, text in TEST_TEXTS.items():
            resp = client.post("/classify", json={"text": text})
            data = resp.json()
            assert data["confidence"] >= 0.3, (
                f"Low confidence {data['confidence']} for {category}: {data['reason']}"
            )

    def test_batch_classify(self, client):
        requests = [{"text": t} for t in TEST_TEXTS.values()]
        resp = client.post("/classify/batch", json=requests)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 7
        assert len(data["results"]) == 7

    def test_heuristic_fallback_method(self, client):
        resp = client.post("/classify", json={"text": "garbage and waste everywhere"})
        data = resp.json()
        assert data["predicted_category"] == "Waste Management"

    def test_classify_empty_text_returns_error(self, client):
        resp = client.post("/classify", json={"text": ""})
        assert resp.status_code == 422
