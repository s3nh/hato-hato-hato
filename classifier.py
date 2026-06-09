import re
import numpy as np
from sentence_transformers import SentenceTransformer

TOPICS = [
    "pricing and billing",
    "technical support",
    "product features",
    "onboarding and setup",
    "security and privacy",
    "integrations",
    "roadmap and future features",
]

# Keyword fast-path: if a message clearly matches, skip the model entirely
KEYWORD_MAP: dict[str, list[str]] = {
    "pricing and billing":       ["price", "cost", "invoice", "subscription", "refund", "billing", "charge"],
    "technical support":         ["bug", "error", "broken", "crash", "not working", "issue", "fix"],
    "product features":          ["feature", "how do i", "how to", "can it", "does it support"],
    "onboarding and setup":      ["setup", "install", "getting started", "first time", "configure"],
    "security and privacy":      ["password", "2fa", "gdpr", "data", "breach", "permission", "access"],
    "integrations":              ["api", "webhook", "zapier", "connect", "integration", "plugin"],
    "roadmap and future features": ["roadmap", "when will", "planned", "upcoming", "release"],
}

class TopicClassifier:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        # Encode all topics once at startup — never repeated
        self.topic_embeddings = self.model.encode(
            TOPICS, normalize_embeddings=True, show_progress_bar=False
        )

    def _keyword_match(self, text: str) -> tuple[str, float] | None:
        lower = text.lower()
        for topic, keywords in KEYWORD_MAP.items():
            if any(re.search(rf"\b{kw}\b", lower) for kw in keywords):
                return topic, 1.0
        return None

    def classify(self, content: str) -> tuple[str, float]:
        # Fast path: keyword hit (~0ms)
        keyword_result = self._keyword_match(content)
        if keyword_result:
            return keyword_result

        # Slow path: model inference (~20ms on CPU)
        embedding = self.model.encode(
            [content], normalize_embeddings=True, show_progress_bar=False
        )
        scores = (embedding @ self.topic_embeddings.T)[0]
        best_idx = int(np.argmax(scores))
        return TOPICS[best_idx], float(scores[best_idx])


# Singleton — model loads once, stays in memory
_instance: TopicClassifier | None = None

def classify_message(content: str) -> tuple[str, float]:
    global _instance
    if _instance is None:
        _instance = TopicClassifier()
    return _instance.classify(content)
