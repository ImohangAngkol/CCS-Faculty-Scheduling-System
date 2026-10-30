"""Unapproved analytical policies, never imported by application/GA code.

Allocation vectors below are arithmetic controls, not generated timetables.
Original hard admission remains a separate mandatory predicate.
"""
from fractions import Fraction
import math


def measures(loads, targets):
    if len(loads) != len(targets) or not loads:
        raise ValueError('Nonempty matching cohorts required')
    if any(type(x) is not int or x < 0 for x in [*loads, *targets]):
        raise ValueError('Only nonnegative integer fictional units supported')
    relative = [Fraction(max(0, t-a), t) for a,t in zip(loads,targets) if t]
    fulfillment = [Fraction(a,t) for a,t in zip(loads,targets) if t]
    mean = sum(fulfillment, Fraction()) / len(fulfillment) if fulfillment else Fraction()
    # Retain the ORIGINAL default overload/heavy-overload arithmetic only.
    overload = sum(10 * math.ceil(max(0, min(a,max(t,30))-t)/3)
                   + 25 * math.ceil(max(0,a-max(t,30))/3) for a,t in zip(loads,targets))
    original = sum(25 * math.ceil(10 * float(x)) for x in relative) + overload
    return dict(
        original_default_workload=original,
        linear_relative=250 * sum(relative, Fraction()) + overload,
        squared_relative=250 * sum((x*x for x in relative), Fraction()) + overload,
        # Ordering here is a policy proposal, NOT a scalar replacement fitness.
        overload_shortage_spread=(Fraction(overload), Fraction(sum(max(0,t-a) for a,t in zip(loads,targets))),
                                   sum(((x-mean)**2 for x in fulfillment), Fraction())),
        underload_units=sum(max(0,t-a) for a,t in zip(loads,targets)),
        overload_units=sum(max(0,a-t) for a,t in zip(loads,targets)),
        zero_assignments=sum(a==0 for a in loads),
        above_warning=sum(a>30 for a in loads),
        teaching_ceiling_valid=all(a<=40 for a in loads),
        scope='Analytical allocation only; not a timetable or a complete hard-validity result')


CASES = {
    'equal_shortage_balanced': ([2,2],[24,24]),
    'equal_shortage_concentrated': ([4,0],[24,24]),
    'all_zero': ([0,0],[24,24]),
    'targets_met': ([24,24],[24,24]),
    'moderate_overload_and_shortfall': ([26,22],[24,24]),
    'warning_boundary': ([30,18],[24,24]),
    'above_warning': ([31,17],[24,24]),
    'ceiling_boundary': ([40,8],[24,24]),
    'invalid_above_ceiling': ([41,7],[24,24]),
    'unequal_targets_equal_units': ([6,6],[12,24]),
    'unequal_targets_equal_fulfillment': ([4,8],[12,24]),
    'zero_target_unassigned': ([0,2],[0,24]),
    'zero_target_assigned': ([2,0],[0,24]),
}


def serial(value):
    if isinstance(value, Fraction):
        return {'exact':str(value),'decimal':float(value)}
    if isinstance(value, dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):return [serial(v) for v in value]
    return value
