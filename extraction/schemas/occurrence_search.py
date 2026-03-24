from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import Field, model_validator
from extraction.schemas.base import ExtractionBase, BASIS_OF_RECORD_VALUES

class OccurrenceSearchExtraction(ExtractionBase):
    """
    Extraction schema for occurrence_search intent.
    Filled by the extractor LLM from the raw user query.
    Router maps this to OccurrenceSearchParams.
    """

    # --- Core ---
    species: Optional[str] = Field(
        None,
        description=(
            "Species name exactly as the user wrote it. "
            "Common name, scientific name, or LSID. "
            "Do NOT normalize or expand. "
            "Omit if no species mentioned."
        ),
        examples=["koala", "Phascolarctos cinereus", "rainbow bee-eater"]
    )

    # --- Spatial ---
    state: Optional[str] = Field(
        None,
        description=(
            "Australian state or territory."
        )
    )
    lat: Optional[float] = Field(
        None,
        description="Decimal latitude. Extract from city name if mentioned.",
        ge=-90, le=90
    )
    lon: Optional[float] = Field(
        None,
        description="Decimal longitude. Extract from city name if mentioned.",
        ge=-180, le=180
    )
    city: Optional[str] = Field(
        None,
        description="City name as written by user, if spatial search is city-based."
    )
    radius: Optional[float] = Field(
        None,
        description="Search radius in kilometres.",
        gt=0
    )

    # --- Temporal ---
    year_exact: Optional[int] = Field(
        None,
        description="Exact year. Use for 'in YYYY' or 'during YYYY'.",
        ge=1800, le=2100
    )
    year_from: Optional[int] = Field(
        None,
        description=(
            "Start of year range (inclusive). "
            "Use for 'after X', 'since X', 'from X', 'between X and Y'. "
            "after/since X → year_from = X + 1. "
            "from X → year_from = X."
        ),
        ge=1800, le=2100
    )
    year_to: Optional[int] = Field(
        None,
        description=(
            "End of year range (inclusive). "
            "Use for 'before X', 'until X', 'between X and Y'. "
            "before X → year_to = X - 1."
        ),
        ge=1800, le=2100
    )
    relative_years: Optional[int] = Field(
        None,
        description=(
            "For 'last N years' or 'past N years'. "
            "Extract N only. Router computes actual year. "
            "Do NOT set year_from or year_to when using this."
        ),
        ge=1
    )
    months: Optional[List[int]] = Field(
        None,
        description=(
            "Month numbers (1-12). "
            "Seasons (Southern Hemisphere): "
            "summer=[12,1,2], autumn=[3,4,5], winter=[6,7,8], spring=[9,10,11]."
        )
    )

    # --- Record filters ---
    basis_of_record: Optional[BASIS_OF_RECORD_VALUES] = Field(
        None,
        description=(
            "Type of record. Extract only when explicitly stated. "
            "specimens→PreservedSpecimen, observations→HumanObservation, "
            "machine→MachineObservation, living→LivingSpecimen, "
            "fossils→FossilSpecimen."
        )
    )
    has_images: Optional[bool] = Field(
        None,
        description="True if user wants only records with images/photos."
    )
    has_coordinates: Optional[bool] = Field(
        None,
        description="True if user wants only records with coordinates."
    )

    # --- Taxonomic filters ---
    kingdom: Optional[str] = Field(None, description="Taxonomic kingdom. Extract only if explicitly mentioned.")
    classs: Optional[str] = Field(
    None,
    description=(
        "Taxonomic class. Extract only if user mentions a broad group. "
        "birds→Aves, mammals→Mammalia, reptiles→Reptilia, "
        "fish→Actinopterygii, frogs/amphibians→Amphibia, insects→Insecta."
    )
    )
    family:  Optional[str] = Field(None, description="Taxonomic family. Extract only if explicitly mentioned.")
    genus:   Optional[str] = Field(None, description="Taxonomic genus. Extract only if explicitly mentioned.")

    # --- Pagination ---
    page_size: Optional[int] = Field(
        None,
        description="Number of records to return. Default is 20 unless user specifies.",
        ge=1, le=1000
    )

    image_count: Optional[int] = Field(
    None,
    description=(
        "Number of images to display. Extract from 'show me 5 photos', "
        "'I want to see 10 images' etc. Only set when has_images=True."
    ),
    ge=1, le=20
    )
    
    @model_validator(mode="after")
    def validate_temporal_consistency(self) -> "OccurrenceSearchExtraction":
        has_temporal_field = any([
            self.year_exact,
            self.year_from,
            self.year_to,
            self.relative_years,
            self.months,
        ])
        # Cannot mix relative_years with absolute year fields
        if self.relative_years and (self.year_exact or self.year_from or self.year_to):
            raise ValueError(
                "Cannot combine relative_years with year_exact/year_from/year_to. "
                "Use one or the other."
            )
        return self

    @model_validator(mode="after")
    def validate_spatial_consistency(self) -> "OccurrenceSearchExtraction":
        # lat/lon must come together
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat and lon must both be present or both be absent.")
        # radius requires lat/lon
        if self.radius and not self.lat:
            raise ValueError("radius requires lat and lon.")
        return self