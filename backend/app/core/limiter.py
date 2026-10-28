from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance. In automated test suite runs (PYTEST_CURRENT_TEST),
# rate limiting is enabled but generous so it doesn't flake standard tests,
# while protecting live production endpoints against runaway LLM billings / DoS.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"], enabled=True)
