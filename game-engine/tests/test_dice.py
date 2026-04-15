"""
Tests for game_engine.core.dice — dice notation parsing and rolling.
"""

from __future__ import annotations

import random

import pytest

from game_engine.core.dice import (
    parse_notation,
    roll,
    roll_dice,
    roll_with_advantage,
    roll_with_disadvantage,
)

# ---------------------------------------------------------------------------
# parse_notation — valid inputs
# ---------------------------------------------------------------------------


class TestParseNotationValid:
    def test_simple_1d6(self) -> None:
        count, sides, modifier = parse_notation("1d6")
        assert count == 1
        assert sides == 6
        assert modifier == 0

    def test_simple_2d8_plus_3(self) -> None:
        count, sides, modifier = parse_notation("2d8+3")
        assert count == 2
        assert sides == 8
        assert modifier == 3

    def test_simple_1d20_minus_1(self) -> None:
        count, sides, modifier = parse_notation("1d20-1")
        assert count == 1
        assert sides == 20
        assert modifier == -1

    def test_no_leading_count_d6(self) -> None:
        """'d6' should parse as count=1."""
        count, sides, modifier = parse_notation("d6")
        assert count == 1
        assert sides == 6
        assert modifier == 0

    def test_no_leading_count_d20(self) -> None:
        count, sides, modifier = parse_notation("d20")
        assert count == 1
        assert sides == 20
        assert modifier == 0

    def test_large_count_4d6(self) -> None:
        count, sides, modifier = parse_notation("4d6")
        assert count == 4
        assert sides == 6
        assert modifier == 0

    def test_zero_modifier_omitted(self) -> None:
        """Notation without modifier should default to 0."""
        _, _, modifier = parse_notation("3d10")
        assert modifier == 0

    def test_large_sides(self) -> None:
        count, sides, modifier = parse_notation("1d100")
        assert count == 1
        assert sides == 100
        assert modifier == 0

    def test_case_insensitive_d(self) -> None:
        """Uppercase D should work."""
        count, sides, modifier = parse_notation("2D6+1")
        assert count == 2
        assert sides == 6
        assert modifier == 1

    def test_positive_modifier_explicit_plus(self) -> None:
        count, sides, modifier = parse_notation("1d4+5")
        assert modifier == 5

    def test_strip_whitespace(self) -> None:
        count, sides, modifier = parse_notation("  2d6+1  ")
        assert count == 2
        assert sides == 6
        assert modifier == 1


# ---------------------------------------------------------------------------
# parse_notation — invalid inputs
# ---------------------------------------------------------------------------


class TestParseNotationInvalid:
    @pytest.mark.parametrize(
        "notation",
        [
            "abc",
            "",
            "d",
            "2d",
            "d+1",
            "2d6x3",  # unsupported keep-highest notation "kh"
            "notadice",
            "1-d6",
        ],
    )
    def test_raises_value_error(self, notation: str) -> None:
        with pytest.raises(ValueError):
            parse_notation(notation)

    def test_4d6kh3_raises_value_error(self) -> None:
        """Keep-highest notation is not supported; should raise ValueError."""
        with pytest.raises(ValueError):
            parse_notation("4d6kh3")


# ---------------------------------------------------------------------------
# roll_dice — value range
# ---------------------------------------------------------------------------


class TestRollDice:
    def test_roll_1d6_in_range(self) -> None:
        for _ in range(50):
            total, rolls = roll_dice(1, 6)
            assert 1 <= total <= 6
            assert len(rolls) == 1

    def test_roll_2d8_plus_3_in_range(self) -> None:
        for _ in range(50):
            total, rolls = roll_dice(2, 8, 3)
            assert 5 <= total <= 19  # 2*[1..8]+3
            assert len(rolls) == 2
            assert all(1 <= r <= 8 for r in rolls)

    def test_roll_1d1_always_one(self) -> None:
        """A d1 has only one face and must always return 1 (plus modifier)."""
        for _ in range(20):
            total, rolls = roll_dice(1, 1)
            assert total == 1
            assert rolls == [1]

    def test_roll_1d1_with_modifier(self) -> None:
        total, rolls = roll_dice(1, 1, 5)
        assert total == 6

    def test_zero_dice_returns_modifier(self) -> None:
        total, rolls = roll_dice(0, 6, 4)
        assert total == 4
        assert rolls == []

    def test_negative_sides_raises(self) -> None:
        with pytest.raises(ValueError):
            roll_dice(1, 0)

    def test_negative_count_raises(self) -> None:
        with pytest.raises(ValueError):
            roll_dice(-1, 6)

    def test_roll_returns_tuple(self) -> None:
        result = roll_dice(1, 6)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_individual_rolls_count_matches(self) -> None:
        _, rolls = roll_dice(5, 10)
        assert len(rolls) == 5


# ---------------------------------------------------------------------------
# roll — convenience wrapper
# ---------------------------------------------------------------------------


class TestRoll:
    def test_roll_1d6(self) -> None:
        for _ in range(30):
            total, rolls = roll("1d6")
            assert 1 <= total <= 6

    def test_roll_2d8_plus_3(self) -> None:
        for _ in range(30):
            total, _ = roll("2d8+3")
            assert 5 <= total <= 19

    def test_roll_d20(self) -> None:
        for _ in range(50):
            total, _ = roll("d20")
            assert 1 <= total <= 20

    def test_roll_invalid_notation_raises(self) -> None:
        with pytest.raises(ValueError):
            roll("invalid")


# ---------------------------------------------------------------------------
# Reproducibility with random.seed
# ---------------------------------------------------------------------------


class TestReproducibility:
    def test_same_seed_same_result_roll_dice(self) -> None:
        random.seed(42)
        total_a, rolls_a = roll_dice(3, 6, 2)

        random.seed(42)
        total_b, rolls_b = roll_dice(3, 6, 2)

        assert total_a == total_b
        assert rolls_a == rolls_b

    def test_same_seed_same_result_roll(self) -> None:
        random.seed(99)
        total_a, _ = roll("2d10+1")

        random.seed(99)
        total_b, _ = roll("2d10+1")

        assert total_a == total_b

    def test_different_seeds_may_differ(self) -> None:
        """Not guaranteed, but very likely to differ across many iterations."""
        results = set()
        for seed in range(30):
            random.seed(seed)
            total, _ = roll_dice(1, 20)
            results.add(total)
        assert len(results) > 1  # at least two distinct results


# ---------------------------------------------------------------------------
# Advantage / disadvantage
# ---------------------------------------------------------------------------


class TestAdvantageDisadvantage:
    def test_advantage_returns_max(self) -> None:
        for _ in range(50):
            total, rolls = roll_with_advantage(20)
            assert total == max(rolls)
            assert len(rolls) == 2

    def test_disadvantage_returns_min(self) -> None:
        for _ in range(50):
            total, rolls = roll_with_disadvantage(20)
            assert total == min(rolls)
            assert len(rolls) == 2

    def test_advantage_in_range(self) -> None:
        for _ in range(50):
            total, _ = roll_with_advantage(20)
            assert 1 <= total <= 20

    def test_disadvantage_in_range(self) -> None:
        for _ in range(50):
            total, _ = roll_with_disadvantage(20)
            assert 1 <= total <= 20

    def test_advantage_invalid_sides_raises(self) -> None:
        with pytest.raises(ValueError):
            roll_with_advantage(0)

    def test_disadvantage_invalid_sides_raises(self) -> None:
        with pytest.raises(ValueError):
            roll_with_disadvantage(0)
