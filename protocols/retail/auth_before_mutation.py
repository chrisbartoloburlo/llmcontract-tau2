"""Retail invariant: must authenticate before any database-mutating action.

Source: data/tau2/domains/retail/policy.md
> "At the beginning of the conversation, you have to authenticate the user
>  identity by locating their user id via email, or via name + zip code. This
>  has to be done even when the user already provides the user id."
> "Before taking any action that updates the database (cancel, modify, return,
>  exchange), you must list the action details and obtain explicit user
>  confirmation (yes) to proceed."

Encoding strategy: project every agent tool call to one of three labels —
{Auth, Mutate, Other} — then check that no Mutate appears before the first
Auth. The protocol below has two recursive states: PreAuth (only Other and
Auth are legal) and PostAuth (anything is legal).

Recursion is open-ended because the trajectory length is unbounded; we don't
require the agent to *terminate* the protocol, only to never violate it.
"""

# Tools that authenticate the user.
AUTH_TOOLS = {
    "find_user_id_by_email",
    "find_user_id_by_name_zip",
}

# Tools the policy explicitly calls out as database-mutating.
MUTATE_TOOLS = {
    "cancel_pending_order",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "modify_user_address",
    "return_delivered_order_items",
    "exchange_delivered_order_items",
}

PROTOCOL = (
    "rec PreAuth.!{"
    "Auth.rec PostAuth.!{Auth.PostAuth, Mutate.PostAuth, Other.PostAuth}, "
    "Other.PreAuth"
    "}"
)


def project(tool_name: str) -> str:
    """Map a tau2 tool name to one of the three protocol labels."""
    if tool_name in AUTH_TOOLS:
        return "Auth"
    if tool_name in MUTATE_TOOLS:
        return "Mutate"
    return "Other"
