"""Airline invariant: must obtain user confirmation before mutating bookings.

Source: data/tau2/domains/airline/policy.md
> "Before taking any actions that update the booking database (booking,
>  modifying flights, editing baggage, changing cabin class, or updating
>  passenger information), you must list the action details and obtain
>  explicit user confirmation (yes) to proceed."

Same shape as `protocols.retail.confirm_before_mutation` — only the set of
mutating tools differs. Reuses the protocol DSL and the projection helper.
"""

from __future__ import annotations

from ..retail.confirm_before_mutation import (
    CONFIRM_RE,
    PROTOCOL,
    project_message as _project_message_retail,
    project_simulation as _project_simulation_retail,
)

__all__ = ["MUTATE_TOOLS", "PROTOCOL", "CONFIRM_RE", "project_message", "project_simulation"]


MUTATE_TOOLS = {
    "book_reservation",
    "cancel_reservation",
    "update_reservation_baggages",
    "update_reservation_flights",
    "update_reservation_passengers",
    "send_certificate",
}


def project_message(message: dict) -> list[str]:
    role = message.get("role")
    if role == "user":
        content = (message.get("content") or "").strip()
        return ["UserConfirm" if CONFIRM_RE.search(content) else "Other"]
    if role == "assistant":
        events: list[str] = []
        for tc in message.get("tool_calls") or []:
            fn = (tc.get("function") or {}).get("name") or tc.get("name")
            if fn:
                events.append("Mutate" if fn in MUTATE_TOOLS else "Other")
        if not events and (message.get("content") or "").strip():
            events.append("Other")
        return events
    return []


def project_simulation(simulation: dict) -> list[str]:
    events: list[str] = []
    for m in simulation.get("messages") or []:
        events.extend(project_message(m))
    return events
