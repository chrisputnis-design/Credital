"""Card helpers. A card is an int 0..51: rank * 4 + suit (rank 0 = '2' ... 12 = 'A')."""
from __future__ import annotations

RANKS = "23456789TJQKA"
SUITS = "cdhs"


def card(s: str) -> int:
    """'As' -> int."""
    return RANKS.index(s[0].upper()) * 4 + SUITS.index(s[1].lower())


def hand(s: str) -> tuple:
    """'AsKd' or 'As Kd' -> tuple of card ints."""
    s = s.replace(" ", "")
    return tuple(card(s[i:i + 2]) for i in range(0, len(s), 2))


def card_str(c: int) -> str:
    return RANKS[c >> 2] + SUITS[c & 3]


def cards_str(cs) -> str:
    return " ".join(card_str(c) for c in cs)
