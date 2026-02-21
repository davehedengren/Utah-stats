#!/usr/bin/env python3
"""
Bank Dice Game Simulator
========================
Simulates the push-your-luck dice game "Bank" with multiple AI strategies
to find the optimal approach.

Rules:
- Players take turns rolling 2 dice; a cumulative pot ("the bank") builds each round.
- First 3 rolls of a round: rolling a 7 = 70 points added to pot; doubles = face value only.
- Rolls 4+: rolling a 7 = round ends, all unbanked players score 0; doubles = double the pot.
- Any player may "bank" before any roll to lock in the current pot as personal score.
- After 20 rounds the highest total score wins.
"""

import random
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RoundState:
    """Snapshot visible to every strategy each time a banking decision is needed."""
    pot: int                   # current cumulative pot this round
    roll_number: int           # how many rolls have happened so far this round (1-indexed)
    round_number: int          # which round we're in (1-indexed)
    my_total_score: int        # this player's banked total across all rounds
    leader_score: int          # highest total score among all players
    players_remaining: int     # how many players still haven't banked this round
    total_players: int         # total player count in the game
    rounds_left: int           # rounds remaining after this one


@dataclass
class PlayerResult:
    """Tracks one player's full game results."""
    name: str
    strategy_name: str
    total_score: int = 0
    round_scores: list = field(default_factory=list)
    banks_called: int = 0
    sevens_hit: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Strategies
# ──────────────────────────────────────────────────────────────────────────────

class Strategy(ABC):
    """Base class for all banking strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def should_bank(self, state: RoundState) -> bool:
        """Return True to bank the current pot, False to stay in."""
        ...


class AlwaysAfterN(Strategy):
    """Banks after a fixed number of rolls have occurred."""

    def __init__(self, n: int):
        self._n = n

    @property
    def name(self) -> str:
        return f"Bank-After-{self._n}"

    @property
    def description(self) -> str:
        return f"Always banks after {self._n} rolls (stays safe through first 3 free rolls)"

    def should_bank(self, state: RoundState) -> bool:
        return state.roll_number >= self._n


class ThresholdStrategy(Strategy):
    """Banks once the pot reaches a target value."""

    def __init__(self, threshold: int):
        self._threshold = threshold

    @property
    def name(self) -> str:
        return f"Threshold-{self._threshold}"

    @property
    def description(self) -> str:
        return f"Banks when pot reaches {self._threshold} points"

    def should_bank(self, state: RoundState) -> bool:
        return state.pot >= self._threshold


class ProbabilityAware(Strategy):
    """Uses multi-step expected value analysis. One-step EV of continuing is
    always positive, but compound risk over multiple rolls means you must
    eventually bank. This strategy uses cumulative bust probability and
    pot size to find the optimal stopping point."""

    @property
    def name(self) -> str:
        return "EV-Optimizer"

    @property
    def description(self) -> str:
        return "Banks using compound-risk analysis (cumulative bust probability vs pot size)"

    def should_bank(self, state: RoundState) -> bool:
        if state.roll_number <= 3:
            return False
        rolls_past_safe = state.roll_number - 3
        # Probability of surviving k MORE rolls without a 7: (5/6)^k
        # After rolls_past_safe risky rolls, we've already survived.
        # Key question: is it worth taking one MORE roll?
        #
        # If we bank now: guaranteed pot
        # If we continue 1 more roll:
        #   P(7)=1/6 → 0, P(doubles)=1/6 → 2*pot, P(normal)=4/6 → pot+~7.7
        #   EV(1 more) = (1/6)*0 + (1/6)*2*pot + (4/6)*(pot+7.7) = pot*5/6 + 5.13
        #   This is always < pot when pot > 30.8... wait, no:
        #   pot*5/6 + 5.13 vs pot → 5.13 vs pot/6 → bank when pot > 30.8
        #
        # BUT: after that roll we face the same decision again. If we keep rolling
        # the compound bust probability 1-(5/6)^k grows fast. The optimal strategy
        # accounts for the FULL trajectory: we should bank when marginal gain
        # per roll is small relative to the pot at risk.
        #
        # Practical heuristic: bank when compound bust probability is high,
        # OR when pot is large enough that one more roll's marginal gain is
        # small relative to what's at risk.
        compound_bust = 1 - (5 / 6) ** rolls_past_safe
        marginal_gain = 7.7  # average gain from a normal (non-seven, non-double) roll
        # The higher the pot, the less valuable marginal_gain is proportionally
        # Bank when: risk of losing pot outweighs marginal improvement
        # risk_cost = (1/6) * pot, benefit = (5/6) * marginal_gain_effective
        # Including doubles: effective_benefit = (4/6)*7.7 + (1/6)*pot ≈ 5.13 + pot/6
        # So one-step EV = pot + 5.13 - pot = +5.13 (always positive one-step)
        #
        # Multi-step: expected final payoff if we continue optimally for k rolls:
        # E = (5/6)^k * pot * growth^k  — this peaks then declines
        # Optimal stopping: bank when the marginal roll's risk exceeds its benefit
        # given that we'll bank next turn anyway.
        #
        # Simple & effective: bank when compound bust > threshold that scales
        # with pot size. Small pot = tolerate more risk; big pot = lock it in.
        risk_tolerance = max(0.30, 0.65 - state.pot / 800)
        return compound_bust >= risk_tolerance


class AdaptiveStrategy(Strategy):
    """Adjusts risk tolerance based on score gap with the leader
    and how many rounds remain."""

    @property
    def name(self) -> str:
        return "Adaptive"

    @property
    def description(self) -> str:
        return "Adjusts risk based on score gap vs leader and rounds remaining"

    def should_bank(self, state: RoundState) -> bool:
        if state.roll_number <= 3:
            return False
        gap = state.leader_score - state.my_total_score
        rounds_left = max(state.rounds_left, 1)
        # How much we need per round to catch up
        needed_per_round = gap / rounds_left if gap > 0 else 0
        # If we're behind, stay in longer; if we're leading, bank earlier
        risk_threshold = max(4, min(12, 4 + int(needed_per_round / 15)))
        return state.roll_number >= risk_threshold


class ConservativeStrategy(Strategy):
    """Banks as soon as the safe rolls are over."""

    @property
    def name(self) -> str:
        return "Conservative"

    @property
    def description(self) -> str:
        return "Banks immediately after the 3 safe rolls"

    def should_bank(self, state: RoundState) -> bool:
        return state.roll_number >= 3


class AggressiveStrategy(Strategy):
    """Stays in until the pot is huge or many rolls have passed."""

    @property
    def name(self) -> str:
        return "Aggressive"

    @property
    def description(self) -> str:
        return "Stays in until roll 10 or pot > 300"

    def should_bank(self, state: RoundState) -> bool:
        return state.roll_number >= 10 or state.pot > 300


class DoubleChaser(Strategy):
    """Stays in after roll 3 hoping for a doubles to double the pot.
    Detects a likely doubles hit by tracking pot growth, then banks.
    Gives up and banks after roll 8 regardless."""

    def __init__(self):
        self._prev_pot = 0

    @property
    def name(self) -> str:
        return "Double-Chaser"

    @property
    def description(self) -> str:
        return "Waits for pot to spike (doubles), then banks; bails by roll 8"

    def should_bank(self, state: RoundState) -> bool:
        if state.roll_number <= 3:
            self._prev_pot = state.pot
            return False
        # Bail after too many rolls without luck
        if state.roll_number >= 8:
            return True
        # Detect a likely doubles hit: pot roughly doubled or more since last check
        if self._prev_pot > 0 and state.pot >= self._prev_pot * 1.8:
            return True
        self._prev_pot = state.pot
        return False


class ProportionalRisk(Strategy):
    """Banks with probability proportional to roll number and pot size."""

    @property
    def name(self) -> str:
        return "Proportional-Risk"

    @property
    def description(self) -> str:
        return "Probabilistically banks more as rolls/pot increase"

    def should_bank(self, state: RoundState) -> bool:
        if state.roll_number <= 3:
            return False
        # Chance of banking increases with roll count and pot size
        roll_factor = (state.roll_number - 3) * 0.12
        pot_factor = min(state.pot / 500, 0.5)
        p_bank = min(roll_factor + pot_factor, 0.95)
        return random.random() < p_bank


class EndgameRush(Strategy):
    """Conservative early, but goes all-in during the last few rounds
    if trailing the leader."""

    @property
    def name(self) -> str:
        return "Endgame-Rush"

    @property
    def description(self) -> str:
        return "Conservative early, aggressive in final rounds if behind"

    def should_bank(self, state: RoundState) -> bool:
        if state.roll_number <= 3:
            return False
        behind = state.leader_score - state.my_total_score
        if state.rounds_left <= 4 and behind > 30:
            # Desperate mode: stay in longer
            return state.roll_number >= 9 or state.pot > 250
        # Normal mode: bank after roll 5
        return state.roll_number >= 5


# ──────────────────────────────────────────────────────────────────────────────
# Game Engine
# ──────────────────────────────────────────────────────────────────────────────

class BankDiceGame:
    """Simulates one full game of Bank."""

    def __init__(self, strategies: list[Strategy], num_rounds: int = 20):
        self.strategies = strategies
        self.num_rounds = num_rounds
        self.players = [
            PlayerResult(name=f"P{i+1}", strategy_name=s.name)
            for i, s in enumerate(strategies)
        ]

    def _roll_dice(self) -> tuple[int, int]:
        return random.randint(1, 6), random.randint(1, 6)

    def play(self) -> list[PlayerResult]:
        for round_num in range(1, self.num_rounds + 1):
            self._play_round(round_num)
        return self.players

    def _play_round(self, round_num: int):
        pot = 0
        roll_count = 0
        # Track who is still "in" this round (hasn't banked)
        still_in = [True] * len(self.strategies)
        round_banked = [0] * len(self.strategies)

        while any(still_in):
            # --- Banking phase: each player still in decides whether to bank ---
            leader_score = max(p.total_score for p in self.players)
            players_remaining = sum(still_in)
            for i, strategy in enumerate(self.strategies):
                if not still_in[i]:
                    continue
                state = RoundState(
                    pot=pot,
                    roll_number=roll_count,
                    round_number=round_num,
                    my_total_score=self.players[i].total_score,
                    leader_score=leader_score,
                    players_remaining=players_remaining,
                    total_players=len(self.strategies),
                    rounds_left=self.num_rounds - round_num,
                )
                if roll_count > 0 and strategy.should_bank(state):
                    still_in[i] = False
                    round_banked[i] = pot
                    self.players[i].banks_called += 1

            if not any(still_in):
                break

            # --- Roll phase ---
            d1, d2 = self._roll_dice()
            roll_count += 1
            total = d1 + d2
            is_double = d1 == d2
            is_seven = total == 7

            if roll_count <= 3:
                # Phase 1: 7 = 70 pts, doubles = face value only
                if is_seven:
                    pot += 70
                elif is_double:
                    pot += total  # face value
                else:
                    pot += total
            else:
                # Phase 2: 7 = round over, doubles = double the pot
                if is_seven:
                    # Everyone still in gets 0
                    for i in range(len(self.strategies)):
                        if still_in[i]:
                            round_banked[i] = 0
                            still_in[i] = False
                            self.players[i].sevens_hit += 1
                    break
                elif is_double:
                    pot *= 2
                else:
                    pot += total

        # Apply round scores
        for i, player in enumerate(self.players):
            player.total_score += round_banked[i]
            player.round_scores.append(round_banked[i])


# ──────────────────────────────────────────────────────────────────────────────
# Simulation Runner
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StrategyStats:
    name: str
    description: str
    wins: int = 0
    total_score: int = 0
    scores: list = field(default_factory=list)
    placements: list = field(default_factory=list)
    banks_called: list = field(default_factory=list)
    sevens_hit: list = field(default_factory=list)
    round_scores_all: list = field(default_factory=list)


def run_simulation(
    strategies: list[Strategy],
    num_games: int = 10_000,
    num_rounds: int = 20,
) -> dict[str, StrategyStats]:
    """Run many games and collect aggregate statistics."""
    stats = {
        s.name: StrategyStats(name=s.name, description=s.description)
        for s in strategies
    }

    for _ in range(num_games):
        # Shuffle turn order each game so no positional bias
        indices = list(range(len(strategies)))
        random.shuffle(indices)
        shuffled = [strategies[i] for i in indices]

        game = BankDiceGame(shuffled, num_rounds)
        results = game.play()

        # Determine winner(s)
        max_score = max(r.total_score for r in results)
        sorted_scores = sorted([r.total_score for r in results], reverse=True)

        for r in results:
            st = stats[r.strategy_name]
            st.scores.append(r.total_score)
            st.total_score += r.total_score
            st.banks_called.append(r.banks_called)
            st.sevens_hit.append(r.sevens_hit)
            placement = sorted_scores.index(r.total_score) + 1
            st.placements.append(placement)
            st.round_scores_all.extend(r.round_scores)
            if r.total_score == max_score:
                st.wins += 1

    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Rich Terminal UX
# ──────────────────────────────────────────────────────────────────────────────

def display_results(stats: dict[str, StrategyStats], num_games: int, num_rounds: int):
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich.bar import Bar
    from rich import box

    console = Console()

    # ── Header ──
    console.print()
    title = Text("BANK DICE GAME SIMULATOR", style="bold bright_white on blue")
    title.align("center", width=70)
    console.print(Panel(title, border_style="bright_blue", padding=(1, 2)))

    # ── Config ──
    config_text = (
        f"[bold]Games simulated:[/] [cyan]{num_games:,}[/]  |  "
        f"[bold]Rounds per game:[/] [cyan]{num_rounds}[/]  |  "
        f"[bold]Strategies tested:[/] [cyan]{len(stats)}[/]"
    )
    console.print(Panel(config_text, title="Configuration", border_style="dim"))

    # ── Main Results Table ──
    sorted_stats = sorted(stats.values(), key=lambda s: s.wins, reverse=True)

    table = Table(
        title="Strategy Performance Rankings",
        box=box.ROUNDED,
        title_style="bold bright_yellow",
        header_style="bold bright_white on dark_green",
        show_lines=True,
        padding=(0, 1),
    )
    table.add_column("Rank", justify="center", style="bold", width=5)
    table.add_column("Strategy", style="bright_cyan", min_width=20)
    table.add_column("Win Rate", justify="center", style="bold", min_width=10)
    table.add_column("Avg Score", justify="right", min_width=10)
    table.add_column("Median", justify="right", min_width=8)
    table.add_column("Std Dev", justify="right", min_width=8)
    table.add_column("Best", justify="right", min_width=8)
    table.add_column("Avg Place", justify="center", min_width=9)
    table.add_column("Avg Banks", justify="center", min_width=9)
    table.add_column("Avg 7s Hit", justify="center", min_width=9)

    medal = {1: "[bright_yellow]1st[/]", 2: "[white]2nd[/]", 3: "[rgb(205,127,50)]3rd[/]"}

    for rank, st in enumerate(sorted_stats, 1):
        win_pct = st.wins / num_games * 100
        avg_score = statistics.mean(st.scores)
        median_score = statistics.median(st.scores)
        std_score = statistics.stdev(st.scores) if len(st.scores) > 1 else 0
        best_score = max(st.scores)
        avg_place = statistics.mean(st.placements)
        avg_banks = statistics.mean(st.banks_called)
        avg_sevens = statistics.mean(st.sevens_hit)

        # Color win rate
        if win_pct >= 20:
            wr_style = "bold bright_green"
        elif win_pct >= 10:
            wr_style = "bright_yellow"
        else:
            wr_style = "bright_red"

        rank_str = medal.get(rank, str(rank))

        table.add_row(
            rank_str,
            st.name,
            f"[{wr_style}]{win_pct:.1f}%[/]",
            f"{avg_score:,.0f}",
            f"{median_score:,.0f}",
            f"{std_score:,.0f}",
            f"{best_score:,}",
            f"{avg_place:.2f}",
            f"{avg_banks:.1f}",
            f"{avg_sevens:.1f}",
        )

    console.print()
    console.print(table)

    # ── Win Rate Bar Chart ──
    console.print()
    bar_table = Table(
        title="Win Rate Distribution",
        box=box.SIMPLE_HEAVY,
        title_style="bold bright_yellow",
        header_style="bold",
        show_edge=False,
        padding=(0, 1),
    )
    bar_table.add_column("Strategy", style="bright_cyan", min_width=20)
    bar_table.add_column("Win %", justify="right", min_width=7)
    bar_table.add_column("Bar", min_width=40)

    max_win_pct = max(s.wins / num_games * 100 for s in sorted_stats)

    for st in sorted_stats:
        win_pct = st.wins / num_games * 100
        bar_len = int(win_pct / max(max_win_pct, 1) * 35)
        bar_char = "█" * bar_len + "░" * (35 - bar_len)
        if win_pct >= 20:
            color = "bright_green"
        elif win_pct >= 10:
            color = "bright_yellow"
        else:
            color = "bright_red"
        bar_table.add_row(st.name, f"{win_pct:.1f}%", f"[{color}]{bar_char}[/]")

    console.print(bar_table)

    # ── Score Distribution Box ──
    console.print()
    dist_table = Table(
        title="Score Distribution (per game)",
        box=box.ROUNDED,
        title_style="bold bright_yellow",
        header_style="bold bright_white on dark_blue",
        show_lines=True,
    )
    dist_table.add_column("Strategy", style="bright_cyan", min_width=20)
    dist_table.add_column("Min", justify="right")
    dist_table.add_column("P25", justify="right")
    dist_table.add_column("Median", justify="right")
    dist_table.add_column("P75", justify="right")
    dist_table.add_column("P90", justify="right")
    dist_table.add_column("Max", justify="right")

    for st in sorted_stats:
        scores = sorted(st.scores)
        n = len(scores)
        dist_table.add_row(
            st.name,
            f"{scores[0]:,}",
            f"{scores[n // 4]:,}",
            f"{scores[n // 2]:,}",
            f"{scores[3 * n // 4]:,}",
            f"{scores[int(n * 0.9)]:,}",
            f"{scores[-1]:,}",
        )

    console.print(dist_table)

    # ── Strategy Descriptions ──
    console.print()
    desc_table = Table(
        title="Strategy Descriptions",
        box=box.ROUNDED,
        title_style="bold bright_yellow",
        header_style="bold",
        show_lines=True,
    )
    desc_table.add_column("Strategy", style="bright_cyan", min_width=20)
    desc_table.add_column("Description", style="white", min_width=50)

    for st in sorted_stats:
        desc_table.add_row(st.name, st.description)

    console.print(desc_table)

    # ── Summary Insight ──
    console.print()
    best = sorted_stats[0]
    worst = sorted_stats[-1]
    best_wr = best.wins / num_games * 100
    worst_wr = worst.wins / num_games * 100
    best_avg = statistics.mean(best.scores)
    worst_avg = statistics.mean(worst.scores)

    insight = (
        f"[bold bright_green]{best.name}[/] is the top strategy with a "
        f"[bold]{best_wr:.1f}%[/] win rate and average score of "
        f"[bold]{best_avg:,.0f}[/].\n"
        f"[bold bright_red]{worst.name}[/] performed worst at "
        f"[bold]{worst_wr:.1f}%[/] win rate (avg score [bold]{worst_avg:,.0f}[/]).\n\n"
        f"[dim]Key insight: The winning strategy balances risk after the 3 safe rolls.\n"
        f"Rolling a 7 has a 1-in-6 (16.7%) chance each roll. Doubles (also 1-in-6)\n"
        f"double the entire pot after roll 3, creating high-variance opportunities.[/]"
    )
    console.print(Panel(insight, title="Summary", border_style="bright_green", padding=(1, 2)))

    # ── Game rules reminder ──
    rules = (
        "[bold]Rolls 1-3:[/] 7 = +70 pts | Doubles = face value | Other = face value\n"
        "[bold]Rolls 4+:[/]  7 = round over (unbanked = 0) | Doubles = pot x2 | Other = +face value\n"
        "[bold]Banking:[/]   Lock in current pot as your score anytime before a roll\n"
        "[bold]Winning:[/]   Highest total after 20 rounds wins"
    )
    console.print(Panel(rules, title="Game Rules", border_style="dim", padding=(0, 2)))
    console.print()


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    NUM_GAMES = 100_000
    NUM_ROUNDS = 20

    strategies = [
        ConservativeStrategy(),
        AlwaysAfterN(4),
        AlwaysAfterN(5),
        AlwaysAfterN(6),
        ThresholdStrategy(50),
        ThresholdStrategy(100),
        ThresholdStrategy(150),
        ProbabilityAware(),
        AdaptiveStrategy(),
        AggressiveStrategy(),
        DoubleChaser(),
        ProportionalRisk(),
        EndgameRush(),
    ]

    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

    console = Console()
    console.print()
    console.print("[bold bright_blue]Starting Bank Dice simulation...[/]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Simulating games...", total=NUM_GAMES)

        # Run in batches to update progress bar
        batch_size = 500
        all_stats: Optional[dict[str, StrategyStats]] = None

        for batch_start in range(0, NUM_GAMES, batch_size):
            batch_end = min(batch_start + batch_size, NUM_GAMES)
            batch_count = batch_end - batch_start

            batch_stats = run_simulation(strategies, batch_count, NUM_ROUNDS)

            if all_stats is None:
                all_stats = batch_stats
            else:
                for name, st in batch_stats.items():
                    all_stats[name].wins += st.wins
                    all_stats[name].total_score += st.total_score
                    all_stats[name].scores.extend(st.scores)
                    all_stats[name].placements.extend(st.placements)
                    all_stats[name].banks_called.extend(st.banks_called)
                    all_stats[name].sevens_hit.extend(st.sevens_hit)
                    all_stats[name].round_scores_all.extend(st.round_scores_all)

            progress.update(task, advance=batch_count)

    display_results(all_stats, NUM_GAMES, NUM_ROUNDS)


if __name__ == "__main__":
    main()
