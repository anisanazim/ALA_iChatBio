from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal

BASIS_OF_RECORD_VALUES = Literal[
    "HUMAN_OBSERVATION",
    "PRESERVED_SPECIMEN",
    "MACHINE_OBSERVATION",
    "LIVING_SPECIMEN",
    "FOSSIL_SPECIMEN",
    "MATERIAL_SAMPLE",
    "OCCURRENCE",
    "OBSERVATION",
]

AUSTRALIAN_STATES = [
    "Australian Capital Territory",
    "New South Wales",
    "Northern Territory", 
    "Queensland",
    "South Australia",
    "Tasmania",
    "Victoria",
    "Western Australia",
]

class ExtractionBase(BaseModel):
    clarification_needed: bool = Field(
        default=False,
        description="True if a required parameter is missing or ambiguous."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask the user. Required if clarification_needed=True."
    )

    @model_validator(mode="after")
    def validate_clarification(self) -> "ExtractionBase":
        if self.clarification_needed and not self.clarification_question:
            raise ValueError(
                "clarification_question required when clarification_needed=True."
            )
        return self