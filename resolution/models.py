from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ResolvedSpecies(BaseModel):
    """
    Resolution result for a single species name.
    Produced by ALAParameterResolver, consumed by the router.
    Never mutates extraction params.
    """

    original_name: str = Field(
        ...,
        description="Species name exactly as extracted by the planner e.g. 'koala'"
    )
    lsid: Optional[str] = Field(
        None,
        description="Resolved taxonConceptID (LSID) e.g. https://biodiversity.org.au/afd/taxa/..."
    )
    scientific_name: Optional[str] = Field(
        None,
        description="Resolved scientific name e.g. 'Phascolarctos cinereus'"
    )
    vernacular_name: Optional[str] = Field(
        None,
        description="Vernacular name from ALA e.g. 'Koala'"
    )
    rank: Optional[str] = Field(
        None,
        description="Taxonomic rank of the resolved match e.g. 'species' or 'genus'"
    )
    kingdom: Optional[str] = Field(None)
    family:  Optional[str] = Field(None)
    genus:   Optional[str] = Field(None)
    resolved: bool = Field(
        ...,
        description="True if resolution succeeded, False if no match found"
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if the species name was ambiguous or not found"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask the user if clarification_needed=True"
    )

    @property
    def display_name(self) -> str:
        """
        Human-readable name for use in response messages.
        Respects rank — genus-level matches include a note.
        """
        if not self.resolved:
            return self.original_name
        if self.rank == "genus" and self.scientific_name:
            return f"{self.scientific_name} (genus — all species included)"
        return self.scientific_name or self.original_name


class ResolutionResult(BaseModel):
    """
    Resolution result for all species in a query.
    Produced by ALAParameterResolver.resolve_all(), consumed by the router.
    """

    species: list[ResolvedSpecies] = Field(
        default_factory=list,
        description="One ResolvedSpecies per name in PlannerOutput.species_mentioned"
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if ANY species failed to resolve"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Combined question for all unresolved species"
    )

    @property
    def resolved_lsids(self) -> list[str]:
        """All successfully resolved LSIDs."""
        return [s.lsid for s in self.species if s.resolved and s.lsid]

    @property
    def all_resolved(self) -> bool:
        """True only if every species resolved successfully."""
        return all(s.resolved for s in self.species)