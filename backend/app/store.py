"""In-memory persistence for the prototype. Replaced by PostgreSQL later (SDP D-02)."""

import threading

from .schemas import Attempt, CourtPoint, PublishedProfile, Session, TrackSummary

DEMO_PLAYER_ID = "demo-player"  # no auth in the prototype; one player owns everything


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.sessions: dict[str, Session] = {}
            self.attempts: dict[str, list[Attempt]] = {}
            self.tracks: dict[str, TrackSummary] = {}
            # Per-frame court points, in the harness's results.csv shape.
            self.track_points: dict[str, list[CourtPoint]] = {}
            self.artifacts: dict = {}
            # Published profile versions per player, oldest first (FR-15).
            self.profiles: dict[str, list[PublishedProfile]] = {}

    def update(self, session_id: str, **changes) -> Session:
        with self.lock:
            s = self.sessions[session_id].model_copy(update=changes)
            self.sessions[session_id] = s
            return s


store = Store()
