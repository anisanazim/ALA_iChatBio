from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from extraction.schemas.taxonomy import TaxonomyExtraction
from models.bie import SpeciesBieSearchParams

logger = logging.getLogger(__name__)

async def run_taxonomy(context, ala_logic, params: SpeciesBieSearchParams, extraction: TaxonomyExtraction) -> None:
    """
    Execute BIE species lookup and stream results to context.

    Args:
        context:    iChatBio ResponseContext
        ala_logic:  ALA HTTP layer
        params:     Typed API params from router
        extraction: Typed extraction result - used for include_image flag
    """
    async with context.begin_process(
        f"Looking up species information for '{params.q}'"
    ) as process:
        await process.log(
            "BIE search parameters",
            data=params.model_dump(exclude_none=True)
        )

        api_url = ala_logic.build_species_bie_search_url(params)
        await process.log(f"API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: ala_logic.execute_request(api_url)
                ),
                timeout=30.0
            )

            await process.log("Retrieved BIE data")

            # Extract results
            total_records = 0
            results_count = 0
            sample_results = []
            primary_image_url = None

            if isinstance(raw_response, dict):
                search_results = raw_response.get("searchResults", {})
                total_records = search_results.get("totalRecords", 0)
                results = search_results.get("results", [])
                results_count = len(results)

                # Extract primary image from first result
                if results and isinstance(results[0], dict):
                    primary_image_url = (
                        results[0].get("imageUrl") or results[0].get("image")
                    )

                for result in results[:3]:
                    if isinstance(result, dict):
                        name = result.get(
                            "name", result.get("scientificName", "Unknown")
                        )
                        common_name = result.get("commonNameSingle", "")
                        sample_results.append(
                            f"{name} ({common_name})" if common_name else name
                        )

            await process.log(
                f"Total records: {total_records}, returning: {results_count}"
            )

            await process.create_artifact(
                mimetype="application/json",
                description=(
                    f"BIE species information for '{params.q}' - "
                    f"{results_count} of {total_records} results"
                ),
                uris=[api_url],
                content=json.dumps(raw_response).encode("utf-8"),
                metadata={
                    "data_source": "ALA Biodiversity Information Explorer",
                    "search_query": params.q,
                    "filter_applied": params.fq,
                    "results_returned": results_count,
                    "total_records": total_records,
                    "primary_image_url": primary_image_url,
                    "retrieval_date": datetime.now().strftime("%Y-%m-%d"),
                }
            )

            if total_records > 0:
                summary = f"Found {total_records} results in the BIE"
                if results_count != total_records:
                    summary += f" (showing first {results_count})"
                if sample_results:
                    summary += f". Top results: {', '.join(sample_results)}"
                    if results_count > 3:
                        summary += f" and {results_count - 3} more"
                if extraction.include_image and primary_image_url:
                    summary += f"\n\nImage: {primary_image_url}"
                summary += "."
            else:
                summary = f"No species information found in the BIE for '{params.q}'."

            await context.reply(summary)

        except asyncio.TimeoutError:
            await process.log("BIE API timed out after 30s")
            await context.reply(
                "The species lookup timed out. Please try again."
            )

        except ConnectionError as e:
            await process.log("API connection error", data={"error": str(e)})
            await context.reply(
                f"Could not connect to the ALA BIE service: {e}"
            )