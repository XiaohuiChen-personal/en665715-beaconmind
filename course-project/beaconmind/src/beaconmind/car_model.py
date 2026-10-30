"""Car geometry arithmetic for M1.T9 (plan/M1-foundations.md step 5): wheel diameter from a roll-out,
track width, sweep radius, encoder counts per revolution, mean and spread of repeated readings, the rounded plate
front, and first-order uncertainty propagation. Standard library only (README L3).

Units are whatever the caller passes in (the M1.T9 writer passes metres and kilograms).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-10: wrote these functions and their tests
(tests/test_car_model.py); 2026-10-16: added rounded_front and rounded_front_corner (the plate's front outline from
its CAD, the private course repo (plate CAD is not published here)).
"""

import math


def effective_diameter(rollout_m, revs):
    """Effective rolling diameter from a roll-out: the floor distance covered in `revs` wheel turns / (revs * pi)."""
    if revs <= 0:
        raise ValueError("revs must be positive, got %r" % (revs,))
    return rollout_m / (revs * math.pi)


def track_width(outer_m, inner_m):
    """Contact-centre to contact-centre track width: the mean of the outer-to-outer and inner-to-inner spans."""
    if inner_m >= outer_m:
        raise ValueError("inner span %r must be smaller than outer span %r" % (inner_m, outer_m))
    return (outer_m + inner_m) / 2.0


def sweep_radius(points):
    """Largest distance from the axle midpoint over [(x, y), ...] (README C5 turn rule)."""
    pts = list(points)
    if not pts:
        raise ValueError("sweep_radius needs at least one point")
    return max(math.hypot(x, y) for x, y in pts)


def counts_per_rev(delta_a, delta_b, revs):
    """Encoder counts per wheel revolution from the A- and B-pin edge counts over `revs` turns."""
    if revs <= 0:
        raise ValueError("revs must be positive, got %r" % (revs,))
    return (delta_a + delta_b) / revs


def mean_and_spread(readings):
    """(mean, max - min) of repeated readings."""
    values = [float(v) for v in readings]
    if not values:
        raise ValueError("mean_and_spread needs at least one reading")
    return sum(values) / len(values), max(values) - min(values)


def rss(*terms):
    """Root-sum-square of independent uncertainty terms (first-order propagation)."""
    return math.sqrt(sum(float(t) ** 2 for t in terms))


def rounded_front(front_x, half_width, arc_radius, corner_radius):
    """The geometry of a plate front made of one arc and two corner fillets, in the axle-midpoint frame.

    The front edge is an arc of radius R = arc_radius whose apex is (front_x, 0), so its centre is (front_x - R, 0).
    Each side of the plate is the line y = +-w (w = half_width), joined to the arc by a fillet of radius
    r = corner_radius tangent to both. The fillet centre is (xf, w - r), at distance R - r from the arc centre:
        xf = front_x - R + sqrt((R - r)^2 - (w - r)^2).
    Returns a dict (upper half; the lower half is the mirror image):
        arc_centre_x   front_x - R
        fillet_centre  (xf, w - r)
        side_tangent   (xf, w): where the straight side ends and the fillet starts
        arc_tangent    the point where the fillet meets the arc, on the line from the arc centre through the fillet
                       centre, at distance R from the arc centre
    """
    big, small, w = float(arc_radius), float(corner_radius), float(half_width)
    if not 0 < small < w < big:
        raise ValueError("need 0 < corner_radius < half_width < arc_radius, got %r, %r, %r"
                         % (corner_radius, half_width, arc_radius))
    cx = front_x - big
    xf = cx + math.sqrt((big - small) ** 2 - (w - small) ** 2)
    k = big / (big - small)
    return {
        "arc_centre_x": cx,
        "fillet_centre": (xf, w - small),
        "side_tangent": (xf, w),
        "arc_tangent": (cx + k * (xf - cx), k * (w - small)),
    }


def rounded_front_corner(front_x, half_width, arc_radius, corner_radius):
    """(x, y >= 0): the point of a rounded plate front (see rounded_front) farthest from the origin (the axle midpoint).

    On one circle, the distance to a fixed point grows monotonically with the angle away from the circle's nearest
    point, so over an arc it is largest either at an end of the arc or at the circle's own farthest point,
    centre + radius * centre / |centre|, when that point lies on the arc. The candidates are therefore the apex, the
    two tangent points, and the fillet's own farthest point when its angle lies between the fillet's two ends
    (the main arc's own farthest point is on the x axis: the apex, or a point behind its centre that is not on the
    front arc).
    """
    g = rounded_front(front_x, half_width, arc_radius, corner_radius)
    (xf, yf), r = g["fillet_centre"], float(corner_radius)
    candidates = [(float(front_x), 0.0), g["arc_tangent"], g["side_tangent"]]
    start = math.atan2(g["arc_tangent"][1] - yf, g["arc_tangent"][0] - xf)  # fillet runs from here ...
    stop = math.pi / 2                                                       # ... to the side tangent, straight up
    far = math.atan2(yf, xf)
    if start <= far <= stop:
        candidates.append((xf + r * math.cos(far), yf + r * math.sin(far)))
    return max(candidates, key=lambda p: math.hypot(*p))
