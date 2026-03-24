from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from extraction.schemas.occurrence_search import OccurrenceSearchExtraction
from models.occurrence import OccurrenceSearchParams

logger = logging.getLogger(__name__)


async def run_occurrence_search(context, ala_logic, params: OccurrenceSearchParams, extraction: OccurrenceSearchExtraction) -> None:
    """
    Execute occurrence search and stream results to context.

    Args:
        context:    iChatBio ResponseContext
        ala_logic:  ALA HTTP layer
        params:     Typed API params from router
        extraction: Typed extraction result - used for image_count flag
    """
    async with context.begin_process("Searching for ALA occurrences") as process:
        await process.log(
            "Search parameters",
            data=params.model_dump(exclude_none=True)
        )

        api_url = ala_logic.build_occurrence_url(params)
        await process.log(f"API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: ala_logic.execute_request(api_url)
                ),
                timeout=30.0
            )

            total = raw_response.get("totalRecords", 0)
            occurrences = raw_response.get("occurrences", [])
            returned = len(occurrences)

            await process.log(f"Found {total:,} total records, returning {returned}")

            # Extract image URLs if user requested images
            image_urls = []
            if extraction.has_images or extraction.image_count:
                for occ in occurrences:
                    image_url = occ.get("largeImageUrl") or occ.get("imageUrl")
                    if image_url:
                        image_urls.append({
                            "url": image_url,
                            "scientificName": occ.get("scientificName"),
                            "vernacularName": occ.get("vernacularName"),
                            "stateProvince": occ.get("stateProvince"),
                            "eventDate": occ.get("eventDate"),
                            "recordedBy": occ.get("recordedBy"),
                        })
                    limit = extraction.image_count or 3
                    if len(image_urls) >= limit:
                        break

            await process.create_artifact(
                mimetype="application/json",
                description=f"ALA occurrence records - {returned} of {total:,} total",
                uris=[api_url],
                content=json.dumps(raw_response).encode("utf-8"),
                metadata={
                    "record_count": returned,
                    "total_matches": total,
                    "search_params": params.model_dump(exclude_none=True),
                    "data_source": "Atlas of Living Australia",
                    "retrieval_date": datetime.now().strftime("%Y-%m-%d"),
                    "image_count": len(image_urls),
                }
            )

            # Create individual image artifacts
            for img in image_urls:
                label = img.get("vernacularName") or img.get("scientificName") or "Species"
                state = img.get("stateProvince", "")
                await process.create_artifact(
                    mimetype="image/jpeg",
                    description=f"{label}{' - ' + state if state else ''}",
                    uris=[img["url"]],
                )

            summary = f"Found {total:,} occurrence records. Returning {returned} in the artifact."
            if image_urls:
                summary += f" Showing {len(image_urls)} image{'s' if len(image_urls) > 1 else ''}."

            await context.reply(summary)

        except asyncio.TimeoutError:
            await process.log("Request timed out after 30s")
            await context.reply(
                "The occurrence search timed out. "
                "Try narrowing your search (add a state or year filter)."
            )

        except ConnectionError as e:
            await process.log("API connection error", data={"error": str(e)})
            await context.reply(
                f"Could not connect to the ALA occurrence service: {e}"
            )