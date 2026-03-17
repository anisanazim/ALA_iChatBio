from __future__ import annotations

from typing import Optional
from pydantic import Field, model_validator
from extraction.schemas.base import ExtractionBase


class TaxaCountExtraction(ExtractionBase):
    """
    Extraction schema for taxa_count intent.
    Filled by the extractor LLM from the raw user query.
    Router maps this to OccurrenceTaxaCountParams.

    Note: species resolution (LSID) is handled by the resolver.
    Extractor only needs species name and filters.
    """

    # --- Core ---
    species: list[str] = Field(
        ...,
        description=(
            "All species names exactly as the user wrote them. "
            "One entry per species. "
            "Multi-species: ['koala', 'wombat']."
        ),
        min_length=1
    )

    # --- Filters ---
    # Note: router combines these into a single fq string with AND
    state: Optional[str] = Field(
        None,
        description=(
            "Filter to a specific state. "
        )
    )
    year_exact: Optional[int] = Field(
        None,
        description="Exact year filter. Use for 'in YYYY'.",
        ge=1800, le=2100
    )
    year_from: Optional[int] = Field(
        None,
        description=(
            "Start of year range (inclusive). "
            "after/since X → year_from = X + 1. "
            "from X / between X and Y → year_from = X."
        ),
        ge=1800, le=2100
    )
    year_to: Optional[int] = Field(
        None,
        description=(
            "End of year range (inclusive). "
            "before X → year_to = X - 1. "
            "between X and Y → year_to = Y."
        ),
        ge=1800, le=2100
    )
    relative_years: Optional[int] = Field(
        None,
        description="For 'last N years'. Extract N only. Do NOT set year_from/year_to.",
        ge=1
    )

    @model_validator(mode="after")
    def validate_temporal(self) -> "TaxaCountExtraction":
        if self.relative_years and (self.year_exact or self.year_from or self.year_to):
            raise ValueError(
                "Cannot combine relative_years with absolute year fields."
            )
        return self