"""Lightweight headline sentiment — shared by Polygon and Tavily providers."""


def sentiment_from_text(text: str) -> float:
    positive = {"beat", "raise", "growth", "surge", "record", "buy", "strong", "gain", "rally", "up"}
    negative = {"miss", "cut", "fall", "drop", "weak", "loss", "risk", "probe", "lawsuit", "selloff", "down"}
    words = set(text.lower().split())
    score = 50.0
    score += 8 * len(words & positive)
    score -= 8 * len(words & negative)
    return max(5.0, min(95.0, score))
