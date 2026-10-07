import numpy as np
from sentence_transformers import SentenceTransformer

from matching.constants.constants import (
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TOKENS,
    EMBEDDING_MODEL,
)
from matching.custom_types.custom_types import Document
from matching.helpers.helpers import token_window_chunks

# loaded models, by name -- loading from disk takes seconds, and every
# evaluate_posting() call builds a fresh SemanticIndex. This caches the model
# only; embeddings are still recomputed on every call, per the no-caching
# design (see ../README.md).
_models: dict[str, SentenceTransformer] = {}


def _load_model(model_name: str) -> SentenceTransformer:
    if model_name not in _models:
        _models[model_name] = SentenceTransformer(model_name)
    return _models[model_name]


# semantic indexing class with chunking
class SemanticIndex:
    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model = _load_model(model_name)
        self.documents = None
        self.docmap = {}
        self.chunk_embeddings = None
        self.chunk_metadata = None

    # split a text into model-token windows (see helpers.token_window_chunks)
    def chunk(self, text: str) -> list[str]:
        return token_window_chunks(text, self.model.tokenizer, CHUNK_TOKENS, CHUNK_OVERLAP_TOKENS)

    # embed texts as unit vectors, so a dot product is the cosine similarity
    def embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)

    # build embeddings for the documents
    def build_chunk_embeddings(self, documents: list[Document]):
        self.documents = documents
        # lists to keep chunks and chunk metadata
        chunks = []
        chunk_metadata = []

        for document in documents:
            # keep the docmap current so chunks can always be hydrated back
            # to their document through the stable document_id
            self.docmap[document.id] = document

            curr_chunks = self.chunk(document.content)
            for j, chunk in enumerate(curr_chunks):
                chunks.append(chunk)
                chunk_metadata.append(
                    {
                        "document_id": document.id,
                        "chunk_index": j,
                        "total_chunks": len(curr_chunks),
                    }
                )

        # create embeddings from the chunks
        self.chunk_embeddings = self.embed(chunks)
        self.chunk_metadata = chunk_metadata

        return self.chunk_embeddings

    # semantic chunk search. The query is chunked the same way as the
    # documents -- a whole posting runs past the model's input limit, and
    # embedding it in one piece silently dropped its tail (requirements and
    # nice-to-haves come last). A document's score is its best-matching
    # (query chunk, document chunk) pair: the one place where some part of the
    # posting and some part of the fact line up most closely.
    def search_chunks(self, query: str, limit: int | None = None):
        # make sure chunk embeddings exists
        if self.chunk_embeddings is None:
            raise ValueError("chunk embeddings is none")

        # make sure chunk metadata exists
        if self.chunk_metadata is None:
            raise ValueError("chunk metadata is none")

        # if the documents do not exist
        if self.documents is None:
            raise ValueError("documents is none")

        query_chunks = self.chunk(query)
        if not query_chunks:
            raise ValueError("text to be embedded is empty")
        query_embeddings = self.embed(query_chunks)

        # similarity of every document chunk to its best-matching query chunk
        chunk_scores = (query_embeddings @ self.chunk_embeddings.T).max(axis=0)

        # document similarity scores, and which chunk index produced each one
        document_scores = {}
        document_best_chunk = {}
        for i, similarity_score in enumerate(chunk_scores):
            document_id = self.chunk_metadata[i]["document_id"]
            # if the document score does not exist, or the current chunk scores
            # higher than the previous best chunk for this document, update both
            if (
                document_id not in document_scores
                or document_scores[document_id] < similarity_score
            ):
                document_scores[document_id] = similarity_score
                document_best_chunk[document_id] = i

        # get the top documents using the limit
        # ties broken by document id, so equal scores rank the same every run
        top_documents = sorted(document_scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        # from the top documents create the result that will be sent
        results = []
        for document_id, score in top_documents:
            # resolve chunks back to documents through the stable docmap
            # using document_id - never rely on positional indexes
            document = self.docmap.get(document_id)
            if document is None:
                continue
            # metadata from the specific chunk that produced the winning score
            metadata = self.chunk_metadata[document_best_chunk[document_id]]
            results.append(
                {
                    "id": document.id,
                    "content": document.content,
                    "score": round(float(score), 4),
                    "metadata": metadata,
                }
            )

        return results
