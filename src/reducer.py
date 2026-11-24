from typing import List
from src.schema import ProjectState, StateDelta


def _add_unique(target_list: List[str], new_items: List[str]) -> List[str]:
    """
    Appends items from `new_items` into `target_list` while avoiding
    case-insensitive duplicates (e.g., won't add 'fastapi' if 'FastAPI' exists).
    """
    existing_lower = {item.strip().lower() for item in target_list}
    updated = list(target_list)

    for item in new_items:
        clean_item = item.strip()
        if clean_item and clean_item.lower() not in existing_lower:
            updated.append(clean_item)
            existing_lower.add(clean_item.lower())

    return updated


def _remove_matching(target_list: List[str], items_to_remove: List[str]) -> List[str]:
    """
    Removes any item from `target_list` that matches an entry in `items_to_remove`
    (case-insensitive exact or substring match for resolved bugs / deprecated tools).
    """
    if not items_to_remove:
        return list(target_list)

    remove_lower = [item.strip().lower() for item in items_to_remove if item.strip()]
    filtered: List[str] = []

    for existing in target_list:
        existing_low = existing.strip().lower()
        # Drop if it matches any item to remove
        is_match = any(
            rem == existing_low or rem in existing_low or existing_low in rem
            for rem in remove_lower
        )
        if not is_match:
            filtered.append(existing)

    return filtered


def apply_delta(state: ProjectState, delta: StateDelta) -> ProjectState:
    """
    Deterministically applies a single StateDelta change ticket onto a ProjectState,
    returning a brand-new updated ProjectState without mutating the input in place.
    """
    # 1. Update goal only if a new goal was explicitly provided
    new_goal = delta.updated_goal.strip() if delta.updated_goal else state.goal

    # 2. Add new strict constraints (deduplicated)
    new_constraints = _add_unique(state.hard_constraints, delta.added_constraints)

    # 3. Handle Tech Stack & Deprecations:
    #    First add new tech, then remove anything marked deprecated in this delta
    updated_tech = _add_unique(state.tech_stack, delta.added_tech)
    updated_tech = _remove_matching(updated_tech, delta.deprecated_tech)

    #    Record deprecated tools in deprecated_approaches (and ensure they aren't re-added)
    updated_deprecated = _add_unique(state.deprecated_approaches, delta.deprecated_tech)

    # 4. Handle Bugs:
    #    Add newly discovered bugs, then remove any bugs confirmed resolved
    updated_bugs = _add_unique(state.active_bugs, delta.new_bugs)
    updated_bugs = _remove_matching(updated_bugs, delta.resolved_bugs)

    # 5. Update Next Steps:
    #    If the delta provides fresh next steps, replace stale next steps; otherwise keep existing
    if delta.updated_next_steps:
        updated_steps = _add_unique([], delta.updated_next_steps)
    else:
        updated_steps = list(state.next_steps)

    return ProjectState(
        goal=new_goal,
        hard_constraints=new_constraints,
        tech_stack=updated_tech,
        deprecated_approaches=updated_deprecated,
        active_bugs=updated_bugs,
        next_steps=updated_steps,
    )