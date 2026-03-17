from __future__ import annotations

import logging
from typing import Optional

from planning.models import PlannerOutput
from resolution.models import ResolutionResult
from extraction.models import ExtractionResult
from extraction.schemas.distribution import DistributionExtraction

from execution.tools.occurrence_search import run_occurrence_search
from execution.tools.facet_breakdown import run_facet_breakdown
from execution.tools.taxa_count import run_taxa_count
from execution.tools.taxonomy import run_taxonomy
from execution.tools.distribution import run_distribution

from models.occurrence import OccurrenceSearchParams
from models.facets import OccurrenceFacetsParams
from models.taxa_count import OccurrenceTaxaCountParams
from models.bie import SpeciesBieSearchParams
from models.distribution import SpatialDistributionByLsidParams

logger = logging.getLogger(__name__)


class ALAExecutor:
    """
    Executes planned tools in priority order.

    Single responsibility: given a router output (tool_name → typed API params),
    call the correct tool function and stream results to context.

    Execution phases:
        Phase 1 — must_call tools: if any fails, stop immediately
        Phase 2 — optional tools:  if any fails, log and continue
    """

    def __init__(self, ala_logic):
        self.ala_logic = ala_logic

    async def execute(
        self,
        context,
        plan: PlannerOutput,
        routed: dict[str, object],
        extraction: ExtractionResult,
        resolution: Optional[ResolutionResult] = None,
    ) -> None:
        """
        Execute all planned tools.

        Args:
            context:    iChatBio ResponseContext
            plan:       PlannerOutput — provides tool priority order
            routed:     Dict of tool_name → typed API params (from ALARouter)
            extraction: ExtractionResult — used for display names etc.
            resolution: ResolutionResult — used to get species display names
        """
        intent = plan.intent
        logger.warning(f"[EXECUTOR] Starting execution for intent: {intent}")
        logger.warning(f"[EXECUTOR] Tools to execute: {list(routed.keys())}")

        # Split tools by priority
        must_call = [t for t in plan.tools_planned if t.priority == "must_call"]
        optional  = [t for t in plan.tools_planned if t.priority == "optional"]

        executed = []

        # ---------------------------------------------------------------
        # PHASE 1: must_call tools — stop on first failure
        # ---------------------------------------------------------------
        async with context.begin_process("Executing planned tools") as process:
            await process.log(
                f"Tool plan: {[(t.tool_name, t.priority) for t in plan.tools_planned]}"
            )
            await process.log(f"Phase 1: {len(must_call)} must_call tool(s)")

            for tool_plan in must_call:
                tool_name = tool_plan.tool_name

                if tool_name in executed:
                    await process.log(f"Skipping '{tool_name}' — already executed")
                    continue

                params = routed.get(tool_name)
                if params is None:
                    await process.log(f"No routed params for '{tool_name}' — skipping")
                    continue

                await process.log(f"Executing: {tool_name} — {tool_plan.reason}")

                try:
                    await self._call_tool(context, tool_name, params, extraction, resolution)
                    executed.append(tool_name)
                    await process.log(f"'{tool_name}' completed successfully")

                except Exception as e:
                    logger.error(f"[EXECUTOR] must_call '{tool_name}' failed: {e}")
                    await process.log(f"'{tool_name}' FAILED: {e}")
                    await context.reply(
                        f"A required operation failed and the request could not be completed: {e}"
                    )
                    return  # Stop — don't execute optional tools

            # ---------------------------------------------------------------
            # PHASE 2: optional tools — log failures and continue
            # ---------------------------------------------------------------
            if optional:
                await process.log(f"Phase 2: {len(optional)} optional tool(s)")

                for tool_plan in optional:
                    tool_name = tool_plan.tool_name

                    if tool_name in executed:
                        await process.log(f"Skipping '{tool_name}' — already executed")
                        continue

                    params = routed.get(tool_name)
                    if params is None:
                        await process.log(f"No routed params for '{tool_name}' — skipping")
                        continue

                    await process.log(f"Executing optional: {tool_name} — {tool_plan.reason}")

                    try:
                        await self._call_tool(context, tool_name, params, extraction, resolution)
                        executed.append(tool_name)
                        await process.log(f"'{tool_name}' completed")

                    except Exception as e:
                        logger.warning(f"[EXECUTOR] optional '{tool_name}' failed: {e}")
                        await process.log(f"Optional '{tool_name}' failed (continuing): {e}")
                        # Do not return — keep going

            await process.log(
                f"Execution complete: {len(executed)} tool(s) executed"
            )

    async def _call_tool(
        self,
        context,
        tool_name: str,
        params: object,
        extraction: ExtractionResult,
        resolution: Optional[ResolutionResult],
    ) -> None:
        """
        Dispatch a single tool by name.

        Each tool receives (context, ala_logic, typed_params).
        Distribution also receives species_name for display.
        """
        ala = self.ala_logic

        if tool_name == "search_species_occurrences":
            assert isinstance(params, OccurrenceSearchParams)
            await run_occurrence_search(context, ala, params)

        elif tool_name == "get_occurrence_breakdown":
            assert isinstance(params, OccurrenceFacetsParams)
            await run_facet_breakdown(context, ala, params)

        elif tool_name == "get_occurrence_taxa_count":
            assert isinstance(params, OccurrenceTaxaCountParams)
            await run_taxa_count(context, ala, params)

        elif tool_name == "lookup_species_info":
            assert isinstance(params, SpeciesBieSearchParams)
            await run_taxonomy(context, ala, params)

        elif tool_name == "get_species_distribution":
            assert isinstance(params, SpatialDistributionByLsidParams)
            # Get display name from resolution if available
            species_name = _get_display_name(extraction, resolution)
            await run_distribution(context, ala, params, species_name=species_name)

        else:
            raise ValueError(f"Unknown tool: '{tool_name}'")


def _get_display_name(
    extraction: ExtractionResult,
    resolution: Optional[ResolutionResult],
) -> str:
    """
    Get a human-readable species name for display in replies.
    Prefers resolved scientific name, falls back to extraction, then default.
    """
    # Try resolved scientific name first
    if resolution and resolution.species:
        resolved = resolution.species[0]
        if resolved.scientific_name:
            return resolved.scientific_name
        if resolved.original_name:
            return resolved.original_name

    # Fall back to extraction
    if hasattr(extraction, "species") and extraction.species:
        species = extraction.species
        if isinstance(species, list):
            return species[0] if species else "Unknown species"
        return str(species)

    return "Unknown species"