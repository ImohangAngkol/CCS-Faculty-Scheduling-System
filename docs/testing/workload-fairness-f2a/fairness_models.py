"""F2A offline score experiments. Never imported by application/GA code.

Integer fictional teaching credits only. Exact rational candidates, original
floating/ceil baseline. Scores are not interchangeable calibrated fitness units.
"""
from fractions import Fraction
import math


def validate(actual,targets):
    if not actual or len(actual)!=len(targets):raise ValueError('MATCHING_NONEMPTY_COHORT_REQUIRED')
    if any(type(x) is not int for x in [*actual,*targets]):raise ValueError('INTEGER_UNITS_REQUIRED')
    if any(x<0 for x in [*actual,*targets]):raise ValueError('NEGATIVE_UNITS_REJECTED')
    if any(x>40 for x in actual):raise ValueError('HARD_TEACHING_CEILING_EXCEEDED')
    if any(t>24 for t in targets):raise ValueError('OUTSIDE_FICTIONAL_OPTION_B_DOMAIN')


def overload(actual,targets):
    validate(actual,targets)
    return sum(10*math.ceil(max(0,min(a,max(t,30))-t)/3)+25*math.ceil(max(0,a-max(t,30))/3)
               for a,t in zip(actual,targets))


def original_workload(actual,targets):
    """Reference arithmetic only; independently checked against real scorer."""
    validate(actual,targets)
    return sum(25*math.ceil((t-a)/t*10) for a,t in zip(actual,targets) if a<t)+overload(actual,targets)


def absolute(actual,targets):
    validate(actual,targets)
    return Fraction(sum(abs(a-t) for a,t in zip(actual,targets)))


def squared(actual,targets):
    validate(actual,targets)
    return Fraction(sum((a-t)**2 for a,t in zip(actual,targets)))


def person_relative(actual,targets):
    validate(actual,targets)
    # A one-credit denominator for target0 is an EXPLICIT unapproved convention.
    return sum((Fraction((a-t)**2,max(t,1)**2) for a,t in zip(actual,targets)),Fraction())


def target_relative(actual,targets):
    validate(actual,targets)
    # Equivalent to sum(T*(actual/T-1)^2) for T>0. Denominator1 at T=0.
    return sum((Fraction((a-t)**2,max(t,1)) for a,t in zip(actual,targets)),Fraction())


def relative_with_original_overload(actual,targets):
    """Explicit sensitivity: illustrative scale plus unchanged overload bands.

    Deliberately counts excess in both continuous deviation and original bands;
    not a silently approved replacement or a hidden change to other components.
    """
    return Fraction(250,24)*target_relative(actual,targets)+overload(actual,targets)


FUNCTIONS={'original_workload':original_workload,'absolute':absolute,'squared':squared,
           'person_relative':person_relative,'target_relative':target_relative,
           'relative_with_original_overload':relative_with_original_overload}


def metrics(actual,targets,eligible=None):
    validate(actual,targets)
    eligible=[True]*len(actual) if eligible is None else eligible
    if len(eligible)!=len(actual):raise ValueError('ELIGIBILITY_VECTOR_MISMATCH')
    q=[Fraction(a,t) for a,t in zip(actual,targets) if t]
    mean=sum(q,Fraction())/len(q) if q else None
    return dict(actual=list(actual),targets=list(targets),signed_deviation=[a-t for a,t in zip(actual,targets)],
        relative_deviation=[Fraction(a-t,t) if t else None for a,t in zip(actual,targets)],
        fulfillment=[Fraction(a,t) if t else None for a,t in zip(actual,targets)],
        underload_units=[max(0,t-a) for a,t in zip(actual,targets)],overload_units=[max(0,a-t) for a,t in zip(actual,targets)],
        total_underload=sum(max(0,t-a) for a,t in zip(actual,targets)),total_overload=sum(max(0,a-t) for a,t in zip(actual,targets)),
        zero_assignment_count=sum(a==0 for a in actual),
        positive_target_eligible_zero_count=sum(a==0 and t>0 and e for a,t,e in zip(actual,targets,eligible)),
        no_eligible_offering_count=sum(not e for e in eligible),
        fulfillment_spread=max(q)-min(q) if q else None,
        fulfillment_variance=sum(((x-mean)**2 for x in q),Fraction())/len(q) if q else None,
        above_warning_count=sum(a>30 for a in actual),hard_ceiling_passed=True)


def serial(value):
    if isinstance(value,Fraction):return dict(exact=str(value),decimal=float(value))
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    return value
