from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Com REDIS_URL, o rate-limit é compartilhado entre todos os workers do gunicorn
# e sobrevive a reinícios. Sem, cai para memória (por worker).
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=settings.redis_url or "memory://",
)
