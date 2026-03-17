from common.types import BaseModel, Field, field_validator, Optional, List

VALID_LSID_PREFIXES = [
    "https://biodiversity.org.au/afd/taxa/",
    "https://id.biodiversity.org.au/",
    "https://www.catalogueoflife.org/data/taxon/",
]
class SpatialDistributionByLsidParams(BaseModel):
    lsid: str = Field(
        ...,
        description="Life Science Identifier for the taxon in https:// format",
        examples=[
            "https://biodiversity.org.au/afd/taxa/6a01d711-2ac6-4928-bab4-a1de1a58e995",
            "https://biodiversity.org.au/afd/taxa/ae56080e-4e73-457d-93a1-0be6a1d50f34"
        ]
    )
    @field_validator('lsid')
    def validate_lsid(cls, v):
        if not any(v.startswith(prefix) for prefix in VALID_LSID_PREFIXES):
            raise ValueError(
                f"Invalid LSID format. Must start with one of: {VALID_LSID_PREFIXES}"
            )
        return v