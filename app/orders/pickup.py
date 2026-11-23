"""Booking a pickup time ("scheduled pickup").

The customer picks one of the 15-minute marks (12:00, 12:15, 12:30, ...). The
earliest one allowed is at least 30 minutes from now, so the stall has time to
see the order and cook it; the latest is 24 hours from now.

A vendor can also limit bookings to its own pickup hours (Vendor.pickup_hours,
e.g. 11:00-13:30 and 17:00-19:30, the same every day, Taiwan time): the booked
time then has to fall inside one of them, both ends included. With no pickup
hours set, every slot is allowed.
"""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, time, timedelta, timezone

from app.core.errors import BadRequestError

SLOT_MINUTES = 15
MIN_LEAD = timedelta(minutes=30)
MAX_AHEAD = timedelta(hours=24)
TAIWAN = timezone(timedelta(hours=8))


def within_hours(at: datetime, periods: Iterable[Mapping[str, str]]) -> bool:
    """Whether the time (any timezone) falls inside one of the pickup hours.

    No periods means the vendor has not limited its hours: always True.
    """
    periods = list(periods)
    if not periods:
        return True
    clock = at.astimezone(TAIWAN).time()
    return any(
        time.fromisoformat(p["open"]) <= clock <= time.fromisoformat(p["close"])
        for p in periods
    )


def check_pickup_time(
    pickup_time: datetime,
    now: datetime | None = None,
    periods: Iterable[Mapping[str, str]] = (),
) -> datetime:
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
    if not within_hours(at, periods):
        raise BadRequestError("This vendor does not take pickups at that time")
    return at
