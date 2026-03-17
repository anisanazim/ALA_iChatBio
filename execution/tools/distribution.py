from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from models.distribution import SpatialDistributionByLsidParams

logger = logging.getLogger(__name__)


async def run_distribution(
    context,
    ala_logic,
    params: SpatialDistributionByLsidParams,
    species_name: str = "Unknown species",
) -> None:
    """
    Execute species distribution lookup and stream results to context.

    The distribution API returns imageUrl directly in the response —
    no separate image fetch call needed.

    Args:
        context:      iChatBio ResponseContext
        ala_logic:    ALA HTTP layer
        params:       Typed API params from router (contains lsid)
        species_name: Display name for logging and replies
    """
    async with context.begin_process(
        f"Fetching expert distribution data for {species_name}"
    ) as process:
        await process.log(f"LSID: {params.lsid}")

        api_url = ala_logic.build_spatial_distribution_by_lsid_url(params.lsid)
        await process.log(f"API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: ala_logic.execute_request(api_url)
                ),
                timeout=30.0
            )

            # Empty response = no expert distribution maps available
            if not raw_response:
                await process.log(f"No distribution data available for {species_name}")
                await context.reply(
                    f"No expert distribution maps are available for **{species_name}** "
                    f"in the ALA spatial service. This means no expert-compiled range "
                    f"maps have been created yet — not that the species doesn't exist. "
                    f"Try searching occurrence records for observed sighting locations."
                )
                return

            await process.log("Retrieved distribution data")

            # Extract distribution areas and image URLs
            distribution_count = 0
            image_urls = []

            if isinstance(raw_response, list):
                distribution_count = len(raw_response)
                for dist in raw_response:
                    if isinstance(dist, dict):
                        image_url = dist.get("imageUrl")
                        if image_url:
                            area_name = dist.get("area_name", "Distribution area")
                            image_urls.append({"url": image_url, "name": area_name})

            await process.log(
                f"Distribution areas: {distribution_count}, "
                f"map images available: {len(image_urls)}"
            )

            await process.create_artifact(
                mimetype="application/json",
                description=(
                    f"Expert spatial distribution for {species_name} — "
                    f"{distribution_count} area(s)"
                ),
                uris=[api_url],
                content=json.dumps(raw_response).encode("utf-8"),
                metadata={
                    "species_name": species_name,
                    "lsid": params.lsid,
                    "data_type": "expert_spatial_distribution",
                    "data_source": "ALA Spatial Service",
                    "distribution_areas": distribution_count,
                    "image_urls": [img["url"] for img in image_urls],
                    "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )

            # Build reply
            summary = (
                f"Retrieved {distribution_count} expert distribution area(s) "
                f"for {species_name}. "
                f"This shows the geographic range where experts believe the "
                f"species occurs based on ecological knowledge.\n\n"
            )

            if image_urls:
                summary += f"**Distribution Maps ({len(image_urls)} available):**\n"
                for img in image_urls:
                    summary += f"• **{img['name']}**: {img['url']}\n"
            else:
                summary += "No distribution map images are available for this species."

            await context.reply(summary)

        except asyncio.TimeoutError:
            await process.log("Distribution API timed out after 30s")
            await context.reply(
                "The distribution service took too long to respond. "
                "Please try again later."
            )

        except ConnectionError as e:
            error_msg = str(e)
            await process.log("API connection error", data={"error": error_msg})

            # Empty/non-JSON response = no data, not a real connection error
            if "not JSON" in error_msg or "empty" in error_msg.lower():
                await context.reply(
                    f"No expert distribution maps are available for **{species_name}** "
                    f"in the ALA spatial service."
                )
            else:
                await context.reply(
                    f"Could not connect to the ALA distribution service: {error_msg}"
                )

        except Exception as e:
            await process.log(f"Unexpected error: {type(e).__name__}: {e}")
            await context.reply(
                f"An error occurred while fetching distribution data for "
                f"{species_name}: {e}"
            )