"""Module with NLP helper functions."""

# fmt: off
signal_words = {
    "NL": [
        "de", "het", "een", "geen", "ja", "nee", "niet", "wel",
        "voor", "achter", "tegen", "op", "onder", "naar", "en",
        "hallo", "je", "jij", "hij", "zij", "wij", "jullie", "ons",
    ],
    "EN": [
        "the", "it", "a", "none", "yes", "no", "not",
        "for", "up", "down", "to", "too", "and", "that",
        "hello", "he", "she", "it", "you", "us", "ours",
    ]
}
# fmt: on


def detect_language(text):
    """Detect language by counting common words.

    Returns
    -------
    dict
        Hits per language.
    """
    max_hits = 0
    max_lang = None
    for lang, words in signal_words.items():
        hits = len(
            [word for word in text.lower().split() if word in words]
        )
        if hits > max_hits:
            max_hits = hits
            max_lang = lang

    return max_lang
