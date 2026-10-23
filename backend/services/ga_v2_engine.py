"""Explicit constrained V2 orchestration; V1 modules and operators are unchanged.

Selection, elitism and fitness call the original implementations. V2 owns
candidate admission and bounded construction with explicit run-local sections.
No runtime global/module replacement, fitness penalties or external Subject genes.
"""
from collections import Counter
import copy
import math
import random

from genetic_algorithm.utils import Functions as schedule
from genetic_algorithm.utils.FrozenInputs import capture_inputs, scoring_inputs
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from genetic_algorithm.operators.ElitisimSelection import elitism_selection
from genetic_algorithm.operators.TournamentSelection import select_parent_pair
from genetic_algorithm.operators.Swap import create_child_by_faculty_swap
from genetic_algorithm.operators.mutation import mutate_by_swapping_faculty_subjects
from services.ga_checkpoint_service import dataframe_to_state, dataframe_from_state
from services.ga_progress_service import input_fingerprint
from services.ga_publication_service import validate_publication
from services.ga_v2_constraints import ConstraintError, reject, reduced_templates, external_conflict
from schemas.ga_constrained import Parameters

ENGINE_VERSION = "ga-constrained-v2.1"


def admit(candidate, snapshot, templates):
    """No fitness, RNG, repair, output or mutation of the supplied chromosome."""
    try:
        conflict = external_conflict(candidate, snapshot)
        if conflict:
            reject(conflict, "Candidate conflicts with a pinned external commitment.")
        validate_publication(candidate, *templates)
        profiles={str(f.code):f for f in templates[1]}
        fields=("eligible_subjects","admin_load","research_load","extension_load","required_teaching_load","absolute_max_teaching_load","seniority_level")
        for subject in candidate:
            member=subject.assigned_faculty
            if not getattr(member,"is_external",False):
                source=profiles.get(str(member.code))
                if source is None or any(getattr(member,field)!=getattr(source,field) for field in fields):
                    reject("INVALID_CANDIDATE", "Candidate faculty metadata differs from the authoritative runtime catalog.")
    except ConstraintError:
        raise
    except (ValueError, RuntimeError, TypeError, AttributeError):
        reject("INVALID_CANDIDATE", "Candidate violates existing academic scheduling constraints.")


def construct(templates, max_restarts):
    """Bounded V2 initial/fresh factory using original assignment/reset helpers.

    Pass run-local subjects explicitly: the V1 convenience constructors can
    otherwise consult Functions.list_subjects from another execution. Pattern
    definitions, qualification/load checks, assignments and rollback stay original.
    """
    subjects, faculty, rooms = copy.deepcopy(templates)
    try:
        schedule.check_minimum_load_feasibility(faculty, subjects)
    except ValueError:
        reject("INPUT_CAPACITY_REJECTED", "The original input-capacity gate rejected the offering set; this is an input conflict, not search exhaustion.")
    if any(s.lec_hours not in (0,2,3) or s.lab_hours not in (0,3) for s in subjects):
        reject("UNSUPPORTED_COMPONENT", "An offering has no supported original GA meeting pattern; no duration was invented.")
    patterns = {("lecture",2):schedule.defined_two_lec_hours, ("lecture",3):schedule.defined_three_lec_hours,
                ("laboratory",3):schedule.defined_three_lab_hours}
    for _ in range(max_restarts):
        schedule.reset_complete_schedule(faculty, subjects, rooms)
        ordered = subjects.copy(); random.shuffle(ordered)
        ordered.sort(key=lambda s:(s.credit_units,s.lab_hours), reverse=True)
        complete = True
        for subject in ordered:
            assigned = False
            candidates = [subject.preassigned_instructor] if schedule.is_preassigned(subject) else schedule.get_ranked_faculty_candidates(subject, faculty)
            for member in candidates:
                assigned = True
                for component, hours in (("lecture",subject.lec_hours),("laboratory",subject.lab_hours)):
                    if not hours:
                        continue
                    options = list(patterns.get((component,hours), ())); random.shuffle(options)
                    if not any(schedule.assign_schedule_to_faculty(member, subject, option,
                               "Lecture" if component=="lecture" else "Laboratory", room_list=rooms,
                               list_subjects=subjects) for option in options):
                        assigned = False
                        break
                if assigned:
                    break
                schedule.rollback_subject_assignment(subject)
            if not assigned:
                complete = False
                break
        if complete:
            return subjects
    reject("SEARCH_EXHAUSTED", "Bounded candidate construction exhausted its restart budget; this is not proof of infeasibility.")


def freeze(templates):
    token=scoring_inputs.set(None)
    try:
        frozen = capture_inputs()
    finally:
        scoring_inputs.reset(token)
    frozen["system_faculty"] = copy.deepcopy(templates[1])
    # Keep the original preference policy; restrict the universe to this sourced
    # catalog without changing any protected JSON or fitness implementation.
    return frozen


def validate_state(state, snapshot, templates):
    from services.ga_v2_store import engine_fingerprint
    if state["engine_identity"]!=engine_fingerprint():
        reject("V2_CHECKPOINT_INCOMPATIBLE", "The pinned V2 engine changed; restart with an explicitly compatible engine.")
    params = Parameters.model_validate(state["parameters"])
    generation = state["generation"]
    if (type(generation) is not int or not 0<=generation<=params.generations
            or len(state["population"])!=params.population_size
            or [h["generation"] for h in state["history"]]!=list(range(generation+1))
            or state["scoring_inputs"]["input_fingerprint"]!=input_fingerprint()
            or not math.isfinite(state["best_fitness"])):
        reject("V2_CHECKPOINT_INVALID", "V2 generation, population, score or input invariants failed.")
    random.Random(0).setstate(state["random_state"])
    publication = reduced_templates(snapshot, templates)
    for candidate in [*state["population"],state["best"]]:
        admit(candidate, snapshot, publication)
    expected=freeze(templates)
    frozen=state["scoring_inputs"]
    if set(frozen)!=set(expected) or any(frozen[k]!=expected[k] for k in expected if k!="system_faculty"):
        reject("V2_CHECKPOINT_INCOMPATIBLE", "The frozen original evaluation inputs differ from the supported current inputs.")
    profiles={str(f.code):f for f in expected["system_faculty"]}
    fields=("eligible_subjects","admin_load","research_load","extension_load","required_teaching_load","absolute_max_teaching_load","seniority_level")
    if len(frozen["system_faculty"])!=len(profiles):
        reject("V2_CHECKPOINT_INVALID", "Frozen faculty universe changed.")
    for member in frozen["system_faculty"]:
        original=profiles.get(str(member.code))
        if original is None or any(getattr(member,k)!=getattr(original,k) for k in fields):
            reject("V2_CHECKPOINT_INVALID", "Frozen faculty profiles changed.")
        for day in member.get_day_map():
            if [(b.start_time,b.end_time,b.is_available) for b in member.get_day_map()[day]]!=[(b.start_time,b.end_time,b.is_available) for b in original.get_day_map()[day]]:
                reject("V2_CHECKPOINT_INVALID", "Frozen faculty calendar changed.")
    token=scoring_inputs.set(frozen)
    try:
        score=faculty_preference_fitness(state["best"],dataframe_from_state(state["preferences"]))
        if score!=state["best_fitness"] or state["history"][-1]["best_ever_fitness"]!=score:
            reject("V2_CHECKPOINT_INVALID", "Best-ever score differs from the original fitness evaluation.")
    finally:
        scoring_inputs.reset(token)
    # Rebuild against current templates instead of trusting serialized calendars.
    return publication


def run(templates, snapshot, parameters, preferences, boundary, *, seed=None, state=None,
        factory=construct, crossover=create_child_by_faculty_swap, mutation=mutate_by_swapping_faculty_subjects):
    """Boundary validates fresh trust and commits before anything is published.

    Injectable callables are local test dependencies, never request parameters or
    deployment flags. Production defaults invoke the original protected operators.
    """
    params = parameters.model_dump()
    from services.ga_v2_store import engine_fingerprint
    engine_identity=engine_fingerprint() if state is None else state["engine_identity"]
    if engine_identity!=engine_fingerprint():
        reject("V2_CHECKPOINT_INCOMPATIBLE", "V2 source identity changed before continuation.")
    publication = reduced_templates(snapshot, templates)
    frozen = freeze(templates) if state is None else state["scoring_inputs"]
    token = scoring_inputs.set(frozen)
    try:
        if frozen["input_fingerprint"]!=input_fingerprint():
            reject("V2_INPUT_CHANGED", "Scheduling inputs changed before V2 execution.")
        def score(candidate):
            value = faculty_preference_fitness(candidate, preferences)
            if not math.isfinite(value):
                reject("NONFINITE_FITNESS", "The original fitness implementation returned a non-finite score.")
            return value
        diagnostics = Counter() if state is None else Counter(state["diagnostics"])
        def accept(candidate, stage):
            if candidate is None:
                diagnostics[stage+":NO_CANDIDATE"] += 1
                return False
            try:
                admit(candidate, snapshot, publication)
            except ConstraintError as error:
                diagnostics[stage+":"+error.code] += 1
                return False
            diagnostics[stage+":ACCEPTED"] += 1
            return True
        def fresh(count):
            candidates=[]
            for _ in range(count*parameters.candidate_attempts):
                if len(candidates)==count:
                    break
                try:
                    candidate=factory(publication,parameters.max_restarts)
                except ConstraintError as error:
                    if error.code!="SEARCH_EXHAUSTED":
                        raise
                    diagnostics["construction:SEARCH_EXHAUSTED"]+=1
                    continue
                if accept(candidate,"construction"):
                    candidates.append(candidate)
            if len(candidates)!=count:
                error=ConstraintError("SEARCH_EXHAUSTED", "Not enough admissible candidates within the bounded budget; feasibility is unknown.")
                error.diagnostics=dict(diagnostics)
                raise error
            return candidates
        if state is None:
            population=[]
            if seed is not None:
                # A requested seed is never silently skipped or repaired.
                try:
                    admit(seed,snapshot,publication)
                except ConstraintError:
                    reject("INCOMPATIBLE_REQUESTED_SEED", "The explicitly requested seed violates the pinned constraint set.")
                population.append(copy.deepcopy(seed))
            population.extend(fresh(parameters.population_size-len(population)))
            population.sort(key=score)
            best=copy.deepcopy(population[0]); best_fitness=score(best)
            history=[]; generation=0
        else:
            validate_state(state,snapshot,templates)
            if state["parameters"]!=params:
                reject("V2_CHECKPOINT_INCOMPATIBLE", "Continuation parameters differ from the pinned checkpoint.")
            population,best,best_fitness,history,generation=(copy.deepcopy(state[k]) for k in ("population","best","best_fitness","history","generation"))
            preferences=dataframe_from_state(state["preferences"])
            random.setstate(state["random_state"])  # Last validation precedes original next RNG draw.

        def checkpoint():
            # Every candidate is admitted before elitism, best-ever or persistence.
            for candidate in [*population,best]:
                admit(candidate,snapshot,publication)
            if frozen["input_fingerprint"]!=input_fingerprint():
                reject("V2_INPUT_CHANGED", "Scheduling inputs changed; publication is blocked.")
            if not history or history[-1]["generation"]!=generation:
                history.append({"generation":generation,"generation_best_fitness":score(population[0]),"best_ever_fitness":best_fitness})
            saved={"engine_identity":engine_identity,"parameters":params,"generation":generation,"population":population,"best":best,
                "best_fitness":best_fitness,"history":history,"diagnostics":dict(diagnostics),"random_state":random.getstate(),
                "scoring_inputs":frozen,"preferences":dataframe_to_state(preferences)}
            return boundary(saved)
        if state is None:
            outcome=checkpoint()
            if outcome in {"pause","stop"}:
                return outcome
        elif generation==parameters.generations:
            outcome=checkpoint()
            return outcome if outcome in {"pause","stop"} else "complete"
        while generation<parameters.generations:
            # The current population is admitted before it enters selection.
            for candidate in population:
                admit(candidate,snapshot,publication)
            scores=[score(c) for c in population]
            elites,_,non_elites,_=elitism_selection(population,scores,elite_percentage=.10)
            parents=elitism_selection(non_elites,[score(c) for c in non_elites],elite_percentage=.50)[0] if non_elites else elites
            children=[]; target=max(1,int(parameters.population_size*.9))
            for _ in range(target*20):
                if len(children)>=target:
                    break
                left,right=select_parent_pair(population,scores,tournament_size=3)
                child=crossover(parent1=left,parent2=right,df_faculty_pref=preferences,max_attempts=parameters.crossover_attempts)
                if accept(child,"crossover"):
                    children.append(child)
            children.extend(parents)
            if children:
                changed=mutation(population=children,df_faculty_pref=preferences,max_attempts=parameters.mutation_attempts)
                if accept(changed,"mutation"):
                    children.append(changed)
            children.extend(elites); children.append(copy.deepcopy(best))
            children.extend(fresh(parameters.fresh_chromosomes))
            admitted=[candidate for candidate in children if accept(candidate,"survivor")]
            # Fill shortfall before sorting/comparison, never report a short population.
            admitted.extend(fresh(max(0,parameters.population_size-len(admitted))))
            admitted.sort(key=score)
            population=admitted[:parameters.population_size]
            if score(population[0])<best_fitness:
                best=copy.deepcopy(population[0]); best_fitness=score(best)
            generation+=1
            outcome=checkpoint()
            if outcome in {"pause","stop"}:
                return outcome
        return "complete"
    finally:
        scoring_inputs.reset(token)
