from regex_classifier import classify_regex
from fuzzy_buckets import FuzzyBucketManager

fuzzy = FuzzyBucketManager(similarity_threshold=65, merge_threshold=80)

def process_message(message_id: str, content: str) -> dict:
    # 1. Try regex first (free, instant)
    regex_result = classify_regex(content)

    if regex_result.bucket:
        # Confident enough — use the hard label as bucket key
        bucket = fuzzy.add_message(message_id, regex_result.bucket)
        source = "regex"
    else:
        # No regex hit — let fuzzy matching decide / create a bucket
        bucket = fuzzy.add_message(message_id, content)
        source = "fuzzy"

    status = fuzzy.queue_status()
    saturated_buckets = [s for s in status if s["saturated"]]

    return {
        "message_id":    message_id,
        "bucket_id":     bucket.id,
        "bucket_label":  bucket.centroid,   # human-readable centroid
        "source":        source,
        "queue_depth":   bucket.size,
        "saturated":     bucket.size >= 10,
        "alternatives":  fuzzy.suggest_alternatives(bucket.id) if bucket.size >= 10 else [],
    }
