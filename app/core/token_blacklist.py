from redis import Redis
from jose import jwt
from datetime import datetime
from app.core.config import settings


class TokenBlacklist:
    def __init__(self):
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )

    def blacklist_token(self, token: str) -> None:
        """Add a token to the blacklist"""
        try:
            # Decode token to get expiration time
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            # Calculate TTL (time until token expires)
            exp_timestamp = payload['exp']
            current_timestamp = datetime.utcnow().timestamp()
            ttl = int(exp_timestamp - current_timestamp)

            if ttl > 0:
                # Store in Redis with automatic expiration
                self.redis_client.setex(
                    f"blacklist_token:{token}",
                    ttl,
                    "1"
                )
        except jwt.JWTError:
            raise ValueError("Invalid token")

    def is_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted"""
        return self.redis_client.exists(f"blacklist_token:{token}")


# Create a singleton instance
token_blacklist = TokenBlacklist()
