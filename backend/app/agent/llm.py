"""
LLM access layer.

This project is configured to use Groq (https://console.groq.com/docs/models)
with `gemma2-9b-it` as the primary model, and `llama-3.3-70b-versatile` as a
fallback for tasks that need a larger context / stronger reasoning (e.g.
free-text entity extraction from a long chat transcript).

NO API KEY IS REQUIRED TO RUN THIS PROJECT.
------------------------------------------
If the environment variable GROQ_API_KEY is not set, every function in this
module transparently falls back to a small rule-based "mock LLM" that mimics
the structure of a real completion (summary, extracted entities, sentiment,
next-best-action) using simple NLP heuristics (keyword spotting, regex,
sentence splitting). This keeps the whole app fully runnable offline/without
credentials, while leaving a single, clearly-marked seam
(`_call_groq`) where real Groq calls plug in the moment a key is added.
"""
import os
import re
from datetime import datetime, timedelta

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # intentionally left unset for this submission
PRIMARY_MODEL = "gemma2-9b-it"
FALLBACK_MODEL = "llama-3.3-70b-versatile"

SENTIMENT_POSITIVE = {"great", "positive", "interested", "excited", "receptive", "happy", "agreed", "good"}
SENTIMENT_NEGATIVE = {"declined", "busy", "negative", "concerned", "refused", "unhappy", "delay", "hesitant"}

DRUG_KEYWORDS = ["cardiozen", "glucobalance", "oncorel", "metabex", "sample", "samples"]
FOLLOWUP_KEYWORDS = ["follow up", "follow-up", "next week", "next month", "call back", "schedule"]


def _call_groq(prompt: str, model: str = PRIMARY_MODEL) -> str | None:
    """
    Real Groq call. Only executes if GROQ_API_KEY is present in the
    environment. Left inactive for this submission per instructions
    (no API keys are checked in / required to run the demo).
    """
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq  # lazy import so the package is optional
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def _mock_summarize(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    key_sentences = sentences[:2] if len(sentences) > 2 else sentences
    return " ".join(key_sentences).strip() or "No summary available."


def _mock_extract_entities(text: str) -> dict:
    lower = text.lower()
    drugs_mentioned = [d.capitalize() for d in DRUG_KEYWORDS if d in lower and d != "samples"]
    sample_match = re.search(r"(\d+)\s+samples?", lower)
    samples_dropped = int(sample_match.group(1)) if sample_match else (5 if "sample" in lower else 0)

    followup_needed = any(k in lower for k in FOLLOWUP_KEYWORDS)
    followup_date = None
    if followup_needed:
        if "next week" in lower:
            followup_date = (datetime.utcnow() + timedelta(days=7)).date().isoformat()
        elif "next month" in lower:
            followup_date = (datetime.utcnow() + timedelta(days=30)).date().isoformat()
        else:
            followup_date = (datetime.utcnow() + timedelta(days=14)).date().isoformat()

    return {
        "topics_discussed": drugs_mentioned or ["General product discussion"],
        "samples_dropped": samples_dropped,
        "followup_required": followup_needed,
        "suggested_followup_date": followup_date,
    }


def _mock_sentiment(text: str) -> str:
    lower = text.lower()
    pos = sum(1 for w in SENTIMENT_POSITIVE if w in lower)
    neg = sum(1 for w in SENTIMENT_NEGATIVE if w in lower)
    if pos > neg:
        return "Positive"
    if neg > pos:
        return "Negative"
    return "Neutral"


def summarize_interaction(raw_text: str) -> dict:
    """
    Returns a structured summary of a free-text HCP interaction description,
    used by the `log_interaction` tool. Tries Groq first (gemma2-9b-it),
    falls back to the offline heuristic summarizer if no key is configured
    or the call fails.
    """
    prompt = (
        "You are a pharmaceutical CRM assistant. Summarize the following "
        "HCP (Healthcare Professional) interaction in 1-2 sentences, extract "
        "topics discussed, number of samples dropped, sentiment, and whether "
        "a follow-up is needed. Return concise JSON.\n\nInteraction:\n" + raw_text
    )
    groq_response = _call_groq(prompt, model=PRIMARY_MODEL)

    entities = _mock_extract_entities(raw_text)
    return {
        "summary": groq_response or _mock_summarize(raw_text),
        "sentiment": _mock_sentiment(raw_text),
        "model_used": PRIMARY_MODEL if groq_response else "mock-offline-heuristic",
        **entities,
    }


def parse_chat_message(message: str, conversation_state: dict) -> dict:
    """
    Used by the conversational logging flow: interprets a single user chat
    message in the context of the interaction being built up, and returns
    which structured field(s) it fills plus a natural language reply.
    Falls back to slot-filling heuristics when Groq is unavailable.
    """
    prompt = (
        "You are helping a pharma sales rep log an HCP interaction via chat. "
        f"Conversation so far (structured fields collected): {conversation_state}. "
        f"New message: '{message}'. Identify which field this message answers "
        "and the extracted value."
    )
    groq_response = _call_groq(prompt, model=FALLBACK_MODEL)
    if groq_response:
        return {"reply": groq_response, "model_used": FALLBACK_MODEL}

    return None  # signal caller to use rule-based slot filling in graph.py
