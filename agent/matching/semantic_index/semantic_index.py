from sentence_transformers import SentenceTransformer
from constants.constants import SEARCH_LIMIT
from helpers.helpers import cosine_similarity, semantic_chunk
from custom_types.custom_types import Document

# semantic indexing class with chunking
class SemanticIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)
        self.documents = None
        self.docmap = {}
        self.chunk_embeddings = None
        self.chunk_metadata = None

    # generate an embedding using the model for a text
    def generate_embedding(self, text: str):
        # check if the text is empty
        if text.strip() == "":
            raise ValueError("text to be embedded is empty")
        embeddings = self.model.encode([text])
        return embeddings[0]

    # build embeddings for the documents
    def build_chunk_embeddings(self, documents: list[Document]):
        self.documents = documents
        # lists to keep chunks and chunk metedata
        chunks = []
        chunk_metadata = []

        # iterate over the documents
        for i in range(len(documents)):
            document = documents[i]
            # keep the docmap current so chunks can always be hydrated back
            # to their document through the stable document_id
            self.docmap[document.id] = document
            # if document content is empty move to the next iteration
            if document.content == "":
                continue

            # create chunks from the document contents
            curr_chunks = semantic_chunk(document.content, 4, 1)
            # iterate over the chunks
            for j in range(len(curr_chunks)):
                # add curr_chunk to the chunks
                chunks.append(curr_chunks[j])
                # create chunk metada
                metadata = {
                        "document_id": document.id,
                        "chunk_index": j,
                        "total_chunks": len(curr_chunks),
                        }
                # add chunk metadata to chunk metadata
                chunk_metadata.append(metadata)

        # create embeddings from the chunks
        self.chunk_embeddings = self.model.encode(chunks)
        # assign chunk metadata
        self.chunk_metadata = chunk_metadata

        return self.chunk_embeddings

    # semantic chunk search
    def search_chunks(self, query: str, limit: int = SEARCH_LIMIT):
        # make sure chunk embeddings exists
        if self.chunk_embeddings is None:
            raise ValueError("chunk embedings is none")

        # make sure chunk metadata exists
        if self.chunk_metadata is None:
            raise ValueError("chunk metadata is none")

        # if the documents do not exist
        if self.documents is None:
            raise ValueError("documents is none")

        # generate an embedding from the query
        query_embedding = self.generate_embedding(query)

        # document similarity_scores, and which chunk index produced each one
        document_scores = {}
        document_best_chunk = {}
        # iterate over the chunks
        for i in range(len(self.chunk_embeddings)):
            # create a similarity score between the query embedding and current chunk embedding
            similarity_score = cosine_similarity(query_embedding, self.chunk_embeddings[i])
            # get chunk metadata
            metadata = self.chunk_metadata[i]
            document_id = metadata["document_id"]
            # if the document score does not exist, or the current chunk scores
            # higher than the previous best chunk for this document, update both
            if document_id not in document_scores or document_scores[document_id] < similarity_score:
                document_scores[document_id] = similarity_score
                document_best_chunk[document_id] = i

        # get the top documents using the limit
        top_documents = sorted(document_scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
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
            result = {
                    "id": document.id,
                    "content": document.content,
                    "score": round(score, 4),
                    "metadata": metadata,
                    }
            results.append(result)

        return results
