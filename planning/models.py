from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Intent types — one per extraction schema
# Maps directly to extraction/schemas/*.py
# ---------------------------------------------------------------------------
IntentType = Literal[
    "occurrence_search",    # User wants individual sighting records
    "facet_breakdown",      # User wants counts grouped by category
    "taxa_count",           # User wants a total record count
    "taxonomy",             # User wants to know about a species
    "distribution",         # User wants geographic range
    "out_of_scope",         # Out of scope — decline gracefully
    "unknown",              # Cannot determine intent — ask for clarification
]

# ---------------------------------------------------------------------------
# Query types — describes the nature of the query
# Used for traceability and logging
# ---------------------------------------------------------------------------
QueryType = Literal[
    "single_species",       # One species mentioned
    "multi_species",        # Multiple species mentioned
    "taxonomic_group",      # A group e.g. "all marsupials"
    "no_species",           # No species — database-wide query
    "comparison",           # Comparing two or more species
]


# ---------------------------------------------------------------------------
# ToolPlan — one entry per tool the planner wants to call
# ---------------------------------------------------------------------------
class ToolPlan(BaseModel):
    tool_name: Literal[
        "search_species_occurrences",
        "get_occurrence_breakdown",
        "get_occurrence_taxa_count",
        "lookup_species_info",
        "get_species_distribution",
    ] = Field(
        ...,
        description="Name of the tool to call"
    )
    priority: Literal["must_call", "optional"] = Field(
        ...,
        description=(
            "must_call: required to answer the query. "
            "optional: enhances the response but not required."
        )
    )
    reason: str = Field(
        ...,
        description="One sentence explaining why this tool was selected"
    )


# ---------------------------------------------------------------------------
# PlannerOutput — complete output of the planner LLM call
# ---------------------------------------------------------------------------
class PlannerOutput(BaseModel):
    intent: IntentType = Field(
        ...,
        description=(
            "Primary intent of the query. "
            "Determines which extraction schema will be used."
        )
    )
    query_type: QueryType = Field(
        ...,
        description="Nature of the query — single species, comparison, etc."
    )
    tools_planned: List[ToolPlan] = Field(
        default_factory=list,
        description="Ordered list of tools to call."
    )
    species_mentioned: List[str] = Field(
        default_factory=list,
        description=(
            "All species names mentioned in the query exactly as the user wrote them. "
            "Empty list if no species mentioned."
        )
    )
    requires_lsid: bool = Field(
        ...,
        description=(
            "True if any planned tool requires a resolved LSID. "
            "Triggers the resolver before extraction."
        )
    )
    reasoning: str = Field(
        ...,
        description=(
            "Step-by-step explanation of why these tools were selected. "
            "Required for traceability. Min 1 sentence per tool planned."
        )
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if the query is too ambiguous to plan without user input."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="The specific question to ask the user. Required if clarification_needed=True."
    )

    @model_validator(mode="after")
    def validate_tools(self) -> "PlannerOutput":
        # out_of_scope and unknown intents legitimately have no tools
        if self.intent in ("out_of_scope", "unknown"):
            return self
        must_calls = [t for t in self.tools_planned if t.priority == "must_call"]
        if not must_calls:
            raise ValueError(
                f"Intent '{self.intent}' requires at least one must_call tool."
            )
        return self
    
    @model_validator(mode="after")
    def validate_clarification(self) -> "PlannerOutput":
        if self.clarification_needed and not self.clarification_question:
            raise ValueError(
                "clarification_question is required when clarification_needed=True"
            )
        return self
    
    @model_validator(mode="after")
    def validate_species_for_lsid(self) -> "PlannerOutput":
        if self.requires_lsid and not self.species_mentioned:
            raise ValueError(
                "requires_lsid=True but species_mentioned is empty. "
                "Planner must extract at least one species name "
                "when a tool requires LSID."
            )
        return self
    
    @model_validator(mode="after")
    def validate_requires_lsid(self) -> "PlannerOutput":
        lsid_tools = {"get_occurrence_taxa_count", "get_species_distribution"}
        planned_tools = {t.tool_name for t in self.tools_planned}
        if planned_tools & lsid_tools:
            self.requires_lsid = True
        return self