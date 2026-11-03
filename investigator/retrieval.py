"""Small, deterministic BM25 retriever. No embeddings or vector database claims."""
import hashlib
import math
import re
from collections import Counter
from pathlib import Path


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


class RunbookIndex:
    def __init__(self, directory=None):
        directory = directory or Path(__file__).parent / "runbooks"
        self.chunks = []
        for path in sorted(Path(directory).glob("*.md")):
            content = path.read_text(encoding="utf-8")
            title = content.splitlines()[0].lstrip("# ")
            for section in content.split("\n## ")[1:]:
                heading, _, body = section.partition("\n")
                text = f"{title}\n{heading}\n{body.strip()}"
                chunk_id = f"{path.stem}:{hashlib.sha256(text.encode()).hexdigest()[:10]}"
                self.chunks.append({"id": chunk_id, "source": path.name,
                                    "title": title, "section": heading,
                                    "text": text, "terms": Counter(tokens(text))})
        if not self.chunks:
            raise ValueError("Runbook collection is empty")
        self.avg_length = sum(sum(c["terms"].values()) for c in self.chunks) / len(self.chunks)

    def search(self, query, limit=3):
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("query must contain 1..1000 characters")
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError("limit must be an integer from 1 to 5")
        terms = set(tokens(query))
        results = []
        for chunk in self.chunks:
            score = 0.0
            length = sum(chunk["terms"].values())
            for term in terms:
                frequency = chunk["terms"].get(term, 0)
                if not frequency:
                    continue
                df = sum(term in c["terms"] for c in self.chunks)
                idf = math.log(1 + (len(self.chunks) - df + .5) / (df + .5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / self.avg_length))
            if score > 0:
                results.append({k: v for k, v in chunk.items() if k != "terms"} | {"score": round(score, 4)})
        return sorted(results, key=lambda r: (-r["score"], r["id"]))[:limit]
