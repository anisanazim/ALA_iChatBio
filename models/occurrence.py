
from common.types import BaseModel, Field, field_validator, Optional, List

class OccurrenceSearchParams(BaseModel):
    """Pydantic model for ALA Occurrence Search API - matches real API structure while keeping user-friendly interface"""
    
    # Core search parameters
    q: Optional[str] = Field(None, 
        description="Main search query. Can be species name, vernacular name, or complex queries",
        examples=["Kangaroo", "Phascolarctos cinereus", "vernacularName:koala", "genus:Macropus","species:cinereus", "kingdom:Animalia"]
    )
    
    fq: Optional[List[str]] = Field(None,
        description="Filter queries array. Used for taxonomic, geographic, and temporal filters",
        examples=[["state:Queensland"], ["year:2020", "basis_of_record:HumanObservation"]]
    )
    
    fl: Optional[str] = Field(None,
        description="Fields to return in the search response",
        examples=["scientificName,commonName,decimalLatitude,decimalLongitude,eventDate"]
    )
    
    # Faceting parameters
    facets: Optional[List[str]] = Field(None,
        description="The facets to be included by the search",
        examples=[["basis_of_record", "state", "year"]]
    )
    
    flimit: Optional[int] = Field(None,
        description="The limit for the number of facet values to return",
        ge=1, examples=[10, 50]
    )
    
    fsort: Optional[str] = Field(None,
        description="The sort order for facets ('count' or 'index')",
        examples=["count", "index"]
    )
    
    foffset: Optional[int] = Field(None,
        description="The offset of facets to return",
        ge=0
    )
    
    fprefix: Optional[str] = Field(None,
        description="The prefix to limit facet values"
    )
    
    # Pagination parameters
    start: Optional[int] = Field(0,
        description="Paging start index",
        ge=0
    )
    
    pageSize: Optional[int] = Field(1000,
        description="Number of records to return per page",
        ge=1, le=1000
    )
    
    # Sorting parameters
    sort: Optional[str] = Field(None,
        description="The sort field to use",
        examples=["scientificName", "eventDate", "score"]
    )
    
    dir: Optional[str] = Field(None,
        description="Direction of sort ('asc' or 'desc')",
        examples=["asc", "desc"]
    )
    
    # Advanced parameters
    includeMultivalues: Optional[bool] = Field(None,
        description="Include multi values"
    )
    
    qc: Optional[str] = Field(None,
        description="The query context to be used for the search. This will be used to generate extra query filters."
    )
    
    facet: Optional[bool] = Field(None,
        description="Enable/disable facets",
        examples=["true", "false"]
    )
    
    qualityProfile: Optional[str] = Field(None,
        description="The quality profile to use"
    )
    
    disableAllQualityFilters: Optional[bool] = Field(None,
        description="Disable all default filters"
    )
    
    disableQualityFilter: Optional[List[str]] = Field(None,
        description="Default filters to disable"
    )
    
    # Spatial search parameters
    radius: Optional[float] = Field(None,
        description="Radius for a spatial search in kilometers",
        gt=0, examples=[10.0, 50.0]
    )
    
    lat: Optional[float] = Field(None,
        description="Decimal latitude for the spatial search",
        ge=-90, le=90, examples=[-27.4698]
    )
    
    lon: Optional[float] = Field(None,
        description="Decimal longitude for the spatial search",
        ge=-180, le=180, examples=[153.0251]
    )
    
    wkt: Optional[str] = Field(None,
        description="Well Known Text for the spatial search",
        examples=["POLYGON((140 -40, 150 -40, 150 -30, 140 -30, 140 -40))"]
    )
    
    # Image metadata
    im: Optional[bool] = Field(None,
        description="Include image metadata",
        examples=["true", "false"]
    )