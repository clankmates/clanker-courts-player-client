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


class ClientCommandModel(ProtocolModel):
    pass


class JoinGame(ClientCommandModel):
    type: Literal["join_game"]
    game_id: str

    @model_validator(mode="before")
    @classmethod
    def reject_client_supplied_identity(cls, value: Any) -> Any:
        if isinstance(value, dict) and "handle" in value:
            raise ValueError("join_game must not include handle")
        return value


class ReadyToStart(ClientCommandModel):
    type: Literal["ready_to_start"]
    game_id: str
    ready_check_id: str


class Order(ProtocolModel):
    kind: Literal["reinforce", "move", "support"]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.lower()
        return value


class OrderResponse(ClientCommandModel):
    type: Literal["order_response"]
    game_id: str
    phase_id: str
    orders: list[Order]

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_identity_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            legacy_fields = (
                "reply_to",
                "player_id",
                "turn",
                "phase",
                "done",
                "table_talk",
                "messages",
            )
            for field in legacy_fields:
                if field in value:
                    raise ValueError(f"order_response must not include {field}")
        return value


class DonePhase(ClientCommandModel):
    type: Literal["done_phase"]
    game_id: str
    phase_id: str


class LobbyPlayer(ProtocolModel):
    slot: int | None = None
    handle: str | None = None
    channel: str | None = None
    player_id: str | None = None


class ServerManifest(ProtocolModel):
    type: Literal["server_manifest"]
    server: dict[str, Any]
    protocol_version: int
    rules: dict[str, Any]
    game: dict[str, Any]
    players: list[LobbyPlayer]


class JoinAck(ProtocolModel):
    type: Literal["join_ack"]
    game_id: str
    status: str
    joined: int
    required: int
    open_slots: int | None = None


class JoinRejected(ProtocolModel):
    type: Literal["join_rejected"]
    game_id: str
    reason: str


class LobbyUpdate(ProtocolModel):
    type: Literal["lobby_update"]
    game_id: str
    joined: int
    required: int
    open_slots: int
    players: list[LobbyPlayer]


class ReadyCheck(ProtocolModel):
    type: Literal["ready_check"]
    game_id: str
    ready_check_id: str
    ready_by_ms: int
    players: list[LobbyPlayer]


class SetupReport(ProtocolModel):
    type: Literal["setup_report"]
    game_id: str
    ruleset_id: str
    ruleset_hash: str
    final_turn: int
    phase_clocks_ms: dict[str, int]
    player_id: str
    capital_location_id: str
    players: list[LobbyPlayer]
    canonical_order: dict[str, Any]
    visibility: dict[str, Any]


class PhaseReport(ProtocolModel):
    game_id: str
    turn: int
    phase: Phase


class ReinforcementReport(PhaseReport):
    type: Literal["reinforcement_report"]
    phase_id: str
    reinforcements_available: int
    controlled_cities: list[dict[str, Any]]
    reinforcement_clock_ms: int | None = None


class ReinforcementResultReport(PhaseReport):
    type: Literal["reinforcement_result_report"]
    applied_orders: list[dict[str, Any]]
    visibility: dict[str, Any]


class MovementVisibilityReport(PhaseReport):
    type: Literal["movement_visibility_report"]
    phase_id: str
    movement_clock_ms: int | None = None
    visibility: dict[str, Any]


class MovementResultReport(PhaseReport):
    type: Literal["movement_result_report"]
    battle_reports: list[dict[str, Any]]
    status: dict[str, Any]
    visibility: dict[str, Any]


class AfterGameReport(ProtocolModel):
    type: Literal["after_game_report"]
    game_id: str


class OrderAccepted(ProtocolModel):
    type: Literal["order_accepted"]
    game_id: str
    phase_id: str
    normalized_orders: list[dict[str, Any]]


class OrderRejected(ProtocolModel):
    type: Literal["order_rejected"]
    game_id: str
    phase_id: str
    errors: list[dict[str, Any]]


class PeerDiplomacyMessage(ProtocolModel):
    """A direct player-to-player Clankmates diplomacy message.

    The server command protocol does not embed diplomacy in order submissions.
    This envelope is local client state and direct Clankmates traffic only.
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
    ServerManifest
    | JoinGame
    | ReadyToStart
    | OrderResponse
    | DonePhase
    | JoinAck
    | JoinRejected
    | LobbyUpdate
    | ReadyCheck
    | SetupReport
    | ReinforcementReport
    | ReinforcementResultReport
    | MovementVisibilityReport
    | MovementResultReport
    | AfterGameReport
    | OrderAccepted
    | OrderRejected
    | PeerDiplomacyMessage,
    Field(discriminator="type"),
]

MESSAGE_MODELS = {
    "server_manifest": ServerManifest,
    "join_game": JoinGame,
    "ready_to_start": ReadyToStart,
    "order_response": OrderResponse,
    "done_phase": DonePhase,
    "join_ack": JoinAck,
    "join_rejected": JoinRejected,
    "lobby_update": LobbyUpdate,
    "ready_check": ReadyCheck,
    "setup_report": SetupReport,
    "reinforcement_report": ReinforcementReport,
    "reinforcement_result_report": ReinforcementResultReport,
    "movement_visibility_report": MovementVisibilityReport,
    "movement_result_report": MovementResultReport,
    "after_game_report": AfterGameReport,
    "order_accepted": OrderAccepted,
    "order_rejected": OrderRejected,
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
        if field == "$" and "join_game must not include handle" in error["msg"]:
            field = "handle"
        if field == "$" and "order_response must not include " in error["msg"]:
            field = error["msg"].rsplit(" ", 1)[-1]
        errors.append({"field": field, "message": error["msg"]})
    return errors
