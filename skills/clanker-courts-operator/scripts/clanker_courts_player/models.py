from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .errors import StructuredValidationError

Phase = Literal["reinforcement", "movement"]
PhaseStatus = Literal["open", "expired"]


class ProtocolModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("by_alias", True)
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


class Order(ProtocolModel):
    kind: Literal["reinforce", "move", "support"]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.lower()
        return value


class OrderPackage(ClientCommandModel):
    type: Literal["order_package"]
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
                    raise ValueError(f"order_package must not include {field}")
        return value


class GetCurrentPhase(ClientCommandModel):
    type: Literal["get_current_phase"]
    game_id: str
    request_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_api_and_replay_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            forbidden_fields = (
                "command",
                "schema_version",
                "player_id",
                "thread_id",
                "phase_id",
                "turn",
                "phase",
                "handle",
            )
            for field in forbidden_fields:
                if field in value:
                    raise ValueError(f"get_current_phase must not include {field}")
        return value


class GetAfterGameReport(ClientCommandModel):
    type: Literal["get_after_game_report"]
    game_id: str
    request_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_api_identity_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            forbidden_fields = (
                "command",
                "schema_version",
                "player_id",
                "turn",
                "phase",
                "handle",
            )
            for field in forbidden_fields:
                if field in value:
                    raise ValueError(f"get_after_game_report must not include {field}")
        return value


class ServerManifest(ProtocolModel):
    type: Literal["server_manifest"]
    server: str
    protocol_version: int
    rules: str
    rules_metadata: dict[str, Any] | None = None
    game: dict[str, Any]


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


class ReadyCheck(ProtocolModel):
    type: Literal["ready_check"]
    game_id: str
    ready_by_ms: int


class StartCancelled(ProtocolModel):
    type: Literal["start_cancelled"]
    game_id: str
    reason: str
    open_slots: int


class PhaseReport(ProtocolModel):
    game_id: str
    turn: int
    phase: Phase


class SetupReport(PhaseReport):
    type: Literal["setup_report"]
    rules: str
    rules_metadata: dict[str, Any] | None = None
    final_turn: int
    phase_id: str
    phase_clock_ms: dict[str, int]
    capital_location_id: str
    player: str | None = None
    handle_mode: Literal["random", "stable"] | None = None
    players: list[str]
    visibility: dict[str, Any]


class MovementPhaseReport(PhaseReport):
    type: Literal["movement_phase_report"]
    phase_id: str
    movement_clock_ms: int | None = None
    visibility: dict[str, Any]


class MovementResultReport(PhaseReport):
    type: Literal["movement_result_report"]
    battle_reports: list[dict[str, Any]]
    status: dict[str, Any]
    visibility: dict[str, Any]
    next_phase: dict[str, Any] | None = None


class AfterGameReport(ProtocolModel):
    type: Literal["after_game_report"]
    game_id: str
    winners: list[str] | None = None
    outcome_reason: str | None = None
    score_rationale: str | None = None
    final_state: dict[str, Any]
    final_standings: list[dict[str, Any]] | None = None
    match_points: list[dict[str, Any]] | None = None
    effective_packages: list[dict[str, Any]]
    battle_events: list[dict[str, Any]]
    phase_timeline: list[dict[str, Any]]


class OrderAccepted(ProtocolModel):
    type: Literal["order_accepted"]
    game_id: str
    phase_id: str
    ready: bool


class OrderRejected(ProtocolModel):
    type: Literal["order_rejected"]
    game_id: str
    phase_id: str
    errors: list[dict[str, Any]]
    ready: bool


class CurrentPhase(ProtocolModel):
    phase_id: str
    turn: int
    phase: Phase
    status: PhaseStatus
    deadline_at: str


class AllowedCommand(ProtocolModel):
    command: str
    accepting: bool | None = None
    request: dict[str, Any]


class LatestReport(ProtocolModel):
    id: str
    phase_id: str | None = None
    report_type: str
    report_hash: str


class CurrentPhaseResponse(ProtocolModel):
    type: Literal["current_phase"]
    schema_version: int
    request_id: str
    current_phase: CurrentPhase | None
    allowed_command: AllowedCommand
    latest_report: LatestReport
    visible_state: dict[str, Any] | None = None

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", False)
        return super().model_dump(*args, **kwargs)


class CurrentPhaseRejected(ProtocolModel):
    type: Literal["current_phase_rejected"]
    game_id: str
    request_id: str | None = None
    error: dict[str, Any]


class AfterGameReportRejected(ProtocolModel):
    type: Literal["after_game_report_rejected"]
    game_id: str
    request_id: str | None = None
    error: dict[str, Any]


class BrokeredNegotiationMessage(ClientCommandModel):
    """A server-brokered private negotiation message.

    Client commands include `destination`; server-delivered negotiation includes
    `from`. Both shapes intentionally use the same protocol `type`.
    """

    type: Literal["message"]
    game_id: str
    body: str
    destination: str | None = None
    from_: str | None = Field(default=None, alias="from")

    @model_validator(mode="after")
    def require_direction(self) -> BrokeredNegotiationMessage:
        has_destination = isinstance(self.destination, str) and self.destination.strip() != ""
        has_from = isinstance(self.from_, str) and self.from_.strip() != ""
        if has_destination == has_from:
            raise ValueError("message must include exactly one of destination or from")
        if self.body.strip() == "":
            raise ValueError("message body must not be empty")
        return self


class MessageAccepted(ProtocolModel):
    type: Literal["message_accepted"]
    game_id: str
    destination: str


class MessageRejected(ProtocolModel):
    type: Literal["message_rejected"]
    game_id: str
    destination: str | None = None
    error: dict[str, Any]


class PeerDiplomacyMessage(ProtocolModel):
    """A direct player-to-player Clankmates diplomacy message.

    Retained for historical archives and explicit fallback tooling. Normal
    current games use server-brokered `message` traffic instead.
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
    | OrderPackage
    | GetCurrentPhase
    | GetAfterGameReport
    | JoinAck
    | JoinRejected
    | ReadyCheck
    | StartCancelled
    | SetupReport
    | MovementPhaseReport
    | MovementResultReport
    | AfterGameReport
    | OrderAccepted
    | OrderRejected
    | CurrentPhaseResponse
    | CurrentPhaseRejected
    | BrokeredNegotiationMessage
    | MessageAccepted
    | MessageRejected
    | AfterGameReportRejected
    | PeerDiplomacyMessage,
    Field(discriminator="type"),
]

MESSAGE_MODELS = {
    "server_manifest": ServerManifest,
    "join_game": JoinGame,
    "ready_to_start": ReadyToStart,
    "order_package": OrderPackage,
    "get_current_phase": GetCurrentPhase,
    "get_after_game_report": GetAfterGameReport,
    "join_ack": JoinAck,
    "join_rejected": JoinRejected,
    "ready_check": ReadyCheck,
    "start_cancelled": StartCancelled,
    "setup_report": SetupReport,
    "movement_phase_report": MovementPhaseReport,
    "movement_result_report": MovementResultReport,
    "after_game_report": AfterGameReport,
    "order_accepted": OrderAccepted,
    "order_rejected": OrderRejected,
    "current_phase": CurrentPhaseResponse,
    "current_phase_rejected": CurrentPhaseRejected,
    "message": BrokeredNegotiationMessage,
    "message_accepted": MessageAccepted,
    "message_rejected": MessageRejected,
    "after_game_report_rejected": AfterGameReportRejected,
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


def parse_get_current_phase_request(payload: Any) -> GetCurrentPhase:
    if not isinstance(payload, dict):
        raise StructuredValidationError([{"field": "$", "message": "expected JSON object"}])
    try:
        return GetCurrentPhase.model_validate(payload)
    except ValidationError as exc:
        raise StructuredValidationError(_structured_errors(exc)) from exc


def parse_get_after_game_report_request(payload: Any) -> GetAfterGameReport:
    if not isinstance(payload, dict):
        raise StructuredValidationError([{"field": "$", "message": "expected JSON object"}])
    try:
        return GetAfterGameReport.model_validate(payload)
    except ValidationError as exc:
        raise StructuredValidationError(_structured_errors(exc)) from exc


def parse_current_phase_response(payload: Any) -> CurrentPhaseResponse:
    if not isinstance(payload, dict):
        raise StructuredValidationError([{"field": "$", "message": "expected JSON object"}])
    try:
        return CurrentPhaseResponse.model_validate(payload)
    except ValidationError as exc:
        raise StructuredValidationError(_structured_errors(exc)) from exc


def _structured_errors(exc: ValidationError) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for error in exc.errors():
        loc = error["loc"]
        field = ".".join(str(part) for part in loc) if loc else "$"
        if field == "$" and "peer diplomacy" in error["msg"]:
            field = "to_player_id"
        if (
            field == "$"
            and "message must include exactly one of destination or from" in error["msg"]
        ):
            field = "destination"
        if field == "$" and "message body must not be empty" in error["msg"]:
            field = "body"
        if field == "$" and "join_game must not include handle" in error["msg"]:
            field = "handle"
        if field == "$" and "order_package must not include " in error["msg"]:
            field = error["msg"].rsplit(" ", 1)[-1]
        if field == "$" and "get_current_phase must not include " in error["msg"]:
            field = error["msg"].rsplit(" ", 1)[-1]
        if field == "$" and "get_after_game_report must not include " in error["msg"]:
            field = error["msg"].rsplit(" ", 1)[-1]
        errors.append({"field": field, "message": error["msg"]})
    return errors
