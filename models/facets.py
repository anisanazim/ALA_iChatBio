from common.types import BaseModel, Field, field_validator, Optional, List

class OccurrenceFacetsParams(BaseModel):
    """Pydantic model for GET /occurrences/facets - Get distinct facet counts"""
    
    # Core search parameters (same as search endpoint)
    q: Optional[str] = Field(None, 
        description="Main search query. Examples 'q=Kangaroo' or 'q=vernacularName:red'",
        examples=["Kangaroo", "vernacularName:koala", "scientificName:Phascolarctos"]
    )
    
    fq: Optional[List[str]] = Field(
        None,
        description=(
            "Filter queries. Multiple filters supported as a list. "
            "Examples: ['state:Queensland'], ['state:Queensland', 'year:[2020 TO *]']"
        ),
        examples=[
            ["state:Queensland"],
            ["state:Queensland", "year:[2020 TO *]"],
            ["basis_of_record:HUMAN_OBSERVATION"]
        ]
    )
    
    fl: Optional[str] = Field(None,
        description="Fields to return in the search response. Optional",
        examples=["scientificName,commonName,decimalLatitude,decimalLongitude"]
    )
    
    # Facet-specific parameters
    facets: Optional[List[str]] = Field(None,
        description="The facets to be included by the search",
        examples=[["basis_of_record", "state", "year"], ["institution_code", "collection_code"]]
    )
    
    flimit: Optional[int] = Field(None,
        description="The limit for the number of facet values to return",
        ge=1, examples=[10, 50, 100]
    )
    
    fsort: Optional[str] = Field(None,
        description="The sort order in which to return the facets. Either 'count' or 'index'",
        examples=["count", "index"]
    )
    
    foffset: Optional[int] = Field(None,
        description="The offset of facets to return. Used in conjunction to flimit",
        ge=0, examples=[0, 10, 20]
    )
    
    fprefix: Optional[str] = Field(None,
        description="The prefix to limit facet values",
        examples=["Aus", "New", "Qld"]
    )
    
    # Pagination parameters  
    start: Optional[int] = Field(0,
        description="Paging start index",
        ge=0
    )
    
    pageSize: Optional[int] = Field(1000,
        description="The number of records per page",
        ge=1, le=1000
    )
    
    # Sorting parameters
    sort: Optional[str] = Field(None,
        description="The sort field to use",
        examples=["scientificName", "eventDate"]
    )
    
    dir: Optional[str] = Field(None,
        description="Direction of sort",
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
        description="Enable/disable facets"
    )
    
    qualityProfile: Optional[str] = Field(None,
        description="The quality profile to use, null for default"
    )
    
    disableAllQualityFilters: Optional[bool] = Field(None,
        description="Disable all default filters"
    )
    
    disableQualityFilter: Optional[List[str]] = Field(None,
        description="Default filters to disable (currently can only disable on category, so it's a list of disabled category name)"
    )
    
    # Spatial search parameters
    radius: Optional[float] = Field(None,
        description="Radius for a spatial search",
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
