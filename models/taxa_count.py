from common.types import BaseModel, Field, field_validator, Optional, List

class OccurrenceTaxaCountParams(BaseModel):
    """Pydantic model for /occurrences/taxaCount - Count occurrences for supplied taxa"""

    guids: str = Field(
        ...,
        description=(
            "Newline-separated taxonConceptIDs/LSIDs. "
            "Multiple species supported."
        ),
        examples=[
            # Single species
            "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad",
            # Multiple species
            "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad\nhttps://biodiversity.org.au/afd/taxa/f2f43ef9-89fd-4f89-8b06-0842e86cfe06",
        ]
    )

    fq: Optional[str] = Field(  
        None,
        description=(
            "Single filter query. Multiple filters MUST be combined "
            "with AND in one string — taxaCount does not support "
            "multiple fq parameters."
        ),
        examples=[
            "state:Queensland",
            "year:2023",
            "year:[2020 TO *]",
            "year:[2020 TO 2024]",
            "state:Queensland AND year:[2020 TO *]",
            "state:Queensland AND basis_of_record:HUMAN_OBSERVATION"
        ]
    )

    separator: Optional[str] = Field(
        "\n",
        description="Separator for guids parameter",
        examples=["\n", ",", "|"]
    )
