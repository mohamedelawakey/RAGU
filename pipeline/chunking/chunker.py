from . import get_logger, Config
from ..cleaning import Cleaner

logger = get_logger("text_splitter.module")


class TextSplitter:
    @staticmethod
    def text_split(
        text,
        chunk_size=Config.CHUNK_SIZE,
        max_chunk_size=Config.MAX_CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP
    ):
        """
        Split and clean the input text into ordered chunks using configured separators, target and maximum sizes, and an overlap.
        
        Parameters:
            text (str): Input text to split; blank or falsy input yields an empty list. The text is cleaned before splitting.
            chunk_size (int): Preferred maximum size (in characters) for chunks.
            max_chunk_size (int): Hard maximum size (in characters) a chunk may reach.
            chunk_overlap (int): Number of characters to overlap between adjacent chunks.
        
        Returns:
            list[str]: Ordered list of text chunks produced from the input.
        """
        if not text or not text.strip():
            return []

        text = Cleaner.clean(text)

        chunks = TextSplitter._recursive_split(
            text,
            Config.SEPARATORS,
            chunk_size,
            max_chunk_size,
            chunk_overlap
        )

        logger.info(f"Text split into {len(chunks)} chunks.")
        return chunks

    @staticmethod
    def _recursive_split(
        text,
        separators,
        chunk_size,
        max_chunk_size,
        chunk_overlap
    ):
        """
        Recursively split text into chunks using a prioritized list of separators while respecting size and overlap constraints.
        
        Chooses the first separator from `separators` that appears in `text` (searching in priority order), splits the text by that separator, and builds chunks that try to stay within `chunk_size` but may grow up to `max_chunk_size`. Segments longer than `chunk_size` are either further split by lower-priority separators (recursively) or sliced into fixed-size pieces. Adjacent chunks preserve `chunk_overlap` characters of overlap at their boundaries.
        
        Parameters:
        	text (str): Input text to split.
        	separators (Sequence[str]): Ordered separators from highest to lowest priority; empty string as a separator means split into characters.
        	chunk_size (int): Preferred maximum size for chunks; chunks at or below this size are grouped when possible.
        	max_chunk_size (int): Absolute maximum size for any chunk; when a potential chunk exceeds this, it is force-split or rolled into the next chunk according to algorithm rules.
        	chunk_overlap (int): Number of characters to overlap between consecutive chunks.
        
        Returns:
        	List[str]: Ordered list of text chunks (whitespace-trimmed) that cover the input text with the specified sizing and overlap.
        """
        if not text:
            return []

        final_chunks = []

        separator = separators[-1]
        new_separators = []
        for i, s in enumerate(separators):
            if s in text:
                separator = s
                new_separators = separators[i+1:]
                break

        if separator != "":
            splits = text.split(separator)
        else:
            splits = list(text)

        current_chunk = ""
        for s in splits:
            if len(s) > chunk_size:
                if current_chunk:
                    final_chunks.append(current_chunk.strip())
                    current_chunk = ""

                if new_separators:
                    recursed_chunks = TextSplitter._recursive_split(
                        s,
                        new_separators,
                        chunk_size,
                        max_chunk_size,
                        chunk_overlap
                    )
                    if recursed_chunks:
                        final_chunks.extend(recursed_chunks)
                        last_chunk = recursed_chunks[-1]
                        overlap_start = max(0, len(last_chunk) - chunk_overlap)
                        current_chunk = last_chunk[overlap_start:]
                else:
                    start = 0
                    while start < len(s):
                        end = min(start + chunk_size, len(s))
                        final_chunks.append(s[start:end].strip())
                        if end >= len(s):
                            break
                        start = end - chunk_overlap

            else:
                potential_chunk = (current_chunk + separator + s) if current_chunk else s

                if len(potential_chunk) <= chunk_size:
                    current_chunk = potential_chunk
                elif len(potential_chunk) <= max_chunk_size:
                    final_chunks.append(potential_chunk.strip())

                    overlap_start = max(0, len(potential_chunk) - chunk_overlap)
                    current_chunk = potential_chunk[overlap_start:]
                else:
                    if current_chunk:
                        final_chunks.append(current_chunk.strip())
                        overlap_start = max(0, len(current_chunk) - chunk_overlap)
                        current_chunk = current_chunk[overlap_start:] + separator + s
                    else:
                        current_chunk = s

        if current_chunk and current_chunk.strip():
            final_chunks.append(current_chunk.strip())

        return final_chunks
