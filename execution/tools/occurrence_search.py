from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from models.occurrence import OccurrenceSearchParams

logger = logging.getLogger(__name__)


async def run_occurrence_search(context, ala_logic, params: OccurrenceSearchParams) -> None:
    """
    Execute occurrence search and stream results to context.

    Args:
        context:   iChatBio ResponseContext
        ala_logic: ALA HTTP layer
        params:    Typed API params from router
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
            returned = len(raw_response.get("occurrences", []))

            await process.log(f"Found {total:,} total records, returning {returned}")

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
                }
            )

            await context.reply(
                f"Found {total:,} occurrence records. "
                f"Returning {returned} in the artifact."
            )

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