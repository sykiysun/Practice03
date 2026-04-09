"""Blackjack card-counting practice app with playable table mode.

Run:
    python3 blackjack_counter_app.py
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


def blackjack_rank_value(rank: str) -> int:
    if rank in {"J", "Q", "K"}:
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(cards: list["Card"]) -> tuple[int, bool]:
    """Return blackjack hand total and whether it is soft."""
    total = 0
    aces = 0
    for card in cards:
        value = blackjack_rank_value(card.rank)
        total += value
        if card.rank == "A":
            aces += 1

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    is_soft = aces > 0
    return total, is_soft


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
        self.cut_index = int(self.total_cards * random.uniform(self.cut_min, self.cut_max))

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


class BlackjackEngine:
    """Game engine that can be driven by any UI."""

    def __init__(self, decks: int = 8, starting_bankroll: float = 1000.0) -> None:
        self.shoe = Shoe(decks=decks)
        self.running_count = 0
        self.pending_shuffle = False

        self.bankroll = float(starting_bankroll)
        self.player_cards: list[Card] = []
        self.dealer_cards: list[Card] = []
        self.current_bet = 0.0
        self.round_active = False
        self.dealer_revealed = False
        self.can_double = False
        self.can_surrender = False

        self.hands_played = 0
        self.hands_won = 0
        self.hands_lost = 0
        self.hands_push = 0
        self.hands_blackjack = 0
        self.hands_surrendered = 0

    def shuffle_new_shoe(self) -> None:
        self.shoe.shuffle()
        self.running_count = 0
        self.pending_shuffle = False

    def _draw_card(self) -> Card:
        if not self.shoe.cards:
            self.shuffle_new_shoe()
        card = self.shoe.draw()
        self.running_count += hi_lo_value(card.rank)
        if self.shoe.cut_reached:
            self.pending_shuffle = True
        return card

    def draw_practice_card(self) -> Card:
        if self.round_active:
            raise RuntimeError("Finish the blackjack hand first.")
        if self.pending_shuffle or not self.shoe.cards:
            self.shuffle_new_shoe()
        return self._draw_card()

    def _finish_round(self, outcome: str, message: str, payout_multiplier: float) -> str:
        self.round_active = False
        self.dealer_revealed = True
        self.can_double = False
        self.can_surrender = False
        self.hands_played += 1

        if outcome == "win":
            self.hands_won += 1
        elif outcome == "loss":
            self.hands_lost += 1
        elif outcome == "push":
            self.hands_push += 1
        elif outcome == "blackjack":
            self.hands_won += 1
            self.hands_blackjack += 1
        elif outcome == "surrender":
            self.hands_lost += 1
            self.hands_surrendered += 1

        if payout_multiplier > 0:
            self.bankroll += self.current_bet * payout_multiplier
        return message

    def _dealer_play_and_resolve(self) -> str:
        self.dealer_revealed = True
        dealer_total, _ = hand_value(self.dealer_cards)
        while dealer_total < 17:
            self.dealer_cards.append(self._draw_card())
            dealer_total, _ = hand_value(self.dealer_cards)

        player_total, _ = hand_value(self.player_cards)
        if dealer_total > 21:
            return self._finish_round("win", "Dealer busts. You win.", payout_multiplier=2.0)
        if player_total > dealer_total:
            return self._finish_round("win", "You win.", payout_multiplier=2.0)
        if player_total < dealer_total:
            return self._finish_round("loss", "Dealer wins.", payout_multiplier=0.0)
        return self._finish_round("push", "Push.", payout_multiplier=1.0)

    def start_round(self, bet: float) -> tuple[bool, str]:
        if self.round_active:
            return False, "A hand is already in progress."
        if bet <= 0:
            return False, "Bet must be greater than 0."
        if bet > self.bankroll:
            return False, "Bet is larger than your bankroll."

        if self.pending_shuffle or not self.shoe.cards:
            self.shuffle_new_shoe()

        self.current_bet = round(bet, 2)
        self.bankroll -= self.current_bet
        self.player_cards = [self._draw_card(), self._draw_card()]
        self.dealer_cards = [self._draw_card(), self._draw_card()]
        self.round_active = True
        self.dealer_revealed = False
        self.can_double = True
        self.can_surrender = True

        player_total, _ = hand_value(self.player_cards)
        dealer_total, _ = hand_value(self.dealer_cards)
        player_blackjack = len(self.player_cards) == 2 and player_total == 21
        dealer_blackjack = len(self.dealer_cards) == 2 and dealer_total == 21

        if player_blackjack and dealer_blackjack:
            return True, self._finish_round("push", "Both have blackjack. Push.", payout_multiplier=1.0)
        if player_blackjack:
            return True, self._finish_round("blackjack", "Blackjack! Paid 3:2.", payout_multiplier=2.5)
        if dealer_blackjack:
            return True, self._finish_round("loss", "Dealer has blackjack.", payout_multiplier=0.0)

        return True, "Hand started. Choose Hit, Stand, Double, or Surrender."

    def hit(self) -> tuple[bool, str]:
        if not self.round_active:
            return False, "No active hand. Click Deal Hand first."

        self.player_cards.append(self._draw_card())
        self.can_double = False
        self.can_surrender = False
        total, _ = hand_value(self.player_cards)
        if total > 21:
            return True, self._finish_round("loss", "You bust. Dealer wins.", payout_multiplier=0.0)
        return True, "You hit."

    def stand(self) -> tuple[bool, str]:
        if not self.round_active:
            return False, "No active hand. Click Deal Hand first."
        self.can_double = False
        self.can_surrender = False
        return True, self._dealer_play_and_resolve()

    def double(self) -> tuple[bool, str]:
        if not self.round_active:
            return False, "No active hand. Click Deal Hand first."
        if not self.can_double or len(self.player_cards) != 2:
            return False, "Double is only allowed as your first action."
        if self.bankroll < self.current_bet:
            return False, "Not enough bankroll to double."

        self.bankroll -= self.current_bet
        self.current_bet *= 2
        self.can_double = False
        self.can_surrender = False
        self.player_cards.append(self._draw_card())

        total, _ = hand_value(self.player_cards)
        if total > 21:
            return True, self._finish_round("loss", "You bust after doubling.", payout_multiplier=0.0)
        return True, self._dealer_play_and_resolve()

    def surrender(self) -> tuple[bool, str]:
        if not self.round_active:
            return False, "No active hand. Click Deal Hand first."
        if not self.can_surrender or len(self.player_cards) != 2:
            return False, "Surrender is only allowed as your first action."
        return True, self._finish_round("surrender", "You surrendered. Half bet returned.", payout_multiplier=0.5)


class CountingPracticeApp:
    def __init__(self, root: Any) -> None:
        self.root = root
        self.root.title("Blackjack Counting Trainer + Table Practice")
        self.root.geometry("920x690")
        self.root.minsize(900, 650)

        self.engine = BlackjackEngine(decks=8, starting_bankroll=1000.0)
        self.current_practice_card: Card | None = None

        self.practice_correct = 0
        self.practice_total = 0
        self.practice_user_running_count = 0

        self.bet_var = tk.StringVar(value="25")

        self._build_ui()
        self._bind_hotkeys()
        self._update_all_views()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill="both", expand=True)

        title = ttk.Label(
            container,
            text="8-Deck Blackjack Trainer (Hi-Lo + Playable Table)",
            font=("TkDefaultFont", 15, "bold"),
        )
        title.pack(anchor="center", pady=(0, 10))

        top_info = ttk.LabelFrame(container, text="Shoe & Count", padding=10)
        top_info.pack(fill="x", pady=(0, 8))
        top_info.columnconfigure(0, weight=1)

        self.global_count_label = ttk.Label(top_info, text="")
        self.global_shoe_label = ttk.Label(top_info, text="")
        self.global_status_label = ttk.Label(top_info, text="")

        self.global_count_label.grid(row=0, column=0, sticky="w")
        self.global_shoe_label.grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.global_status_label.grid(row=2, column=0, sticky="w", pady=(3, 0))
        ttk.Button(top_info, text="Manual Shuffle (Between Hands)", command=self.manual_shuffle).grid(
            row=0, column=1, rowspan=3, sticky="e"
        )

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        practice_tab = ttk.Frame(notebook, padding=12)
        table_tab = ttk.Frame(notebook, padding=12)
        notebook.add(practice_tab, text="Counting Drill")
        notebook.add(table_tab, text="Blackjack Table")

        self._build_practice_tab(practice_tab)
        self._build_table_tab(table_tab)

    def _build_practice_tab(self, parent: Any) -> None:
        self.practice_card_label = ttk.Label(
            parent,
            text="Press Deal Practice Card",
            anchor="center",
            font=("TkDefaultFont", 28, "bold"),
            relief="groove",
            padding=22,
        )
        self.practice_card_label.pack(fill="x", pady=(0, 10))

        guess_row = ttk.Frame(parent)
        guess_row.pack(fill="x", pady=(0, 6))
        guess_row.columnconfigure((0, 1, 2), weight=1)

        self.minus_btn = ttk.Button(
            guess_row, text="-1 (10/J/Q/K/A)", command=lambda: self.submit_guess(-1), state="disabled"
        )
        self.zero_btn = ttk.Button(
            guess_row, text="0 (7/8/9)", command=lambda: self.submit_guess(0), state="disabled"
        )
        self.plus_btn = ttk.Button(
            guess_row, text="+1 (2/3/4/5/6)", command=lambda: self.submit_guess(1), state="disabled"
        )

        self.minus_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.zero_btn.grid(row=0, column=1, sticky="ew", padx=3)
        self.plus_btn.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        self.practice_deal_btn = ttk.Button(parent, text="Deal Practice Card [Space]", command=self.deal_practice_card)
        self.practice_deal_btn.pack(fill="x", pady=(5, 6))

        self.practice_feedback_label = ttk.Label(parent, text="Hi-Lo: 2-6=+1, 7-9=0, 10-A=-1")
        self.practice_feedback_label.pack(fill="x", pady=(0, 8))

        practice_stats = ttk.LabelFrame(parent, text="Drill Stats", padding=10)
        practice_stats.pack(fill="x")

        self.practice_accuracy_label = ttk.Label(practice_stats, text="")
        self.practice_counts_label = ttk.Label(practice_stats, text="")
        self.practice_accuracy_label.pack(anchor="w")
        self.practice_counts_label.pack(anchor="w", pady=(4, 0))

        ttk.Button(parent, text="Reset Drill Stats", command=self.reset_practice_stats).pack(anchor="w", pady=(8, 0))

    def _build_table_tab(self, parent: Any) -> None:
        bet_row = ttk.Frame(parent)
        bet_row.pack(fill="x", pady=(0, 8))
        bet_row.columnconfigure(6, weight=1)

        ttk.Label(bet_row, text="Bankroll:").grid(row=0, column=0, sticky="w")
        self.bankroll_label = ttk.Label(bet_row, text="")
        self.bankroll_label.grid(row=0, column=1, sticky="w", padx=(6, 16))

        ttk.Label(bet_row, text="Bet:").grid(row=0, column=2, sticky="w")
        self.bet_spinbox = ttk.Spinbox(bet_row, from_=1, to=10000, textvariable=self.bet_var, width=10)
        self.bet_spinbox.grid(row=0, column=3, sticky="w", padx=(6, 10))

        self.deal_hand_btn = ttk.Button(bet_row, text="Deal Hand", command=self.deal_hand)
        self.deal_hand_btn.grid(row=0, column=4, padx=(0, 4))
        self.hit_btn = ttk.Button(bet_row, text="Hit", command=self.hit_hand)
        self.hit_btn.grid(row=0, column=5, padx=2)
        self.stand_btn = ttk.Button(bet_row, text="Stand", command=self.stand_hand)
        self.stand_btn.grid(row=0, column=6, padx=2, sticky="w")
        self.double_btn = ttk.Button(bet_row, text="Double", command=self.double_hand)
        self.double_btn.grid(row=0, column=7, padx=2)
        self.surrender_btn = ttk.Button(bet_row, text="Surrender", command=self.surrender_hand)
        self.surrender_btn.grid(row=0, column=8, padx=2)

        table_cards = ttk.Frame(parent)
        table_cards.pack(fill="both", expand=True)
        table_cards.columnconfigure((0, 1), weight=1)

        dealer_frame = ttk.LabelFrame(table_cards, text="Dealer", padding=10)
        player_frame = ttk.LabelFrame(table_cards, text="Player", padding=10)
        dealer_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        player_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.dealer_cards_label = ttk.Label(dealer_frame, text="No hand", font=("TkDefaultFont", 16, "bold"))
        self.dealer_total_label = ttk.Label(dealer_frame, text="")
        self.dealer_cards_label.pack(anchor="w")
        self.dealer_total_label.pack(anchor="w", pady=(6, 0))

        self.player_cards_label = ttk.Label(player_frame, text="No hand", font=("TkDefaultFont", 16, "bold"))
        self.player_total_label = ttk.Label(player_frame, text="")
        self.player_cards_label.pack(anchor="w")
        self.player_total_label.pack(anchor="w", pady=(6, 0))

        self.table_feedback_label = ttk.Label(parent, text="Click Deal Hand to start a round.")
        self.table_feedback_label.pack(fill="x", pady=(8, 8))

        table_stats = ttk.LabelFrame(parent, text="Table Stats", padding=10)
        table_stats.pack(fill="x")
        self.table_stats_label = ttk.Label(table_stats, text="")
        self.table_stats_label.pack(anchor="w")

    def _bind_hotkeys(self) -> None:
        self.root.bind("<space>", lambda _: self.deal_practice_card())
        self.root.bind("-", lambda _: self.submit_guess(-1))
        self.root.bind("0", lambda _: self.submit_guess(0))
        self.root.bind("=", lambda _: self.submit_guess(1))
        self.root.bind("+", lambda _: self.submit_guess(1))

    def _set_guess_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.minus_btn.config(state=state)
        self.zero_btn.config(state=state)
        self.plus_btn.config(state=state)

    def _format_cards(self, cards: list[Card], hide_second: bool = False) -> str:
        if not cards:
            return "No cards"
        parts: list[str] = []
        for idx, card in enumerate(cards):
            if hide_second and idx == 1:
                parts.append("??")
            else:
                parts.append(card.display)
        return "  ".join(parts)

    def _update_global_info(self) -> None:
        true_count = 0.0
        if self.engine.shoe.decks_remaining > 0:
            true_count = self.engine.running_count / self.engine.shoe.decks_remaining
        self.global_count_label.config(
            text=f"Actual running count: {self.engine.running_count:+d} | Estimated true count: {true_count:+.2f}"
        )
        self.global_shoe_label.config(
            text=(
                f"Cards left: {self.engine.shoe.cards_remaining} | "
                f"Penetration: {self.engine.shoe.penetration * 100:.1f}% | "
                f"Cut card: {self.engine.shoe.cut_index}/{self.engine.shoe.total_cards}"
            )
        )
        if self.engine.pending_shuffle:
            self.global_status_label.config(text="Status: Cut card reached - next card/hand reshuffles automatically.")
        else:
            self.global_status_label.config(text="Status: In current shoe.")

    def _update_practice_info(self) -> None:
        accuracy = 0.0
        if self.practice_total > 0:
            accuracy = 100.0 * self.practice_correct / self.practice_total
        self.practice_accuracy_label.config(
            text=f"Answers: {self.practice_correct}/{self.practice_total} ({accuracy:.1f}% accuracy)"
        )
        self.practice_counts_label.config(
            text=(
                f"Your drill running count: {self.practice_user_running_count:+d} | "
                f"Actual running count: {self.engine.running_count:+d}"
            )
        )

    def _update_table_info(self) -> None:
        self.bankroll_label.config(text=f"${self.engine.bankroll:,.2f}")

        hide_dealer = self.engine.round_active and not self.engine.dealer_revealed
        self.dealer_cards_label.config(text=self._format_cards(self.engine.dealer_cards, hide_second=hide_dealer))
        self.player_cards_label.config(text=self._format_cards(self.engine.player_cards))

        if self.engine.dealer_cards:
            if hide_dealer:
                visible_total, _ = hand_value(self.engine.dealer_cards[:1])
                self.dealer_total_label.config(text=f"Visible total: {visible_total}")
            else:
                dealer_total, dealer_soft = hand_value(self.engine.dealer_cards)
                soft_mark = " (soft)" if dealer_soft else ""
                self.dealer_total_label.config(text=f"Total: {dealer_total}{soft_mark}")
        else:
            self.dealer_total_label.config(text="Total: -")

        if self.engine.player_cards:
            player_total, player_soft = hand_value(self.engine.player_cards)
            soft_mark = " (soft)" if player_soft else ""
            self.player_total_label.config(text=f"Total: {player_total}{soft_mark}")
        else:
            self.player_total_label.config(text="Total: -")

        self.table_stats_label.config(
            text=(
                f"Hands: {self.engine.hands_played} | Wins: {self.engine.hands_won} | "
                f"Losses: {self.engine.hands_lost} | Pushes: {self.engine.hands_push} | "
                f"Blackjacks: {self.engine.hands_blackjack} | Surrenders: {self.engine.hands_surrendered}"
            )
        )

        in_hand = self.engine.round_active
        double_ok = (
            in_hand
            and self.engine.can_double
            and len(self.engine.player_cards) == 2
            and self.engine.bankroll >= self.engine.current_bet
        )
        surrender_ok = in_hand and self.engine.can_surrender and len(self.engine.player_cards) == 2

        self.deal_hand_btn.config(state="disabled" if in_hand else "normal")
        self.hit_btn.config(state="normal" if in_hand else "disabled")
        self.stand_btn.config(state="normal" if in_hand else "disabled")
        self.double_btn.config(state="normal" if double_ok else "disabled")
        self.surrender_btn.config(state="normal" if surrender_ok else "disabled")

    def _update_all_views(self) -> None:
        self._update_global_info()
        self._update_practice_info()
        self._update_table_info()

    def manual_shuffle(self) -> None:
        if self.engine.round_active:
            self.table_feedback_label.config(text="Finish the current hand before shuffling.")
            return
        self.engine.shuffle_new_shoe()
        self.current_practice_card = None
        self.practice_user_running_count = 0
        self.practice_card_label.config(text="Shoe shuffled. Deal Practice Card.")
        self.practice_feedback_label.config(text="New shoe started. Running counts reset.")
        self._set_guess_enabled(False)
        self._update_all_views()

    def reset_practice_stats(self) -> None:
        self.practice_correct = 0
        self.practice_total = 0
        self.practice_user_running_count = 0
        self.current_practice_card = None
        self.practice_card_label.config(text="Drill reset. Deal Practice Card.")
        self.practice_feedback_label.config(text="Hi-Lo: 2-6=+1, 7-9=0, 10-A=-1")
        self._set_guess_enabled(False)
        self._update_all_views()

    def deal_practice_card(self) -> None:
        if self.current_practice_card is not None:
            self.practice_feedback_label.config(text="Classify the current card first (-1, 0, +1).")
            return
        if self.engine.round_active:
            self.practice_feedback_label.config(text="Finish the blackjack hand first.")
            return

        self.current_practice_card = self.engine.draw_practice_card()
        self.practice_card_label.config(text=self.current_practice_card.display)
        self._set_guess_enabled(True)
        self._update_all_views()

    def submit_guess(self, guess: int) -> None:
        if self.current_practice_card is None:
            self.practice_feedback_label.config(text="Deal a practice card first.")
            return

        expected = hi_lo_value(self.current_practice_card.rank)
        self.practice_total += 1
        self.practice_user_running_count += guess

        if guess == expected:
            self.practice_correct += 1
            self.practice_feedback_label.config(
                text=f"Correct: {self.current_practice_card.display} is {expected:+d}."
            )
        else:
            self.practice_feedback_label.config(
                text=f"Incorrect: {self.current_practice_card.display} is {expected:+d}."
            )

        self.current_practice_card = None
        self._set_guess_enabled(False)
        self._update_all_views()

    def _parse_bet(self) -> float | None:
        raw_bet = self.bet_var.get().strip()
        try:
            bet = float(raw_bet)
        except ValueError:
            self.table_feedback_label.config(text="Enter a valid numeric bet.")
            return None
        if bet <= 0:
            self.table_feedback_label.config(text="Bet must be greater than zero.")
            return None
        return round(bet, 2)

    def deal_hand(self) -> None:
        bet = self._parse_bet()
        if bet is None:
            return
        ok, message = self.engine.start_round(bet)
        self.table_feedback_label.config(text=message)
        self._update_all_views()
        if ok and not self.engine.round_active and self.engine.pending_shuffle:
            self.table_feedback_label.config(
                text=f"{message} Cut card reached: shoe will reshuffle before next hand."
            )

    def hit_hand(self) -> None:
        ok, message = self.engine.hit()
        self.table_feedback_label.config(text=message)
        self._update_all_views()
        if ok and not self.engine.round_active and self.engine.pending_shuffle:
            self.table_feedback_label.config(
                text=f"{message} Cut card reached: shoe will reshuffle before next hand."
            )

    def stand_hand(self) -> None:
        ok, message = self.engine.stand()
        self.table_feedback_label.config(text=message)
        self._update_all_views()
        if ok and not self.engine.round_active and self.engine.pending_shuffle:
            self.table_feedback_label.config(
                text=f"{message} Cut card reached: shoe will reshuffle before next hand."
            )

    def double_hand(self) -> None:
        ok, message = self.engine.double()
        self.table_feedback_label.config(text=message)
        self._update_all_views()
        if ok and not self.engine.round_active and self.engine.pending_shuffle:
            self.table_feedback_label.config(
                text=f"{message} Cut card reached: shoe will reshuffle before next hand."
            )

    def surrender_hand(self) -> None:
        ok, message = self.engine.surrender()
        self.table_feedback_label.config(text=message)
        self._update_all_views()
        if ok and not self.engine.round_active and self.engine.pending_shuffle:
            self.table_feedback_label.config(
                text=f"{message} Cut card reached: shoe will reshuffle before next hand."
            )


def main() -> None:
    if tk is None:
        print("Tkinter is not installed in this Python environment.")
        print("Install Tk support, then run: python3 blackjack_counter_app.py")
        if TK_IMPORT_ERROR is not None:
            print(f"Details: {TK_IMPORT_ERROR}")
        return

    root = tk.Tk()
    CountingPracticeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
