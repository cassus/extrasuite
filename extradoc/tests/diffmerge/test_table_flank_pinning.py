"""Tests for the table-flank pinning invariant in content alignment.

Google Docs guarantees that every table is immediately preceded AND
immediately followed by a paragraph. When a table is matched across
base/desired, the pre- and post-flank paragraphs must refer to the same
structural slot — even when their text is completely rewritten.

These tests exercise ``_pin_table_flanks`` in isolation via
``align_content``, using synthetic ``StructuralElement`` fixtures.
"""

from __future__ import annotations

from extradoc.diffmerge.content_align import (
    ContentNode,
    align_content,
    content_node_from_element,
)
from tests.diffmerge.helpers import (
    make_para_el,
    make_table_el,
    make_terminal_para,
)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _nodes(elements: list, terminal_at_end: bool = True) -> list[ContentNode]:
    """Build ContentNode list from StructuralElement fixtures."""
    nodes: list[ContentNode] = []
    last = len(elements) - 1
    for i, el in enumerate(elements):
        nodes.append(
            content_node_from_element(el, is_terminal=(terminal_at_end and i == last))
        )
    return nodes


def _match_map(alignment) -> dict[int, int]:
    return {m.base_idx: m.desired_idx for m in alignment.matches}


def _assert_matched(alignment, bi: int, di: int) -> None:
    mm = _match_map(alignment)
    assert bi in mm, f"base index {bi} expected to be matched but was deleted/unmatched"
    assert mm[bi] == di, f"base index {bi} matched desired {mm[bi]}, expected {di}"


def _assert_not_deleted(alignment, bi: int) -> None:
    assert bi not in set(alignment.base_deletes), (
        f"base index {bi} was unexpectedly deleted"
    )


def _assert_not_inserted(alignment, di: int) -> None:
    assert di not in set(alignment.desired_inserts), (
        f"desired index {di} was unexpectedly inserted"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_basic_table_unchanged_flanks_unchanged() -> None:
    """Table + flanks all unchanged — naturally match, pinning is no-op."""
    base_els = [
        make_para_el("Introduction paragraph"),
        make_table_el([["A", "B"], ["C", "D"]]),
        make_para_el("Closing paragraph"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Introduction paragraph"),
        make_table_el([["A", "B"], ["C", "D"]]),
        make_para_el("Closing paragraph"),
        make_terminal_para(),
    ]
    base = _nodes(base_els)
    desired = _nodes(desired_els)
    a = align_content(base, desired)
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)
    _assert_matched(a, 3, 3)


def test_preflank_completely_rewritten() -> None:
    """Pre-flank paragraph completely rewritten — must still match."""
    base_els = [
        make_para_el("Alpha bravo charlie delta echo"),
        make_table_el([["x", "y"]]),
        make_para_el("Closing shared text"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Zulu yankee xray whiskey victor"),
        make_table_el([["x", "y"]]),
        make_para_el("Closing shared text"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)  # pinned even though text totally different
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)
    _assert_not_deleted(a, 0)
    _assert_not_inserted(a, 0)


def test_postflank_completely_rewritten() -> None:
    """Post-flank paragraph completely rewritten — must still match."""
    base_els = [
        make_para_el("Opening shared text"),
        make_table_el([["x", "y"]]),
        make_para_el("Alpha bravo charlie delta echo"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Opening shared text"),
        make_table_el([["x", "y"]]),
        make_para_el("Zulu yankee xray whiskey victor"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)  # pinned even though text totally different


def test_both_flanks_rewritten() -> None:
    """Both flanks completely rewritten — both must be pinned."""
    base_els = [
        make_para_el("Alpha bravo charlie delta echo"),
        make_table_el([["x", "y"]]),
        make_para_el("Foxtrot golf hotel india juliet"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("One two three four five"),
        make_table_el([["x", "y"]]),
        make_para_el("Six seven eight nine ten"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)


def test_table_heavily_modified_flanks_unchanged() -> None:
    """Table rows/cols changed, flanks unchanged — flanks match naturally."""
    base_els = [
        make_para_el("Opening paragraph"),
        make_table_el([["x", "y"], ["z", "w"]]),
        make_para_el("Closing paragraph"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Opening paragraph"),
        make_table_el([["x", "y", "new"], ["z", "w", "added"], ["e", "f", "g"]]),
        make_para_el("Closing paragraph"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)


def test_table_modified_and_both_flanks_rewritten() -> None:
    """Table modified AND both flanks rewritten — everything matches."""
    base_els = [
        make_para_el("Alpha bravo charlie"),
        make_table_el([["x", "y"]]),
        make_para_el("Delta echo foxtrot"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Completely different one"),
        make_table_el([["x", "y"], ["new", "row"]]),
        make_para_el("Completely different two"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)


def test_multiple_tables_with_various_flanks_changed() -> None:
    """Two tables; pre-flank of first changed, post-flank of second changed."""
    base_els = [
        make_para_el("Alpha bravo charlie"),
        make_table_el([["t1", "a"]]),
        make_para_el("Middle shared paragraph"),
        make_table_el([["t2", "b"]]),
        make_para_el("Foxtrot golf hotel"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Xray yankee zulu"),
        make_table_el([["t1", "a"]]),
        make_para_el("Middle shared paragraph"),
        make_table_el([["t2", "b"]]),
        make_para_el("Umbrella vector whale"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    for i in range(6):
        _assert_matched(a, i, i)


def test_adjacent_tables_sharing_flank() -> None:
    """Two tables separated by one paragraph — shared flank pinned once."""
    base_els = [
        make_para_el("Aaa bbb ccc"),
        make_table_el([["t1", "x"]]),
        make_para_el("Middle shared text"),
        make_table_el([["t2", "y"]]),
        make_para_el("Ddd eee fff"),
        make_terminal_para(),
    ]
    # Rewrite the shared middle paragraph
    desired_els = [
        make_para_el("Aaa bbb ccc"),
        make_table_el([["t1", "x"]]),
        make_para_el("Completely new middle"),
        make_table_el([["t2", "y"]]),
        make_para_el("Ddd eee fff"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    # All 6 positions should match 1:1
    for i in range(6):
        _assert_matched(a, i, i)


def test_unequal_table_counts_one_deleted() -> None:
    """Base has 2 tables, desired has 1 — only the remaining pair gets pinned.

    "Outro" is exact-text-unique in both base and desired, so the exact-text
    pre-pin (base idx 4 <-> desired idx 2) wins over the table-flank
    heuristic that would otherwise force "Middle" (base idx 2, unrelated
    text) onto "Outro" — the pre-pin gives a strictly better alignment.
    """
    base_els = [
        make_para_el("Intro"),
        make_table_el([["keep1", "a"]]),
        make_para_el("Middle"),
        make_table_el([["drop", "z"]]),
        make_para_el("Outro"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Intro"),
        make_table_el([["keep1", "a"]]),
        make_para_el("Outro"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    # The preserved table pair and its flanks should match.
    _assert_matched(a, 0, 0)  # Intro
    _assert_matched(a, 1, 1)  # table keep1
    # "Outro" (base idx 4) exact-matches "Outro" (desired idx 2) directly.
    _assert_matched(a, 4, 2)
    # "Middle" (base idx 2) and the dropped table (base idx 3) are deleted.
    assert 2 in set(a.base_deletes)
    assert 3 in set(a.base_deletes)


def test_unequal_table_counts_one_inserted() -> None:
    """Base has 1 table, desired has 2 — only existing pair is pinned.

    "Outro" is exact-text-unique in both base and desired (at desired idx 4,
    after the newly-inserted heading + table), so the exact-text pre-pin
    wins over the table-flank heuristic that would otherwise force it onto
    the new "Middle new" heading right after the kept table. The new
    heading + table are simply inserts; "Outro" is left untouched.
    """
    base_els = [
        make_para_el("Intro"),
        make_table_el([["keep", "a"]]),
        make_para_el("Outro"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Intro"),
        make_table_el([["keep", "a"]]),
        make_para_el("Middle new"),
        make_table_el([["new", "z"]]),
        make_para_el("Outro"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    # "Outro" (base idx 2) exact-matches "Outro" (desired idx 4) directly.
    _assert_matched(a, 2, 4)
    assert 2 in set(a.desired_inserts)  # "Middle new" heading
    assert 3 in set(a.desired_inserts)  # new table


def test_table_at_start_no_preflank() -> None:
    """Table at start of content (no preflank possible) — only post-flank pins."""
    # base starts with table (no preflank). Note: first element is the table itself.
    base_els = [
        make_table_el([["only", "t"]]),
        make_para_el("After table totally rewritten AAA BBB CCC"),
        make_terminal_para(),
    ]
    desired_els = [
        make_table_el([["only", "t"]]),
        make_para_el("Completely different ZZZ YYY XXX"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)  # post-flank pinned
    _assert_matched(a, 2, 2)


def test_issue_58_repro_shape() -> None:
    """Issue #58 shape: [SB, heading, sep, table, sep, heading, terminal].

    Only the heading text changes — neither sep_para should be deleted.
    """
    from extradoc.api_types._generated import (
        SectionBreak,
        StructuralElement,
    )

    def section_break_el() -> StructuralElement:
        return StructuralElement(section_break=SectionBreak())

    base_els = [
        section_break_el(),
        make_para_el("Original Heading", named_style="HEADING_1"),
        make_para_el("\n"),  # separator paragraph
        make_table_el([["x", "y"], ["z", "w"]]),
        make_para_el("\n"),  # separator paragraph
        make_para_el("Another Heading", named_style="HEADING_1"),
        make_terminal_para(),
    ]
    desired_els = [
        section_break_el(),
        make_para_el("Changed Heading Text", named_style="HEADING_1"),
        make_para_el("\n"),
        make_table_el([["x", "y"], ["z", "w"]]),
        make_para_el("\n"),
        make_para_el("Another Heading", named_style="HEADING_1"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    # Neither separator para should be deleted.
    _assert_not_deleted(a, 2)
    _assert_not_deleted(a, 4)
    # Both table flanks (sep_paras) should be matched to their counterparts.
    _assert_matched(a, 2, 2)
    _assert_matched(a, 3, 3)  # the table itself
    _assert_matched(a, 4, 4)


def test_pre_flank_conflict_dp_had_different_match() -> None:
    """DP matched a pre-flank to a different paragraph; pin must override.

    Build a case where the natural DP alignment matches base's preflank to
    some other desired paragraph (because its text happens to align better
    with a further-away desired para). After pinning, the preflank must
    match the table's desired preflank; the other para becomes unmatched.
    """
    # base: [para_A, para_B, table, terminal]
    # desired: [para_B_copy, table, para_A_moved, terminal]
    # Without pinning, DP could match base para_A with desired para_A_moved.
    # But table pair pins (base idx 2 <-> desired idx 1), forcing:
    #   pre-flank pin: base idx 1 <-> desired idx 0
    # So base idx 1 (para_B) must be pinned to desired idx 0 (para_B_copy),
    # which is the correct assignment anyway.
    # Let's construct a sharper test: base = [A, table, terminal]; desired
    # = [A_matching_something_else, table, terminal]. The pinning ensures
    # base[0] and desired[0] match regardless.
    base_els = [
        make_para_el("completely unique alpha beta gamma delta"),
        make_table_el([["shared", "cell"]]),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("totally different omega psi chi phi upsilon"),
        make_table_el([["shared", "cell"]]),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)


def test_no_tables_at_all_noop() -> None:
    """When no tables exist, pinning is a no-op; DP result preserved."""
    base_els = [
        make_para_el("one two three"),
        make_para_el("four five six"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("one two three"),
        make_para_el("four five six modified"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    _assert_matched(a, 0, 0)
    _assert_matched(a, 1, 1)
    _assert_matched(a, 2, 2)


def test_flank_pin_never_overrides_exact_text_pre_pin() -> None:
    """A table-flank pin must never clobber an unambiguous exact-text pin.

    Regression test for the "III. FEJEZET" bug: a table's row count changes
    AND a brand-new heading is inserted right after the table in `desired`,
    while the *original* post-flank heading (unchanged text) is still present
    further downstream in `desired`, unambiguously pre-pinned there by
    ``_pre_pin_stable_anchors``. The naive table-flank post-processor used to
    force the post-flank paragraph to match the new adjacent heading,
    clobbering the correct far-away exact-text match.
    """
    base_els = [
        make_para_el("Opening paragraph"),
        make_table_el([["x", "y"], ["z", "w"], ["p", "q"]]),
        make_para_el("STABLE HEADING TEXT UNIQUE"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("Opening paragraph"),
        make_table_el(
            [["x", "y"], ["z", "w"], ["p", "q"], ["new1", "new2"], ["new3", "new4"]]
        ),
        make_para_el("BRAND NEW HEADING INSERTED"),
        make_para_el("Some other stable filler text"),
        make_para_el("STABLE HEADING TEXT UNIQUE"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    # The exact-text pre-pin must win: base idx 2 ("STABLE HEADING TEXT
    # UNIQUE") must match desired idx 4, NOT be clobbered into desired idx 2
    # (the new heading) by the table-flank heuristic.
    _assert_matched(a, 2, 4)
    _assert_not_deleted(a, 2)
    # The new heading must be a genuine insert, not a forced match.
    assert 2 in set(a.desired_inserts), (
        "desired idx 2 (brand new heading) should be an insert, "
        "not force-matched to base idx 2"
    )
    # The table pair itself should still be pinned.
    _assert_matched(a, 1, 1)


def test_three_tables_all_flanks_rewritten() -> None:
    """Three tables with all flanks completely rewritten."""
    base_els = [
        make_para_el("alpha one"),
        make_table_el([["t1", "a"]]),
        make_para_el("bravo two"),
        make_table_el([["t2", "b"]]),
        make_para_el("charlie three"),
        make_table_el([["t3", "c"]]),
        make_para_el("delta four"),
        make_terminal_para(),
    ]
    desired_els = [
        make_para_el("rewritten AAA"),
        make_table_el([["t1", "a"]]),
        make_para_el("rewritten BBB"),
        make_table_el([["t2", "b"]]),
        make_para_el("rewritten CCC"),
        make_table_el([["t3", "c"]]),
        make_para_el("rewritten DDD"),
        make_terminal_para(),
    ]
    a = align_content(_nodes(base_els), _nodes(desired_els))
    for i in range(8):
        _assert_matched(a, i, i)
