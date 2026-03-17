from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import Field, field_validator, model_validator
from extraction.schemas.base import ExtractionBase, BASIS_OF_RECORD_VALUES


ALLOWED_FACETS = Literal[
    "state", "year", "month", "species", "kingdom", "phylum",
    "class", "order", "family", "genus", "basis_of_record",
    "institution_uid", "data_resource_uid", "multimedia",
]

class FacetBreakdownExtraction(ExtractionBase):
    """
    Extraction schema for facet_breakdown intent.
    Filled by the extractor LLM from the raw user query.
    Router maps this to OccurrenceFacetsParams.
    """

    # --- Core ---
    species: Optional[str] = Field(
        None,
        description=(
            "Species name exactly as the user wrote it. "
            "Omit if no species mentioned — facets work database-wide."
        )
    )

    # --- Facets ---
    facets: List[str] = Field(
        ...,
        description=(
            "One or more facet fields to group by. "
            "Allowed values: state, year, month, species, kingdom, phylum, "
            "class, order, family, genus, basis_of_record, institution_uid. "
            "Plural → singular: families→family, genera→genus, orders→order. "
            "Seasonal/monthly queries → month. "
            "State comparison → state. "
            "Taxonomic breakdown → relevant rank field."
        ),
        min_length=1
    )

    fsort: Optional[Literal["count", "index"]] = Field(
        None,
        description=(
            "Sort order for facet values. "
            "count = most records first (use for top-N, most common, highest). "
            "index = alphabetical or calendar order (use for trends over time, monthly distributions)."
        )
    )

    flimit: Optional[int] = Field(
        None,
        description=(
            "Number of facet values to return. "
            "Extract from 'top N', 'top 10 species' etc."
        ),
        ge=1
    )

    # --- Filters ---
    state: Optional[str] = Field(
        None,
        description=(
            "Filter to a specific state. "
            "Do NOT set if user is comparing states — use facets=[state] instead."
        )
    )
    basis_of_record: Optional[BASIS_OF_RECORD_VALUES] = Field(
        None,
        description="Filter to a specific record type."
    )
    year_exact: Optional[int] = Field(
        None,
        description="Exact year filter.",
        ge=1800, le=2100
    )
    year_from: Optional[int] = Field(
        None,
        description="Start of year range (inclusive). after/since X → year_from = X + 1.",
        ge=1800, le=2100
    )
    year_to: Optional[int] = Field(
        None,
        description="End of year range (inclusive). before X → year_to = X - 1.",
        ge=1800, le=2100
    )
    relative_years: Optional[int] = Field(
        None,
        description="For 'last N years'. Extract N only. Do NOT set year_from/year_to.",
        ge=1
    )

    @model_validator(mode="after")
    def validate_temporal(self) -> "FacetBreakdownExtraction":
        if self.relative_years and (self.year_exact or self.year_from or self.year_to):
            raise ValueError(
                "Cannot combine relative_years with absolute year fields."
            )
        return self

