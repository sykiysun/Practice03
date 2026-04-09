"""Blackjack card-counting practice app (8-deck shoe, Hi-Lo system).

Run:
    python blackjack_counter_app.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

TK_IMPORT_ERROR: Exception | None = None
try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError as exc:  # pragma: no cover - depends on host runtime packages
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    TK_IMPORT_ERROR = exc


RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]


def hi_lo_value(rank: str) -> int:
    """Return Hi-Lo counting value for a card rank."""
    if rank in {"2", "3", "4", "5", "6"}:
        return 1
    if rank in {"7", "8", "9"}:
        return 0
    return -1


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def display(self) -> str:
        return f"{self.rank}{self.suit}"


class Shoe:
    """Represents an 8-deck shoe with a cut card around half penetration."""

    def __init__(self, decks: int = 8, cut_min: float = 0.45, cut_max: float = 0.55) -> None:
        self.decks = decks
        self.cut_min = cut_min
        self.cut_max = cut_max
        self.cards: list[Card] = []
        self.total_cards = 0
        self.cut_index = 0
        self.dealt_count = 0
        self.shuffle()

    def shuffle(self) -> None:
        self.cards = [Card(rank, suit) for _ in range(self.decks) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)
        self.total_cards = len(self.cards)
        self.dealt_count = 0

        cut_ratio = random.uniform(self.cut_min, self.cut_max)
        self.cut_index = int(self.total_cards * cut_ratio)

    @property
    def cards_remaining(self) -> int:
        return self.total_cards - self.dealt_count

    @property
    def penetration(self) -> float:
        if self.total_cards == 0:
            return 0.0
        return self.dealt_count / self.total_cards

    @property
    def cut_reached(self) -> bool:
        return self.dealt_count >= self.cut_index

    @property
    def decks_remaining(self) -> float:
        return max(self.cards_remaining / 52.0, 0.0)

    def draw(self) -> Card:
        if not self.cards:
            raise RuntimeError("Shoe is empty. Shuffle before drawing.")
        card = self.cards.pop()
        self.dealt_count += 1
        return card


class CountingPracticeApp:
    def __init__(self, root: Any) -> None:
        self.root = root
        self.root.title("Blackjack Card Counting Practice")
        self.root.geometry("560x460")
        self.root.minsize(560, 460)

        self.shoe = Shoe(decks=8)
        self.current_card: Card | None = None

        self.correct_answers = 0
        self.total_answers = 0

        self.user_running_count = 0
        self.actual_running_count = 0
        self.last_answer: int | None = None
        self.pending_shuffle = False

        self._build_ui()
        self._bind_hotkeys()
        self._update_stats()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(
            container,
            text="8-Deck Blackjack Counting Trainer (Hi-Lo)",
            font=("TkDefaultFont", 14, "bold"),
        )
        title.pack(anchor="center", pady=(0, 12))

        self.card_label = ttk.Label(
            container,
            text="Press Deal Card to start",
            anchor="center",
            font=("TkDefaultFont", 26, "bold"),
            relief="groove",
            padding=20,
        )
        self.card_label.pack(fill="x", pady=(0, 10))

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(0, 8))
        controls.columnconfigure((0, 1, 2), weight=1)

        self.minus_btn = ttk.Button(controls, text="-1 (High)", command=lambda: self.submit_guess(-1), state="disabled")
        self.zero_btn = ttk.Button(controls, text="0 (Neutral)", command=lambda: self.submit_guess(0), state="disabled")
        self.plus_btn = ttk.Button(controls, text="+1 (Low)", command=lambda: self.submit_guess(1), state="disabled")
        self.minus_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.zero_btn.grid(row=0, column=1, sticky="ew", padx=3)
        self.plus_btn.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        self.deal_btn = ttk.Button(container, text="Deal Card  [Space]", command=self.deal_card)
        self.deal_btn.pack(fill="x", pady=(6, 8))

        self.feedback_label = ttk.Label(
            container,
            text="Hi-Lo: 2-6 = +1, 7-9 = 0, 10-A = -1",
            foreground="#2b2b2b",
        )
        self.feedback_label.pack(fill="x", pady=(0, 10))

        stats_frame = ttk.LabelFrame(container, text="Practice Stats", padding=10)
        stats_frame.pack(fill="x")
        stats_frame.columnconfigure((0, 1), weight=1)

        self.accuracy_label = ttk.Label(stats_frame, text="")
        self.counts_label = ttk.Label(stats_frame, text="")
        self.shoe_label = ttk.Label(stats_frame, text="")
        self.status_label = ttk.Label(stats_frame, text="")

        self.accuracy_label.grid(row=0, column=0, sticky="w")
        self.counts_label.grid(row=0, column=1, sticky="w")
        self.shoe_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.status_label.grid(row=1, column=1, sticky="w", pady=(4, 0))

        reset_row = ttk.Frame(container)
        reset_row.pack(fill="x", pady=(10, 0))
        ttk.Button(reset_row, text="Reset Session Stats", command=self.reset_stats).pack(side="left")
        ttk.Button(reset_row, text="Manual Shuffle", command=self.manual_shuffle).pack(side="right")

    def _bind_hotkeys(self) -> None:
        self.root.bind("<space>", lambda _: self.deal_card())
        self.root.bind("-", lambda _: self.submit_guess(-1))
        self.root.bind("0", lambda _: self.submit_guess(0))
        self.root.bind("=", lambda _: self.submit_guess(1))  # '+' on most keyboards
        self.root.bind("+", lambda _: self.submit_guess(1))

    def _set_guess_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.minus_btn.config(state=state)
        self.zero_btn.config(state=state)
        self.plus_btn.config(state=state)

    def reset_stats(self) -> None:
        self.correct_answers = 0
        self.total_answers = 0
        self.user_running_count = 0
        self.actual_running_count = 0
        self.current_card = None
        self.pending_shuffle = False
        self.card_label.config(text="Session reset. Press Deal Card.")
        self.feedback_label.config(text="Hi-Lo: 2-6 = +1, 7-9 = 0, 10-A = -1", foreground="#2b2b2b")
        self._set_guess_enabled(False)
        self._update_stats()

    def manual_shuffle(self) -> None:
        self.shoe.shuffle()
        self.user_running_count = 0
        self.actual_running_count = 0
        self.current_card = None
        self.pending_shuffle = False
        self.card_label.config(text="Shoe shuffled. Press Deal Card.")
        self.feedback_label.config(text="New shoe started. Running counts reset to 0.", foreground="#0b5394")
        self._set_guess_enabled(False)
        self._update_stats()

    def deal_card(self) -> None:
        if self.current_card is not None:
            self.feedback_label.config(text="Classify the current card first (-1, 0, +1).", foreground="#b45f06")
            return

        if self.pending_shuffle or not self.shoe.cards:
            self.shoe.shuffle()
            self.user_running_count = 0
            self.actual_running_count = 0
            self.pending_shuffle = False
            self.feedback_label.config(text="Cut card reached. New shoe shuffled.", foreground="#0b5394")

        self.current_card = self.shoe.draw()
        self.card_label.config(text=self.current_card.display)
        self._set_guess_enabled(True)
        self._update_stats()

    def submit_guess(self, guess: int) -> None:
        if self.current_card is None:
            self.feedback_label.config(text="Press Deal Card first.", foreground="#b45f06")
            return

        expected = hi_lo_value(self.current_card.rank)
        self.last_answer = guess
        self.total_answers += 1
        self.user_running_count += guess
        self.actual_running_count += expected

        if guess == expected:
            self.correct_answers += 1
            self.feedback_label.config(
                text=f"Correct: {self.current_card.display} is {expected:+d}.",
                foreground="#38761d",
            )
        else:
            self.feedback_label.config(
                text=f"Incorrect: {self.current_card.display} is {expected:+d}.",
                foreground="#a61c00",
            )

        self.current_card = None
        self._set_guess_enabled(False)

        if self.shoe.cut_reached:
            self.pending_shuffle = True
            self.status_label.config(text="Status: Cut card reached - next deal reshuffles")

        self._update_stats()

    def _update_stats(self) -> None:
        accuracy = 0.0 if self.total_answers == 0 else (100.0 * self.correct_answers / self.total_answers)
        true_count = 0.0
        if self.shoe.decks_remaining > 0:
            true_count = self.actual_running_count / self.shoe.decks_remaining

        self.accuracy_label.config(
            text=f"Answers: {self.correct_answers}/{self.total_answers} ({accuracy:.1f}%)"
        )
        self.counts_label.config(
            text=(
                f"Your running count: {self.user_running_count:+d} | "
                f"Actual running count: {self.actual_running_count:+d}"
            )
        )
        self.shoe_label.config(
            text=(
                f"Shoe: {self.shoe.cards_remaining} cards left | "
                f"Penetration: {self.shoe.penetration * 100:.1f}% | "
                f"Cut at card {self.shoe.cut_index}/{self.shoe.total_cards}"
            )
        )
        if not self.pending_shuffle:
            self.status_label.config(text=f"Status: In shoe | Estimated true count: {true_count:+.2f}")


def main() -> None:
    if tk is None:
        print("Tkinter is not installed in this Python environment.")
        print("Install Tk support, then run: python3 blackjack_counter_app.py")
        if TK_IMPORT_ERROR is not None:
            print(f"Details: {TK_IMPORT_ERROR}")
        return

    root = tk.Tk()
    app = CountingPracticeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
