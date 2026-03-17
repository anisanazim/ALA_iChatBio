from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing_extensions import override

from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentCard, AgentEntrypoint

from ala_logic import ALA
from extraction.models import ExtractionResult
from planning.planner import ALAPlanner
from extraction.extractor import ALAExtractor
from resolution.resolver import ALAParameterResolver
from routing.router import ALARouter
from execution.executor import ALAExecutor
from common.config import get_config_value

from instructor.exceptions import InstructorRetryException

logger = logging.getLogger(__name__)


class UnifiedALAParams(BaseModel):
    query: str = Field(
        ...,
        description="Natural language query about Australian biodiversity data"
    )
    context: Optional[str] = Field(
        None,
        description="Additional context or specific requirements"
    )

def _get_species_from_extraction(extraction: ExtractionResult) -> list[str]:
    """Get species list from typed extraction — always cleaner than planner species."""
    species = getattr(extraction, "species", None)
    if not species:
        return []
    if isinstance(species, list):
        return [s for s in species if s]
    return [species]

class ALAAgent(IChatBioAgent):
    """
    Thin entry point. Wires pipeline components together.
    No business logic lives here.

    Pipeline:
        PLANNER → EXTRACTOR → RESOLVER → ROUTER → EXECUTOR
    """

    def __init__(self):
        # Infrastructure
        openai_client = AsyncOpenAI(
            api_key=get_config_value("OPENAI_API_KEY"),
            base_url=get_config_value(
                "OPENAI_BASE_URL", "https://api.ai.it.ufl.edu"
            ),
        )
        redis_client = aioredis.from_url(
            "redis://localhost:6379",
            decode_responses=True
        )
        ala_logic = ALA()

        # Pipeline components
        self.planner  = ALAPlanner(openai_client)
        self.extractor = ALAExtractor(openai_client)
        self.resolver  = ALAParameterResolver(ala_logic, redis_client)
        self.router    = ALARouter()
        self.executor  = ALAExecutor(ala_logic)

    @override
    def get_agent_card(self) -> AgentCard:
        return AgentCard(
            name="Atlas of Living Australia Agent",
            description=(
                "Search Australian biodiversity data using natural language. "
                "Ask about species occurrences, distributions, taxonomy, and more."
            ),
            icon="https://www.ala.org.au/wp-content/uploads/2018/06/logo-ALA-1-300x140.png",
            url="http://localhost:9999",
            entrypoints=[
                AgentEntrypoint(
                    id="search_biodiversity_data",
                    description=(
                        "Search Australian biodiversity data using natural language. "
                        "Ask about species occurrences, distributions, taxonomy, "
                        "record counts, and analytical breakdowns."
                    ),
                    parameters=UnifiedALAParams
                )
            ]
        )

    @override
    async def run(
        self,
        context: ResponseContext,
        request: str,
        entrypoint: str,
        params: UnifiedALAParams,
    ) -> None:
        """
        Execute the full pipeline for a user query.

        Failure handling:
            P1 — clarification needed from planner  → ask user, return
            P2 — out of scope                       → decline, return
            P3 — extractor clarification needed     → ask user, return
            P4 — resolution clarification needed    → ask user, return
            P5 — LLM validation failure             → safe fallback message
            P6 — router ValueError (no LSID etc.)  → safe fallback message
        """
        logger.warning(f"[AGENT] Query: {request}")

        if not get_config_value("OPENAI_API_KEY"):
            await context.reply(
                "Configuration error: OpenAI API key not found."
            )
            return

        # ------------------------------------------------------------------
        # STEP 1: PLAN
        # ------------------------------------------------------------------
        try:
            plan = await self.planner.plan(request)
        except Exception as e:
            logger.error(f"[AGENT] Planner failed: {e}")
            await context.reply(
                "I was unable to understand your request. "
                "Please try rephrasing your query."
            )
            return

        logger.warning(f"[AGENT] Plan: intent={plan.intent}, tools={[t.tool_name for t in plan.tools_planned]}")

        # P1 — planner needs clarification
        if plan.clarification_needed:
            await context.reply(plan.clarification_question)
            return

        # P2 — out of scope
        if plan.intent in ("out_of_scope", "unknown"):
            await context.reply(
                "I can only answer questions about Australian biodiversity data "
                "available through the Atlas of Living Australia. "
                "This query appears to be outside that scope."
            )
            return

        # ------------------------------------------------------------------
        # STEP 2: EXTRACT
        # ------------------------------------------------------------------
        try:
            extraction = await self.extractor.extract(request, plan)
        except InstructorRetryException as e:
            logger.error(f"[AGENT] Extractor failed after retries: {e}")
            await context.reply(
                "I had trouble interpreting the parameters in your query. "
                "Please try rephrasing or simplifying your request."
            )
            return
        except ValueError as e:
            # Intent has no extraction step — shouldn't reach here
            logger.error(f"[AGENT] Extractor ValueError: {e}")
            await context.reply(
                "An internal error occurred during parameter extraction."
            )
            return

        logger.warning(f"[AGENT] Extraction: {extraction.model_dump(exclude_none=True)}")

        # P3 — extractor needs clarification
        if extraction.clarification_needed:
            await context.reply(extraction.clarification_question)
            return

        # ------------------------------------------------------------------
        # STEP 3: RESOLVE (only if LSID needed)
        # ------------------------------------------------------------------
        resolution = None

        if plan.requires_lsid:
            species_to_resolve = _get_species_from_extraction(extraction)

            if not species_to_resolve:
                await context.reply(
                    "I couldn't identify any species in your query. "
                    "Please specify a species name."
                )
                return

            try:
                resolution = await self.resolver.resolve_all(species_to_resolve)
            except Exception as e:
                logger.error(f"[AGENT] Resolver failed: {e}")
                await context.reply(
                    "I was unable to resolve the species name(s) in your query. "
                    "Please check the spelling or try a scientific name."
                )
                return

            logger.warning(f"[AGENT] Resolution: {resolution}")

            # P4 — resolution needs clarification
            if resolution.clarification_needed:
                await context.reply(resolution.clarification_question)
                return

        # ------------------------------------------------------------------
        # STEP 4: ROUTE
        # ------------------------------------------------------------------
        try:
            routed = self.router.route(plan, extraction, resolution)
        except ValueError as e:
            # P6 — router error (e.g. no LSID for distribution)
            logger.error(f"[AGENT] Router failed: {e}")
            await context.reply(
                "I was unable to build the API parameters for your request. "
                f"Reason: {e}"
            )
            return

        logger.warning(f"[AGENT] Routed tools: {list(routed.keys())}")

        if not routed:
            await context.reply(
                "No tools were matched for your request. "
                "Please try a more specific query."
            )
            return

        # ------------------------------------------------------------------
        # STEP 5: EXECUTE
        # ------------------------------------------------------------------
        await self.executor.execute(
            context=context,
            plan=plan,
            routed=routed,
            extraction=extraction,
            resolution=resolution,
        )

        logger.warning(f"[AGENT] Pipeline complete for query: {request}")