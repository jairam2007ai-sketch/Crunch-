"""Small in-memory rate limiters. Per process: fine for one server, swap for Redis if you scale out."""
import threading
import time
from collections import defaultdict, deque

from .config import get_settings


class RateLimiter:
    def __init__(self, max_hits: int, window_seconds: float):
        self.max_hits = max_hits
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls = 0

    def hit(self, key: str) -> bool:
        """Record a hit; False when the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            self._calls += 1
            if self._calls % 5000 == 0:  # forget idle keys now and then so memory stays small
                for k in [k for k, q in self._hits.items() if not q or now - q[-1] > self.window]:
                    del self._hits[k]
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_hits:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = RateLimiter(max_hits=8, window_seconds=300)            # one address guessing one account
login_ip_limiter = RateLimiter(max_hits=40, window_seconds=300)        # one address trying many accounts
login_account_limiter = RateLimiter(max_hits=20, window_seconds=900)   # many addresses on one account
setup_limiter = RateLimiter(max_hits=10, window_seconds=600)
ai_limiter = RateLimiter(max_hits=30, window_seconds=60)               # AI models can cost money
api_limiter = RateLimiter(max_hits=get_settings().api_requests_per_minute, window_seconds=60)  # every API call


def reset_all() -> None:
    for lim in (login_limiter, login_ip_limiter, login_account_limiter, setup_limiter, ai_limiter, api_limiter):
        lim.reset()
