from enum import StrEnum


class Sport(StrEnum):
    NFL = "NFL"
    NBA = "NBA"
    MLB = "MLB"
    NHL = "NHL"
    NCAAF = "NCAAF"
    NCAAB = "NCAAB"
    OTHER = "OTHER"


class BetType(StrEnum):
    SPREAD = "SPREAD"
    MONEYLINE = "MONEYLINE"
    TOTAL = "TOTAL"
    PROP = "PROP"
    PARLAY = "PARLAY"
    TEASER = "TEASER"


class BetResult(StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"
    PENDING = "PENDING"


class Tier(StrEnum):
    FREE = "free"
    PRO = "pro"
    SHARP = "sharp"


class AlertType(StrEnum):
    VALUE = "value"
    MOVEMENT = "movement"
    GAME = "game"
