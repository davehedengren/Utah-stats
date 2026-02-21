# Bank Dice Game — Strategy Definitions

## Game Rules Quick Reference

- **2 dice** are rolled each turn; a cumulative pot builds throughout each round.
- **Rolls 1–3 (Safe Zone):** Rolling a 7 adds **70 points** to the pot. Doubles add face value only. All other rolls add face value.
- **Rolls 4+ (Danger Zone):** Rolling a 7 **ends the round** — all unbanked players score **0**. Doubles **double the entire pot**. All other rolls add face value.
- **Banking:** Any player can call "Bank" before any roll to lock in the current pot as personal score for that round.
- **Winning:** Highest total score after **20 rounds** wins.

**Key probabilities (2 dice):**
| Outcome | Probability |
|---------|-------------|
| Rolling a 7 | 6/36 = 16.7% |
| Rolling doubles | 6/36 = 16.7% |
| Other result | 24/36 = 66.7% |

---

## Strategies

### 1. Conservative

**Rule:** Banks immediately after the 3 safe rolls (banks at roll 3).

**Philosophy:** Take the guaranteed points from the safe zone and never risk the danger zone. Prioritizes consistency over upside.

**Strengths:** Very low variance; almost never scores 0 in a round. Reliable floor.

**Weaknesses:** Misses all doubles-doubling opportunities in the danger zone, leading to consistently lower scores than bolder strategies.

---

### 2. Bank-After-N (N = 4, 5, 6)

**Rule:** Stays in for exactly N rolls, then banks. Three variants tested: N=4, N=5, N=6.

**Philosophy:** Take a controlled number of extra rolls in the danger zone. Each additional roll risks a 7 (16.7%) but gains ~7.7 average points or a chance at a pot-doubling doubles.

**Strengths:** Simple and predictable. Easy to follow in a real game.

**Weaknesses:** Doesn't adapt to pot size or game state. N=4 is too cautious, N=6 is moderate.

| Variant | Extra risky rolls | Cumulative bust chance |
|---------|-------------------|----------------------|
| Bank-After-4 | 1 | 16.7% |
| Bank-After-5 | 2 | 30.6% |
| Bank-After-6 | 3 | 42.1% |

---

### 3. Threshold-N (N = 50, 100, 150)

**Rule:** Banks as soon as the pot reaches N points, regardless of roll count.

**Philosophy:** Focus on the pot's value rather than roll count. Different thresholds represent different risk appetites.

**Strengths:** Adapts to lucky/unlucky streaks — banks fast when dice run hot (especially after doubles), stays in when the pot is small.

**Weaknesses:** In rounds with mostly low rolls, Threshold-150 may stay in for many rolls chasing a target it can't safely reach. Threshold-50 banks too early and misses upside.

| Variant | Target pot | Typical behavior |
|---------|-----------|-----------------|
| Threshold-50 | 50 pts | Banks very early, often during safe zone |
| Threshold-100 | 100 pts | Banks after ~5–7 rolls typically |
| Threshold-150 | 150 pts | Stays in longer, captures doubles spikes |

---

### 4. EV-Optimizer

**Rule:** Uses compound bust-probability analysis. Calculates the cumulative probability of having been eliminated by a 7 given how many danger-zone rolls have passed, then compares it to a risk tolerance that shrinks as the pot grows (bigger pot = bank sooner).

**Formula:**
```
compound_bust = 1 - (5/6)^(rolls_past_safe_zone)
risk_tolerance = max(0.30, 0.65 - pot / 800)
Bank when: compound_bust >= risk_tolerance
```

**Philosophy:** One-step expected value of continuing is always positive (+5.13 points on average), but multi-step compound risk means you'll eventually bust if you never bank. This strategy finds the sweet spot where marginal gain per roll no longer justifies the accumulated risk.

**Strengths:** Mathematically grounded. Adapts to both roll count AND pot size. Banks earlier when the pot is large (more to lose) and later when the pot is small (less to lose).

**Weaknesses:** The heuristic approximates but doesn't solve the full dynamic programming problem. Outperformed by simpler aggressive strategies in practice because Bank's doubles mechanic rewards high-variance play.

---

### 5. Adaptive

**Rule:** Adjusts how long it stays in based on the score gap between itself and the leader, scaled by how many rounds remain.

**Formula:**
```
needed_per_round = (leader_score - my_score) / rounds_remaining
risk_threshold = clamp(4 + needed_per_round / 15, min=4, max=12)
Bank when: roll_number >= risk_threshold
```

**Philosophy:** If you're winning, play it safe. If you're losing, take bigger risks to catch up. The fewer rounds remain, the more desperate the play.

**Strengths:** Game-aware — the only strategy that reacts to opponent scores. Can make dramatic comebacks.

**Weaknesses:** When behind by a lot, can enter a "death spiral" of excessive risk-taking. Extremely high variance (max scores of 39,000+ observed, but also many rounds of 0).

---

### 6. Aggressive

**Rule:** Stays in until roll 10 OR the pot exceeds 300 points.

**Philosophy:** Maximize exposure to the doubles-doubling mechanic. Every extra roll past the safe zone has a 1-in-6 chance of doubling the entire pot. Stay in long enough and you'll hit multiple doubles.

**Strengths:** Highest average score and highest win rate across all simulations. The pot-doubling mechanic in Bank is so powerful that tolerating the 7-risk pays off over many games.

**Weaknesses:** Highest variance. Can score 0 frequently when 7s hit. Not ideal for single-game play where consistency matters.

---

### 7. Double-Chaser

**Rule:** After the safe zone, monitors pot growth. If the pot roughly doubles (indicating a doubles roll hit), banks immediately to lock in the windfall. Bails by roll 8 regardless.

**Philosophy:** Stay in specifically to catch one doubles event, then get out. Don't push your luck beyond that.

**Strengths:** Captures the upside of doubles while limiting exposure. Good risk/reward balance.

**Weaknesses:** Can't directly observe dice results (only pot changes), so the detection heuristic can be fooled by sequences of high normal rolls. If no doubles hit by roll 8, banks at a modest pot anyway.

---

### 8. Proportional-Risk

**Rule:** Banks probabilistically — the chance of banking increases with both roll count and pot size. Uses randomization rather than a hard threshold.

**Formula:**
```
roll_factor = (roll_number - 3) * 0.12
pot_factor = min(pot / 500, 0.5)
p_bank = min(roll_factor + pot_factor, 0.95)
Bank with probability p_bank
```

**Philosophy:** Introduce unpredictability. In a real multiplayer game, being predictable lets opponents exploit your timing. This strategy adds noise.

**Strengths:** Hard for opponents to anticipate. Naturally adapts to pot size.

**Weaknesses:** Randomness means inconsistent behavior — sometimes banks too early, sometimes too late. Underperforms deterministic strategies in simulation (where opponents can't exploit predictability anyway).

---

### 9. Endgame-Rush

**Rule:** Plays conservatively for most of the game (banks at roll 5). In the final 4 rounds, if trailing the leader by more than 30 points, switches to aggressive mode (stays until roll 9 or pot > 250).

**Philosophy:** Keep it steady, then go big when it matters most. A controlled version of the Adaptive strategy with a clear trigger.

**Strengths:** Solid baseline performance with comeback potential in late rounds.

**Weaknesses:** The switch point (4 rounds left, 30-point gap) is somewhat arbitrary. The conservative early play means it often falls behind and needs the comeback mode.

---

## Simulation Results Summary (100,000 games)

| Rank | Strategy | Win Rate | Avg Score | Std Dev |
|------|----------|----------|-----------|---------|
| 1 | **Aggressive** | **26.9%** | 1,434 | 564 |
| 2 | Threshold-150 | 19.5% | 1,406 | 427 |
| 3 | Adaptive | 12.7% | 1,283 | 648 |
| 4 | Threshold-100 | 8.9% | 1,328 | 321 |
| 5 | EV-Optimizer | 7.4% | 1,353 | 425 |
| 6 | Bank-After-6 | 6.6% | 1,286 | 416 |
| 7 | Double-Chaser | 5.1% | 1,292 | 363 |
| 8 | Endgame-Rush | 4.5% | 1,264 | 379 |
| 9 | Proportional-Risk | 3.6% | 1,246 | 337 |
| 10 | Bank-After-5 | 2.5% | 1,222 | 329 |
| 11 | Conservative | 1.9% | 1,050 | 183 |
| 12 | Bank-After-4 | 1.7% | 1,143 | 252 |
| 13 | Threshold-50 | 1.4% | 1,034 | 146 |

## Key Takeaway

**Aggressive play wins in Bank.** The doubles mechanic — which doubles the *entire pot* — is so powerful that accepting the 16.7% per-roll bust risk is worth it. The first 3 rolls are completely safe, giving every round a free foundation. The optimal approach is to stay in well past the safe zone and chase doubles, accepting that some rounds will end in 0.
