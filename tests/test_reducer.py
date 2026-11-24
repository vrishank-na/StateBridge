from src.schema import ProjectState, StateDelta
from src.reducer import apply_delta


def test_tech_deprecation_moves_tool_out_of_stack():
    state = ProjectState(goal="Build REST API", tech_stack=["Python", "FastAPI", "SQLite"])
    delta = StateDelta(
        added_tech=["PostgreSQL", "asyncpg"],
        deprecated_tech=["SQLite"],
        added_constraints=["Never use an ORM, only raw SQL"],
    )

    new_state = apply_delta(state, delta)

    assert "SQLite" not in new_state.tech_stack
    assert "SQLite" in new_state.deprecated_approaches
    assert "PostgreSQL" in new_state.tech_stack
    assert "Never use an ORM, only raw SQL" in new_state.hard_constraints


def test_bug_resolution_clears_active_bug():
    state = ProjectState(
        active_bugs=['asyncpg.exceptions.InvalidCatalogNameError: database "expenses" does not exist']
    )
    delta = StateDelta(resolved_bugs=["InvalidCatalogNameError"])

    new_state = apply_delta(state, delta)

    assert new_state.active_bugs == []


def test_case_insensitive_deduplication():
    state = ProjectState(tech_stack=["FastAPI"])
    delta = StateDelta(added_tech=["fastapi", "FASTAPI"])

    new_state = apply_delta(state, delta)

    assert new_state.tech_stack == ["FastAPI"]