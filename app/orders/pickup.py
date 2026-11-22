"""Booking a pickup time ("scheduled pickup").

The customer picks one of the 15-minute marks (12:00, 12:15, 12:30, ...). The
earliest one allowed is at least 30 minutes from now, so the stall has time to
see the order and cook it; the latest is 24 hours from now.
"""

from datetime import UTC, datetime, timedelta

from app.core.errors import BadRequestError

SLOT_MINUTES = 15
MIN_LEAD = timedelta(minutes=30)
MAX_AHEAD = timedelta(hours=24)


def check_pickup_time(pickup_time: datetime, now: datetime | None = None) -> datetime:
    """Returns the booked time in UTC, or raises if it is not an allowed slot."""
    now = now or datetime.now(UTC)
    at = pickup_time.astimezone(UTC)
    # Taiwan is UTC+8, a whole number of hours, so a 15-minute mark in UTC is one there too
    if at.minute % SLOT_MINUTES or at.second or at.microsecond:
        raise BadRequestError(
            f"Pickup time must be on a {SLOT_MINUTES}-minute mark (e.g. 12:00, 12:15)"
        )
    if at < now + MIN_LEAD:
        raise BadRequestError(
            "A booked pickup time must be at least 30 minutes from now"
        )
    if at > now + MAX_AHEAD:
        raise BadRequestError("Pickup can be booked at most 24 hours ahead")
    return at
