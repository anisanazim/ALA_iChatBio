from __future__ import annotations

from typing import Optional
from pydantic import Field, model_validator
from extraction.schemas.base import ExtractionBase

class TaxonomyExtraction(ExtractionBase):
    """
    Extraction schema for taxonomy intent.
    Filled by the extractor LLM from the raw user query.
    Router maps this to SpeciesBieSearchParams.

    Intentionally simple — BIE search only needs the species name.
    """

    species: str = Field(
        ...,
        description=(
            "Species name exactly as the user wrote it. "
            "Common name, scientific name, indigenous name, or LSID. "
            "Do NOT normalize or expand."
        ),
        examples=["koala", "Phascolarctos cinereus", "Guba", "platypus"]
    )

    include_image: bool = Field(
    False,
    description=(
        "Set to True if the user explicitly asks for an image, picture, or photo of the species. "
        "False for all other requests including general species info, taxonomy, or classification."
    ),
    examples=["image of koala → True", "show me a picture of platypus → True", "tell me about koala → False"]
    
    )
