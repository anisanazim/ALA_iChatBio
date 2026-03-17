from __future__ import annotations

import logging
from typing import Union
from openai import AsyncOpenAI
import instructor
from instructor.exceptions import InstructorRetryException

from planning.models import PlannerOutput
from extraction.schemas.occurrence_search import OccurrenceSearchExtraction
from extraction.schemas.facet_breakdown import FacetBreakdownExtraction
from extraction.schemas.taxa_count import TaxaCountExtraction
from extraction.schemas.taxonomy import TaxonomyExtraction
from extraction.schemas.distribution import DistributionExtraction
from extraction.models import ExtractionResult

logger = logging.getLogger(__name__)



# Schema registry — maps intent to its extraction schema
INTENT_SCHEMA_MAP: dict[str, type] = {
    "occurrence_search": OccurrenceSearchExtraction,
    "facet_breakdown":   FacetBreakdownExtraction,
    "taxa_count":        TaxaCountExtraction,
    "taxonomy":          TaxonomyExtraction,
    "distribution":      DistributionExtraction,
}

EXTRACTOR_SYSTEM_PROMPT = """
You are a schema-guided parameter extractor for the Atlas of Living Australia (ALA).

The planner has already determined the user's intent: {intent}
Your job is to extract parameters from the user's query and populate the provided schema.

## CORE RULES

**Schema contract:**
- Populate ONLY fields defined in the schema
- Never invent fields or output anything outside the schema
- Your output must validate against the schema

**Extract, don't interpret:**
- Extract species names EXACTLY as the user wrote them
- Do NOT normalize, expand, or resolve species names
- Do NOT convert common names to scientific names
- "koala" stays "koala" — the resolver handles the rest

**Don't guess:**
- Only populate a field when the user's query clearly provides that information
- If unsure, leave the field empty
- Never hallucinate values

**Required fields:**
- If a required field cannot be determined from the query, do NOT guess
- Set clarification_needed=True and ask the user specifically for that information
- Write a clear, specific question in clarification_question

**Clarification:**
- Set clarification_needed=True only when a required field is genuinely ambiguous
  or missing and cannot be reasonably inferred
- Write a specific, helpful question in clarification_question
- Do NOT ask for clarification on optional fields
- Do NOT ask for clarification when you can reasonably infer the value

## TEMPORAL RULES

Convert natural language to typed year fields:
- "after X" / "since X" / "post X"  → year_from = X + 1
- "from X"                           → year_from = X
- "before X"                         → year_to = X - 1
- "until X"                          → year_to = X
- "in X" / "during X"               → year_exact = X
- "between X and Y"                  → year_from = X, year_to = Y
- "last N years" / "past N years"   → relative_years = N
  (do NOT set year_from or year_to when using relative_years)

## SPATIAL RULES

State normalization:
- QLD → Queensland
- NSW → New South Wales
- VIC → Victoria
- SA  → South Australia
- WA  → Western Australia
- TAS → Tasmania
- NT  → Northern Territory
- ACT → Australian Capital Territory

City → coordinates: extract lat and lon for any Australian city mentioned.

## SEASONAL RULES (Southern Hemisphere)

- Summer → months = [12, 1, 2]
- Autumn → months = [3, 4, 5]
- Winter → months = [6, 7, 8]
- Spring → months = [9, 10, 11]

## BASIS OF RECORD

Extract only when explicitly stated:
- human observations / sightings  → HUMAN_OBSERVATION
- preserved / specimens           → PRESERVED_SPECIMEN
- machine / sensor                → MACHINE_OBSERVATION
- living                          → LIVING_SPECIMEN
- fossils                         → FOSSIL_SPECIMEN
- material samples                → MATERIAL_SAMPLE
"""


class ALAExtractor:
    """
    Extracts typed parameters from a natural language query.

    Single responsibility: given a raw query and a PlannerOutput,
    return a typed extraction result for the planned intent.

    Does not call APIs. Does not resolve species. Does not build URLs.
    """

    def __init__(self, openai_client: AsyncOpenAI):
        self.client = instructor.from_openai(openai_client)

    async def extract(
        self,
        query: str,
        plan: PlannerOutput,
    ) -> ExtractionResult:
        """
        Extract parameters from the user query based on the planned intent.

        Args:
            query: Raw natural language query from the user
            plan:  PlannerOutput from the planner

        Returns:
            Typed extraction result for the planned intent

        Raises:
            ValueError: If intent is out_of_scope, unknown, or unsupported
            InstructorRetryException: If LLM fails to produce valid output after retries
        """
        intent = plan.intent

        # These intents have no extraction step
        if intent in ("out_of_scope", "unknown", "conservation"):
            raise ValueError(
                f"Intent '{intent}' does not require parameter extraction."
            )

        schema = INTENT_SCHEMA_MAP.get(intent)
        if not schema:
            raise ValueError(f"No extraction schema registered for intent: {intent}")

        system_prompt = EXTRACTOR_SYSTEM_PROMPT.format(intent=intent)

        logger.warning(f"[EXTRACTOR] Extracting for intent: {intent}")
        logger.warning(f"[EXTRACTOR] Schema: {schema.__name__}")

        try:
            result = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": query},
                ],
                response_model=schema,
                temperature=0,
                max_retries=2,
            )
        except InstructorRetryException as e:
            logger.error(f"[EXTRACTOR] Failed after retries for intent '{intent}': {e}")
            raise
        except Exception as e:
            logger.error(f"[EXTRACTOR] Unexpected error for intent '{intent}': {e}")
            raise

        logger.warning(f"[EXTRACTOR] Result: {result.model_dump(exclude_none=True)}")

        if result.clarification_needed:
            logger.warning(
                f"[EXTRACTOR] Clarification needed: {result.clarification_question}"
            )

        return result