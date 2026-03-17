from common.types import BaseModel, Field, field_validator, Optional, List

class SpeciesImageSearchParams(BaseModel):
    """Pydantic model for GET /imageSearch/{id} - Search for a taxon with images"""
    id: str = Field(...,
        description="The guid of a specific taxon (LSID)",
        examples=[
            "https://id.biodiversity.org.au/node/apni/29057",
            "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad"
        ]
    )
    
    start: Optional[int] = Field(None,
        description="The records offset, to enable paging",
        ge=1, examples=[1, 10, 20]
    )

    rows: Optional[int] = Field(None,
        description="The number of records to return, to enable paging",
        ge=1, le=100, examples=[5, 10, 20]
    )
    
    qc: Optional[str] = Field(None,
        description="Solr query context, passed on to the search engine"
    )
