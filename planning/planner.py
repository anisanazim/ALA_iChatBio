import logging
from openai import AsyncOpenAI
import instructor

from planning.models import PlannerOutput
from planning.registry import registry

logger = logging.getLogger(__name__)


class ALAPlanner:
    """
    Plans which ALA tools to call for a given user query.

    Single responsibility: read raw query → produce PlannerOutput.
    Does not extract params, does not call APIs.
    """

    def __init__(self, openai_client: AsyncOpenAI):
        self.client = instructor.from_openai(openai_client)
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return f"""
You are a biodiversity research planner for the Atlas of Living Australia (ALA).

Your job:
1. Understand what the user is asking
2. Select the right tools to answer their query
3. Explain your reasoning clearly

## AVAILABLE TOOLS

{registry.get_all_for_planner()}

## RULES

**Intent selection:**
- Choose the single intent that best describes the primary goal
- If the query has two valid intents, pick the more specific one
- Use "unknown" only if the query is genuinely unresolvable

**Tool selection:**
- Only plan tools that are needed — do not add optional tools speculatively
- A tool is "must_call" if the query cannot be answered without it
- A tool is "optional" if it enriches the response but is not required

**Species extraction:**
- Extract ALL species mentioned, exactly as the user wrote them
- Include common names, scientific names, and indigenous names as-is
- If the user says "kangaroo" extract "kangaroo" — do not expand to scientific name

**LSID requirement:**
- Set requires_lsid=true if ANY planned tool requires an LSID
- Tools that require LSID: get_species_distribution, get_occurrence_taxa_count
- Tools that do NOT require LSID: search_species_occurrences, get_occurrence_breakdown, lookup_species_info

**Clarification:**
- Only request clarification if the query is genuinely ambiguous
- Do NOT request clarification for incomplete queries you can reasonably handle
- If clarification is needed, write a specific, helpful question for the user

**Out of scope queries:**
- Set intent="out_of_scope", tools_planned=[], clarification_needed=False
- The executor will decline gracefully with an explanation
- ALA does NOT provide data on any of the following:
  * Genetic or genomic data
  * Behaviour or physiology
  * Economic impact data
  * Environmental monitoring or climate data
  * Disease, health, or pathogen data
  * Captive breeding programs
  * Habitat quality assessments

**Partial out of scope:**
- If query is MOSTLY in-scope but includes one out-of-scope element,
  plan the in-scope tools and note the limitation in reasoning
- Only use intent="out_of_scope" if the ENTIRE query is out of scope

**Reasoning:**
- Write at least one sentence per planned tool explaining why it was selected
- This is required for supervisor traceability

"""

    async def plan(self, query: str) -> PlannerOutput:
        """
        Plans tool execution for a user query.

        Args:
            query: Raw natural language query from the user

        Returns:
            PlannerOutput with intent, tools, species, reasoning
        """
        logger.warning(f"[PLANNER] Planning query: {query}")

        result = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": query},
            ],
            response_model=PlannerOutput,
            max_retries=2,
        )

        logger.warning(f"[PLANNER] Intent: {result.intent}")
        logger.warning(f"[PLANNER] Query type: {result.query_type}")
        logger.warning(f"[PLANNER] Tools: {[(t.tool_name, t.priority) for t in result.tools_planned]}")
        logger.warning(f"[PLANNER] Species: {result.species_mentioned}")
        logger.warning(f"[PLANNER] Requires LSID: {result.requires_lsid}")
        logger.warning(f"[PLANNER] Reasoning: {result.reasoning}")

        if result.clarification_needed:
            logger.warning(f"[PLANNER] Clarification needed: {result.clarification_question}")

        return result