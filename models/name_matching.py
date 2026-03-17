from common.types import BaseModel, Field, field_validator, Optional, List

class NameMatchingSearchParams(BaseModel):
    """Parameters for scientific name search"""
    q: str = Field(..., description="Scientific name to search")
