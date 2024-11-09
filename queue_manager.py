# queue_manager.py
import redis

class QueueManager:
    def __init__(self, redis_host='localhost', redis_port=6379, db=0):
        # Initialize Redis connection
        self.redis_conn = redis.StrictRedis(host=redis_host, port=redis_port, db=db, decode_responses=True)
        self.queue_name = "linkedin_profile_queue"
        self.processed_set = "processed_profiles"  # Track processed URLs

    def enqueue_url(self, url):
        """Add a new URL to the queue if it hasn't been processed."""
        if not self.redis_conn.sismember(self.processed_set, url):
            self.redis_conn.lpush(self.queue_name, url)

    def dequeue_url(self):
        """Pop a URL from the queue for processing."""
        return self.redis_conn.rpop(self.queue_name)

    def mark_processed(self, url):
        """Add a URL to the set of processed URLs."""
        self.redis_conn.sadd(self.processed_set, url)

    def is_processed(self, url):
        """Check if a URL has been processed."""
        return self.redis_conn.sismember(self.processed_set, url)
