from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from models.taxa_count import OccurrenceTaxaCountParams

logger = logging.getLogger(__name__)


async def run_taxa_count(context, ala_logic, params: OccurrenceTaxaCountParams) -> None:
    """
    Execute taxa count and stream results to context.

    Args:
        context:   iChatBio ResponseContext
        ala_logic: ALA HTTP layer
        params:    Typed API params from router (guids already newline-separated)
    """
    # Count GUIDs for process description
    guid_list = [g for g in params.guids.split("\n") if g.strip()]
    guid_count = len(guid_list)
    filter_description = f" with filter: {params.fq}" if params.fq else ""

    async with context.begin_process(
        f"Counting occurrences for {guid_count} taxa{filter_description}"
    ) as process:
        await process.log(
            "Taxa count parameters",
            data=params.model_dump(exclude_none=True)
        )
        await process.log(f"Resolving counts for {guid_count} taxa GUIDs")

        api_url = ala_logic.build_occurrence_taxa_count_url(params)
        await process.log(f"API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: ala_logic.execute_request(api_url)
                ),
                timeout=30.0
            )

            await process.log("Retrieved taxa count data")

            # Parse response: {guid: count, ...}
            total_occurrences = 0
            taxa_with_records = 0
            sample_results = []

            if isinstance(raw_response, dict):
                for guid, count in raw_response.items():
                    if isinstance(count, (int, float)) and count > 0:
                        taxa_with_records += 1
                        total_occurrences += int(count)
                        sample_results.append(f"{guid}: {count:,} records")

            await process.log(
                f"Taxa with records: {taxa_with_records}/{guid_count}, "
                f"total: {total_occurrences:,}"
            )

            await process.create_artifact(
                mimetype="application/json",
                description=(
                    f"Taxa occurrence counts — {taxa_with_records} of {guid_count} taxa, "
                    f"{total_occurrences:,} total occurrences"
                ),
                uris=[api_url],
                content=json.dumps(raw_response).encode("utf-8"),
                metadata={
                    "data_source": "ALA Occurrence Taxa Count",
                    "taxa_requested": guid_count,
                    "taxa_with_records": taxa_with_records,
                    "total_occurrences": total_occurrences,
                    "filter_applied": params.fq or "",
                    "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )

            if taxa_with_records > 0:
                summary = (
                    f"Found occurrence counts for {taxa_with_records} of {guid_count} taxa, "
                    f"totaling {total_occurrences:,} records"
                )
                if filter_description:
                    summary += filter_description
                summary += "."

                if sample_results and len(sample_results) <= 3:
                    summary += f" Results: {', '.join(sample_results)}."
                elif sample_results:
                    summary += (
                        f" Sample: {', '.join(sample_results[:2])} "
                        f"and {len(sample_results) - 2} more."
                    )
            else:
                summary = f"No occurrence records found for the {guid_count} taxa provided"
                if filter_description:
                    summary += filter_description
                summary += "."

            await context.reply(summary)

        except asyncio.TimeoutError:
            await process.log("Taxa count API timed out after 30s")
            await context.reply(
                "The taxa count request timed out. "
                "Try reducing the number of species or adding filters."
            )

        except ConnectionError as e:
            await process.log("API connection error", data={"error": str(e)})
            await context.reply(
                f"Could not connect to the ALA taxa count service: {e}"
            )