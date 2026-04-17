from pipeline.reranker.loading_model import LocalRerankerLoader
from utils.logger import get_logger
from pipeline.config import Config
from typing import List, Dict, Any

logger = get_logger("reranker.local")


class LocalReranker:
    @staticmethod
    def rerank(query: str, chunks: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
        try:
            logger.info(
                f"Reranker [LOCAL]: reranking {len(chunks)} chunks "
                f"(top_n={top_n}) using "
                f"'{Config.LOCAL_RERANKER_MODEL}'..."
            )

            model = LocalRerankerLoader.get_model()
            documents = [chunk["text_content"] for chunk in chunks]

            pairs = [[query, doc] for doc in documents]
            scores = model.predict(pairs)

            results = []
            for idx, score in enumerate(scores):
                results.append({
                    "chunk": chunks[idx],
                    "score": float(score)
                })

            results.sort(key=lambda x: x["score"], reverse=True)

            top_results = results[:top_n]

            reranked = []
            for res in top_results:
                original_chunk = res["chunk"]
                reranked.append({
                    "chunk_id": original_chunk["chunk_id"],
                    "rrf_score": original_chunk["score"],
                    "rerank_score": res["score"],
                    "text_content": original_chunk["text_content"],
                    "filename": original_chunk.get("filename", "Unknown")
                })

            logger.info(f"Reranker [LOCAL]: successfully reranked to {len(reranked)} top chunks.")
            return reranked

        except Exception as e:
            logger.exception(f"Reranker [LOCAL]: error during reranking: {e}")
            return chunks
