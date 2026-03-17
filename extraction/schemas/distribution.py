from __future__ import annotations

from typing import Optional
from pydantic import Field, model_validator
from extraction.schemas.base import ExtractionBase

class DistributionExtraction(ExtractionBase):
    """
    Extraction schema for distribution intent.
    Filled by the extractor LLM from the raw user query.
    Router maps this to SpatialDistributionByLsidParams.

    Note: LSID is provided by the resolver — extractor only needs species name.
    The resolver runs before extraction for this intent.
    """

    species: str = Field(
        ...,
        description=(
            "Species name exactly as the user wrote it. "
            "Common name, scientific name, or LSID. "
            "Do NOT normalize or expand."
        ),
        examples=["koala", "Tasmanian Devil", "Phascolarctos cinereus"]
    )