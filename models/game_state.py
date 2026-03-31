from dataclasses import asdict, dataclass, field, fields


@dataclass
class GameState:
    message_id: int | None = None
    bet_amount: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        # Use fields(cls) to get ALL fields including inherited ones
        valid_fields = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid_fields})


@dataclass
class TKMState(GameState):
    game: str = "tkm"


@dataclass
class SlotState(GameState):
    game: str = "slot"


@dataclass
class BlackjackState(GameState):
    deck: list[tuple[str, str]] = field(default_factory=list)
    player_hand: list[tuple[str, str]] = field(default_factory=list)
    dealer_hand: list[tuple[str, str]] = field(default_factory=list)
    game: str = "blackjack"

    # Inherit generic from_dict from GameState which now handles everything correctly
