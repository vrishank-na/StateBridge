from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectState(BaseModel):
    """
    The Master 'ICU Clipboard' representing the single source of truth
    for a project at any point in the conversation.
    """
    goal: str = Field(
        default="Not yet defined",
        description="The core objective of what the user is building or solving."
    )
    hard_constraints: List[str] = Field(
        default_factory=list,
        description="Strict rules or boundaries that must never be violated (e.g., 'No LangChain')."
    )
    tech_stack: List[str] = Field(
        default_factory=list,
        description="Currently active languages, frameworks, libraries, and tools."
    )
    deprecated_approaches: List[str] = Field(
        default_factory=list,
        description="Tools, libraries, or ideas that were tried and abandoned (do not suggest again)."
    )
    active_bugs: List[str] = Field(
        default_factory=list,
        description="Unresolved errors, stack traces, or blockers currently being debugged."
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Immediate actionable tasks queued up next."
    )


class StateDelta(BaseModel):
    """
    The 'Change Ticket' extracted from a small 4-turn batch of messages.
    Captures ONLY what changed in that specific window.
    """
    updated_goal: Optional[str] = Field(
        default=None,
        description="New project goal ONLY if the user explicitly changed or clarified the main objective."
    )
    added_constraints: List[str] = Field(
        default_factory=list,
        description="New strict rules introduced in these messages."
    )
    added_tech: List[str] = Field(
        default_factory=list,
        description="New tools, libraries, or frameworks adopted in these messages."
    )
    deprecated_tech: List[str] = Field(
        default_factory=list,
        description="Tools or approaches explicitly rejected, dropped, or replaced in these messages."
    )
    new_bugs: List[str] = Field(
        default_factory=list,
        description="New errors or bugs encountered in these messages."
    )
    resolved_bugs: List[str] = Field(
        default_factory=list,
        description="Previously active bugs that were confirmed fixed in these messages."
    )
    updated_next_steps: List[str] = Field(
        default_factory=list,
        description="New immediate next steps decided in these messages."
    )