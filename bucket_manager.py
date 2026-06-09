import redis
import json
from dataclasses import dataclass
from typing import Optional

BUCKET_THRESHOLD = 10       # max questions per topic before it's "saturated"
WINDOW_SECONDS   = 300      # sliding 5-min window

@dataclass
class QueueStatus:
    topic: str
    count: int
    is_saturated: bool
    suggested_topics: list[str]

class BucketManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.r = redis.from_url(redis_url)

    def _key(self, topic: str) -> str:
        return f"chat:bucket:{topic.replace(' ', '_')}"

    def add_message(self, topic: str, message_id: str) -> QueueStatus:
        key = self._key(topic)
        pipe = self.r.pipeline()
        pipe.zadd(key, {message_id: __import__("time").time()})
        # remove entries outside the sliding window
        pipe.zremrangebyscore(key, 0, __import__("time").time() - WINDOW_SECONDS)
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SECONDS + 60)
        _, _, count, _ = pipe.execute()

        is_saturated = count >= BUCKET_THRESHOLD
        suggested = self.get_suggested_topics(exclude=topic) if is_saturated else []

        return QueueStatus(
            topic=topic,
            count=count,
            is_saturated=is_saturated,
            suggested_topics=suggested,
        )

    def get_all_counts(self) -> dict[str, int]:
        import time
        now = time.time()
        counts = {}
        for topic in __import__("classifier").TOPICS:
            key = self._key(topic)
            # clean stale entries first
            self.r.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
            counts[topic] = self.r.zcard(key)
        return counts

    def get_suggested_topics(self, exclude: str, top_n: int = 3) -> list[str]:
        counts = self.get_all_counts()
        return [
            t for t, _ in sorted(counts.items(), key=lambda x: x[1])
            if t != exclude
        ][:top_n]
