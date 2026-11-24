from src.schema import ProjectState
from src.compiler import compile_handoff


def test_compile_within_budget_preserves_all_fields():
    state = ProjectState(
        goal="Build expense tracker API",
        hard_constraints=["Never use an ORM"],
        tech_stack=["Python", "FastAPI", "PostgreSQL"],
        deprecated_approaches=["SQLite"],
        active_bugs=["InvalidCatalogNameError"],
        next_steps=["Create expenses DB"],
    )

    result = compile_handoff(state, raw_tokens=500, max_tokens=400)

    assert result.compiled_tokens <= 400
    assert result.was_trimmed is False
    assert "SQLite" in result.prompt
    assert "Never use an ORM" in result.prompt


def test_compile_trims_low_priority_when_over_budget():
    state = ProjectState(
        goal="Build expense tracker API",
        hard_constraints=["Never use an ORM"],
        tech_stack=["Python", "FastAPI", "PostgreSQL"],
        deprecated_approaches=["SQLite", "MongoDB", "MySQL", "Django"],
        next_steps=["Step 1", "Step 2", "Step 3"],
    )

    result = compile_handoff(state, raw_tokens=600, max_tokens=130)

    assert result.compiled_tokens <= 130
    assert result.was_trimmed is True
    # Highest-priority items must survive
    assert "Build expense tracker API" in result.prompt
    assert "Never use an ORM" in result.prompt