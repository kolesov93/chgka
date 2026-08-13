"""Opaque in-memory admin token lifecycle."""

from dataclasses import dataclass
import secrets
import time
from typing import Callable, Optional


@dataclass(frozen=True)
class AdminTokenRecord:
    issued_at: float
    expires_at: float


class AdminTokenStore:
    """One-active-token store with a fixed, non-sliding expiry."""

    def __init__(
        self,
        ttl_seconds: int,
        *,
        clock: Callable[[], float] = time.time,
        token_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._records: dict[str, AdminTokenRecord] = {}

    def issue(self) -> str:
        now = self._clock()
        token = self._token_factory()
        self._records.clear()
        self._records[token] = AdminTokenRecord(
            issued_at=now,
            expires_at=now + self._ttl_seconds,
        )
        return token

    def validate(self, token: object) -> bool:
        if not isinstance(token, str) or not token:
            return False
        record = self._records.get(token)
        if record is None:
            return False
        if record.expires_at <= self._clock():
            self._records.pop(token, None)
            return False
        return True

    def revoke(self, token: object) -> None:
        if isinstance(token, str):
            self._records.pop(token, None)

    def clear(self) -> None:
        self._records.clear()

    def expires_at(self, token: str) -> Optional[float]:
        record = self._records.get(token)
        return record.expires_at if record is not None else None

    def __len__(self) -> int:
        return len(self._records)
