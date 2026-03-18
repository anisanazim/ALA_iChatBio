from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from models.facets import OccurrenceFacetsParams

logger = logging.getLogger(__name__)


async def run_facet_breakdown(context, ala_logic, params: OccurrenceFacetsParams) -> None:
    """
    Execute facet breakdown and stream results to context.

    Args:
        context:   iChatBio ResponseContext
        ala_logic: ALA HTTP layer
        params:    Typed API params from router
    """
    # Build human-readable process description
    parts = []
    if params.q:
        parts.append(f"query: '{params.q}'")
    if params.fq:
        fq_list = params.fq if isinstance(params.fq, list) else [params.fq]
        parts.append(f"filters: {', '.join(fq_list)}")
    if params.facets:
        parts.append(f"facets: {', '.join(params.facets)}")

    search_context = (" with " + ", ".join(parts)) if parts else " for all occurrence data"

    async with context.begin_process(
        f"Getting occurrence breakdowns{search_context}"
    ) as process:
        await process.log(
            "Facet parameters",
            data=params.model_dump(exclude_none=True)
        )

        api_url = ala_logic.build_occurrence_facets_url(params)
        await process.log(f"API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: ala_logic.execute_request(api_url)
                ),
                timeout=30.0
            )

            await process.log("Retrieved facet data")

            # Handle both dict and list response formats
            if isinstance(raw_response, dict):
                facet_results = raw_response.get("facetResults", [])
            elif isinstance(raw_response, list):
                facet_results = raw_response
            else:
                facet_results = []

            # Extract facet summary
            facet_fields = []
            total_values = 0

            for facet in facet_results:
                if isinstance(facet, dict):
                    field_name = facet.get("fieldName", "Unknown")
                    field_result = facet.get("fieldResult", [])
                    count = len(field_result)
                    facet_fields.append(f"{field_name} ({count} values)")
                    total_values += count

            await process.log(
                f"Facet summary: {len(facet_fields)} fields, {total_values} total values"
            )

            await process.create_artifact(
                mimetype="application/json",
                description=(
                    f"Occurrence breakdown - {total_values} values "
                    f"across {len(facet_fields)} fields"
                ),
                uris=[api_url],
                content=json.dumps(raw_response).encode("utf-8"),
                metadata={
                    "data_source": "ALA Occurrence Facets",
                    "facet_fields": len(facet_fields),
                    "total_facet_values": total_values,
                    "search_context": search_context.strip(),
                    "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )

            if facet_fields:
                summary = (
                    f"Found {total_values} values across "
                    f"{len(facet_fields)} categories: "
                    f"{', '.join(facet_fields[:3])}"
                )
                if len(facet_fields) > 3:
                    summary += f" and {len(facet_fields) - 3} more"
                summary += "."
            else:
                summary = (
                    "No facet data found - this may indicate "
                    "no matching records for this query."
                )

            await context.reply(summary)

        except asyncio.TimeoutError:
            await process.log("Facet API timed out after 30s")
            await context.reply(
                "Facet analysis timed out. "
                "Try a more specific query or add filters to reduce the dataset."
            )

        except ConnectionError as e:
            await process.log("API connection error", data={"error": str(e)})
            await context.reply(
                f"Could not connect to the ALA facet service: {e}"
            )

        except Exception as e:
            await process.log(f"Unexpected error: {type(e).__name__}: {e}")
            await context.reply(f"An unexpected error occurred during facet analysis: {e}")