from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .errors import StructuredValidationError

Phase = Literal["reinforcement", "movement"]


class ProtocolModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class JoinGame(ProtocolModel):
    type: Literal["join_game"]
    game_id: str
    handle: str


class JoinAck(ProtocolModel):
    type: Literal["join_ack"]
    game_id: str
    status: Any
    joined: int
    required: int


class JoinRejected(ProtocolModel):
    type: Literal["join_rejected"]
    game_id: str
    reason: str


class GameStarted(ProtocolModel):
    type: Literal["game_started"]
    game_id: str
    player_id: str
    ruleset_id: str
    reports: list[dict[str, Any]]
    communication_rules: dict[str, Any]
    status: dict[str, Any]


class PhaseRequest(ProtocolModel):
    type: Literal["phase_request"]
    game_id: str
    request_id: str
    player_id: str
    turn: int
    phase: Phase
    status: dict[str, Any]
    reports: list[dict[str, Any]]
    deadline_ms: int | None = None


class PeerDiplomacyDraft(ProtocolModel):
    """Outbound peer diplomacy text the harness may send via Clankmates.

    This is not a server command. It is kept on OrderResponse only for compatibility
    with the current local-game harness fanout shape; production play should send
    peer diplomacy directly through Clankmates.
    """

    to_player_id: str
    body: str


class Order(ProtocolModel):
    kind: Literal["reinforce", "move", "support"]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.lower()
        return value


class OrderResponse(ProtocolModel):
    type: Literal["order_response"]
    game_id: str
    reply_to: str
    player_id: str
    turn: int
    phase: Phase
    orders: list[Order]
    done: bool
    table_talk: list[Any]
    messages: list[PeerDiplomacyDraft]
    source: str
    fallback_reason: str | None = None


class PeerDiplomacyMessage(ProtocolModel):
    """A direct player-to-player Clankmates diplomacy message.

    The JSON body type remains ``diplomacy_message`` because that is the envelope
    used in Clankmates inbox bodies. It is not a server command and should not be
    sent to the game server as authoritative game input.
    """

    type: Literal["diplomacy_message"]
    game_id: str
    from_player_id: str
    to_player_id: str
    turn: int
    phase: Phase
    body: str

    @model_validator(mode="after")
    def reject_self_directed(self) -> PeerDiplomacyMessage:
        if self.from_player_id == self.to_player_id:
            raise ValueError("peer diplomacy message cannot be self-directed")
        return self


MessageBody = Annotated[
    JoinGame
    | JoinAck
    | JoinRejected
    | GameStarted
    | PhaseRequest
    | OrderResponse
    | PeerDiplomacyMessage,
    Field(discriminator="type"),
]

MESSAGE_MODELS = {
    "join_game": JoinGame,
    "join_ack": JoinAck,
    "join_rejected": JoinRejected,
    "game_started": GameStarted,
    "phase_request": PhaseRequest,
    "order_response": OrderResponse,
    "diplomacy_message": PeerDiplomacyMessage,
}


def parse_message_body(payload: Any) -> ProtocolModel:
    if not isinstance(payload, dict):
        raise StructuredValidationError([{"field": "$", "message": "expected JSON object"}])
    message_type = payload.get("type")
    model = MESSAGE_MODELS.get(message_type)
    if model is None:
        raise StructuredValidationError([{"field": "type", "message": "unknown message type"}])
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise StructuredValidationError(_structured_errors(exc)) from exc


def _structured_errors(exc: ValidationError) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for error in exc.errors():
        loc = error["loc"]
        field = ".".join(str(part) for part in loc) if loc else "$"
        if field == "$" and "peer diplomacy" in error["msg"]:
            field = "to_player_id"
        errors.append({"field": field, "message": error["msg"]})
    return errors
