import uuid
from dataclasses import dataclass, field
from rapidfuzz.fuzz import token_set_ratio   # better than ratio for short chat msgs

SIMILARITY_THRESHOLD = 65   # 0–100; tune this — lower = bigger buckets
MERGE_THRESHOLD      = 80   # if two centroids are this similar, merge buckets


@dataclass
class Bucket:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    centroid: str = ""            # representative message for the bucket
    members: list[str] = field(default_factory=list)
    message_ids: list[str] = field(default_factory=list)

    def add(self, message_id: str, content: str):
        self.members.append(content)
        self.message_ids.append(message_id)
        # Update centroid to the most central member (highest avg similarity)
        self.centroid = _best_centroid(self.members)

    @property
    def size(self) -> int:
        return len(self.members)

    def similarity_to(self, text: str) -> float:
        return token_set_ratio(self.centroid, text)


def _best_centroid(members: list[str]) -> str:
    """Pick the member with the highest average similarity to all others."""
    if len(members) == 1:
        return members[0]
    best, best_score = members[0], -1.0
    for candidate in members:
        avg = sum(token_set_ratio(candidate, m) for m in members) / len(members)
        if avg > best_score:
            best, best_score = candidate, avg
    return best


class FuzzyBucketManager:
    def __init__(
        self,
        similarity_threshold: int = SIMILARITY_THRESHOLD,
        merge_threshold: int = MERGE_THRESHOLD,
    ):
        self.buckets: list[Bucket] = []
        self.sim_threshold = similarity_threshold
        self.merge_threshold = merge_threshold

    # ------------------------------------------------------------------
    # Core: assign a message to the best bucket, or create a new one
    # ------------------------------------------------------------------
    def add_message(self, message_id: str, content: str) -> Bucket:
        best_bucket, best_score = self._find_best(content)

        if best_bucket and best_score >= self.sim_threshold:
            best_bucket.add(message_id, content)
            target = best_bucket
        else:
            # No close bucket found — start a new one
            new_bucket = Bucket(centroid=content)
            new_bucket.add(message_id, content)
            self.buckets.append(new_bucket)
            target = new_bucket

        # Opportunistically try to merge similar buckets
        self._try_merge()

        return target

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_best(self, text: str) -> tuple[Bucket | None, float]:
        if not self.buckets:
            return None, 0.0
        scored = [(b, b.similarity_to(text)) for b in self.buckets]
        return max(scored, key=lambda x: x[1])

    def _try_merge(self):
        """Merge pairs of buckets whose centroids are very similar."""
        merged = True
        while merged:
            merged = False
            for i, a in enumerate(self.buckets):
                for j, b in enumerate(self.buckets):
                    if i >= j:
                        continue
                    if token_set_ratio(a.centroid, b.centroid) >= self.merge_threshold:
                        # Merge b into a
                        a.members.extend(b.members)
                        a.message_ids.extend(b.message_ids)
                        a.centroid = _best_centroid(a.members)
                        self.buckets.pop(j)
                        merged = True
                        break
                if merged:
                    break

    # ------------------------------------------------------------------
    # Queue analytics — same interface as before
    # ------------------------------------------------------------------
    def queue_status(self) -> list[dict]:
        return sorted(
            [
                {
                    "bucket_id": b.id,
                    "centroid": b.centroid,
                    "size": b.size,
                    "saturated": b.size >= 10,
                }
                for b in self.buckets
            ],
            key=lambda x: x["size"],
            reverse=True,
        )

    def suggest_alternatives(self, current_bucket_id: str, top_n: int = 3) -> list[dict]:
        """Return least-queued buckets that are NOT the current one."""
        return [
            s for s in self.queue_status()
            if s["bucket_id"] != current_bucket_id
        ][:top_n]
