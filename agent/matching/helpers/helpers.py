import re

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


# only hits the network/prints download noise the first time a resource is
# actually missing, instead of on every import
def _ensure_nltk_data(resource: str, path: str) -> None:
    try:
        nltk.data.find(path)
    except LookupError:
        nltk.download(resource, quiet=True)


_ensure_nltk_data("punkt_tab", "tokenizers/punkt_tab")
_ensure_nltk_data("stopwords", "corpora/stopwords")

# built once at import rather than on every tokenize() call
STOP_WORDS = frozenset(stopwords.words("english"))

# a token counts as a word only if it has at least one letter/digit -- drops
# the JSON punctuation word_tokenize emits for json.dumps'd facts and postings
# ({ } : , and the `` '' quote tokens), which every document and every query
# share, so it only added noise to BM25 scores and lengths
_WORD = re.compile(r"\w")


# helper function to tokenize a string
def tokenize(text: str) -> list[str]:
    tokens = (w.lower() for w in word_tokenize(text))
    return [w for w in tokens if _WORD.search(w) and w not in STOP_WORDS]


# helper function to split a text into overlapping windows of at most
# `size` model tokens, returned as slices of the original text. Windows are
# measured in the embedding model's own tokens (not words or sentences), so no
# chunk can exceed the model's input limit and be silently truncated.
def token_window_chunks(text: str, tokenizer, size: int, overlap: int) -> list[str]:
    if text.strip() == "":
        return []
    if not 0 <= overlap < size:
        raise ValueError(f"overlap must be in [0, size), got size={size} overlap={overlap}")

    # offsets map each token back to its (start, end) character span in text.
    # verbose=False: tokenizing the full text here (only to find window
    # boundaries, never fed to the model) would otherwise log a spurious
    # "longer than the specified maximum sequence length" warning
    offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, verbose=False)[
        "offset_mapping"
    ]
    if not offsets:
        return []

    chunks = []
    step = size - overlap
    for start in range(0, len(offsets), step):
        window = offsets[start : start + size]
        chunks.append(text[window[0][0] : window[-1][1]])
        # the last window already reaches the end of the text
        if start + size >= len(offsets):
            break
    return chunks


# function to calculate rrf score
def calc_rrf_score(rank: int, k: int = 60) -> float:
    return 1 / (rank + k)
