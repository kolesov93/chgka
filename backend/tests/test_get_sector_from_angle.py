import math


def test_get_sector_from_angle_matches_sector_centers():
    # Import inside test so we don't accidentally trigger app startup hooks.
    from main import get_sector_from_angle, SECTORS_COUNT, ANGLE_STEP

    # Centers are defined exactly the same way as in get_sector_from_angle().
    for i in range(1, SECTORS_COUNT + 1):
        center = (90 + i * ANGLE_STEP) % 360
        assert get_sector_from_angle(center) == i


def test_get_sector_from_angle_wraps_near_0_360():
    from main import get_sector_from_angle, ANGLE_STEP

    # There is a sector with center angle close to 0 degrees (wrap-around).
    # With current formula, sector 10 center is around 6.923°.
    sector10_center = (90 + 10 * ANGLE_STEP) % 360
    assert 0 <= sector10_center < 15

    # Angles near 0° and near 360° should both map to that sector (wrap-around distance).
    assert get_sector_from_angle(1.0) == 10
    assert get_sector_from_angle(359.0) == 10


def test_forced_sector_candidates_wrap_from_one_to_thirteen(monkeypatch):
    from main import calculate_spin_result
    import main

    captured = {}

    def choose(candidates):
        captured["candidates"] = list(candidates)
        return candidates[0]

    monkeypatch.setattr(main.random, "choice", choose)
    monkeypatch.setattr(main.random, "uniform", lambda low, high: (low + high) / 2)

    _angle, sector = calculate_spin_result(force_sector=1, used_questions=[13, 12])

    assert captured["candidates"] == [1, 13, 12]
    assert sector == 1

