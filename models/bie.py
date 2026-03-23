from common.types import BaseModel, Field, field_validator, Optional, List

class SpeciesBieSearchParams(BaseModel):
    """Pydantic model for GET /search - Search the BIE"""
    q: str = Field(...,
        description="Primary search query for the form field value e.g. q=rk_genus:Macropus or free text e.g q=gum",
        examples=["gum", "rk_genus:Macropus", "Eucalyptus", "kangaroo"]
    )

    fq: Optional[str] = Field(
        "idxtype:TAXON AND rank:species",
        description="Filters to be applied to the original query.",
        examples=["idxtype:TAXON AND rank:species", "imageAvailable:\"true\""]
    )
    
    start: Optional[int] = Field(0,
        description="The records offset, to enable paging",
        ge=0, examples=[0, 10, 20]
    )
    
    pageSize: Optional[int] = Field(100,
        description="The number of records to return",
        ge=1, le=100, examples=[5, 10, 20]
    )

    sort: Optional[str] = Field("score",
    description="The field to sort the records by",
    examples=["score", "commonNameSingle", "scientificName", "rank"]
    )
    
    dir: Optional[str] = Field("desc",
        description="Sort direction 'asc' or 'desc'",
        examples=["asc", "desc"]
    )
    
    facets: Optional[str] = Field(None,
        description="Comma separated list of fields to display facets for",
        examples=["datasetName,commonNameExact", "rank,genus"]
    )
