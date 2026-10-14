import json
import pytest
from ai_daily_briefing.evaluator import evaluate_with_ollama


def test_ollama_evaluator_accepts_only_four_boolean_criteria_and_summary():
    def post(url, body):
        assert body["model"] == "qwen3-hermes:8b"
        assert body["format"]["required"] == ["criteria", "summary", "central_ai"]
        assert "https://" not in body["messages"][1]["content"]
        return {"message": {"content": json.dumps({"criteria": {
            "novelty": True, "rigor": False, "ecosystem_relevance": True,
            "reproducibility": False}, "summary": "Un método de agentes.", "central_ai": True})}}
    item = {"kind": "paper", "title": "Agent method", "abstract": "A comparison with baseline.",
            "url": "https://example.org/a"}
    assert evaluate_with_ollama(item, "qwen3-hermes:8b", post=post)["criteria"]["novelty"] is True


def test_ollama_evaluator_rejects_unbounded_hallucinated_output():
    item = {"kind": "paper", "title": "A", "abstract": "B"}
    with pytest.raises(ValueError):
        evaluate_with_ollama(item, "qwen3-hermes:8b", post=lambda url, body: {
            "message": {"content": '{"summary":"' + ("a" * 700) + '","criteria":{}}'}})

def _assessed_paper(summary):
    return {"message": {"content": json.dumps({"criteria": {
        "novelty": False, "rigor": False, "ecosystem_relevance": False,
        "reproducibility": False}, "summary": summary, "central_ai": True})}}

def test_evaluator_removes_model_character_count_annotation():
    item = {"kind": "paper", "title": "Language model", "abstract": "A full abstract."}
    result = evaluate_with_ollama(item, "qwen3:4b", post=lambda url, body:
                                  _assessed_paper("El estudio presenta resultados. (237 caracteres)"))
    assert result["summary"] == "El estudio presenta resultados."

def test_evaluator_removes_count_annotation_with_trailing_period():
    item = {"kind": "news", "title": "Language model", "abstract": "A full article."}
    def post(url, body):
        return {"message": {"content": json.dumps({"criteria": {
            "economic_impact": False, "deployment": False,
            "competitive_disruption": False, "source_verifiability": True},
            "summary": "El modelo mejora la inferencia local. (240 caracteres).",
            "central_ai": True})}}
    assert evaluate_with_ollama(item, "qwen3:4b", post=post)["summary"] == "El modelo mejora la inferencia local."

def test_evaluator_rejects_unfinished_summary_before_count_annotation():
    item = {"kind": "paper", "title": "Language model", "abstract": "A full abstract."}
    with pytest.raises(ValueError, match="incomplete assessment summary"):
        evaluate_with_ollama(item, "qwen3:4b", post=lambda url, body:
                             _assessed_paper("El estudio no termina la oración (240 caracteres)."))

def test_evaluator_rejects_unfinished_summary_before_it_reaches_report():
    item = {"kind": "paper", "title": "Language model", "abstract": "A full abstract."}
    with pytest.raises(ValueError, match="incomplete assessment summary"):
        evaluate_with_ollama(item, "qwen3:4b", post=lambda url, body:
                             _assessed_paper("Los resultados mejoran y con cuatro ciclos mejora"))

def test_evaluator_does_not_use_a_schema_length_that_clips_mid_sentence():
    item = {"kind": "paper", "title": "Language model", "abstract": "A full abstract."}
    def post(url, body):
        assert "maxLength" not in body["format"]["properties"]["summary"]
        assert "máximo 240 caracteres" in body["messages"][1]["content"]
        assert "termina con punto" in body["messages"][1]["content"]
        return _assessed_paper("Un método verificable.")
    assert evaluate_with_ollama(item, "qwen3:4b", post=post)["summary"] == "Un método verificable."

def test_evaluator_prefers_short_sentences_but_does_not_cut_complete_ones():
    item = {"kind": "paper", "title": "Language model", "abstract": "A full abstract."}
    summary = "El trabajo presenta " + "resultados verificables y acotados " * 8 + "en modelos."
    assert 240 < len(summary) <= 400
    def post(url, body):
        prompt = body["messages"][1]["content"]
        assert "idealmente máximo 240 caracteres" in prompt
        assert "límite duro de 400 caracteres" in prompt
        return _assessed_paper(summary)
    assert evaluate_with_ollama(item, "qwen3:4b", post=post)["summary"] == summary
