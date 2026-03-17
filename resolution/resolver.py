from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from ala_logic import NameMatchingSearchParams

from resolution.models import ResolvedSpecies, ResolutionResult

logger = logging.getLogger(__name__)

VALID_LSID_PREFIXES = [
    "https://biodiversity.org.au/afd/taxa/",
    "https://id.biodiversity.org.au/",
    "https://www.catalogueoflife.org/data/taxon/",
]


class ALAParameterResolver:
    """
    Redis-backed species resolver for ALA.

    Responsibilities:
    - Resolve species name → LSID + metadata
    - Use Redis as species knowledge base
    - Avoid unnecessary ALA API calls by checking Redis first

    Does NOT:
    - Mutate extraction params (that is the router's job)
    - Pick species identifiers from dicts (planner does that now)
    """

    def __init__(self, ala_logic, redis_client):
        self.ala_logic = ala_logic
        self.redis = redis_client

    # -------------------------------------------------------------------------
    # Redis helpers
    # -------------------------------------------------------------------------

    async def _redis_get(self, key: str) -> Optional[Dict[str, Any]]:
        raw = await self.redis.get(key)
        if not raw:
            logger.warning(f"Cache MISS: {key}")
            return None
        logger.warning(f"Cache HIT: {key}")
        return json.loads(raw)

    async def _redis_set(self, key: str, value: Dict[str, Any]):
        logger.warning(f"Storing in cache: {key}")
        await self.redis.set(key, json.dumps(value))

    # -------------------------------------------------------------------------
    # Key helpers
    # -------------------------------------------------------------------------

    def _key_scientific(self, name: str) -> str:
        return f"scientific:{name.lower()}"

    def _key_vernacular(self, name: str) -> str:
        return f"vernacular:{name.lower()}"

    def _key_synonym(self, name: str) -> str:
        return f"synonym:{name.lower()}"

    def _key_lsid(self, lsid: str) -> str:
        return f"lsid:{lsid}"

    def _key_no_match(self, name: str) -> str:
        return f"noMatch:{name.lower()}"

    # -------------------------------------------------------------------------
    # LSID detection
    # -------------------------------------------------------------------------

    def _is_lsid(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        return any(value.startswith(p) for p in VALID_LSID_PREFIXES)

    # -------------------------------------------------------------------------
    # Store full ALA response under multiple Redis keys
    # -------------------------------------------------------------------------

    async def _store_full_response(self, original_name: str, data: Dict[str, Any]):
        logger.warning(f"Storing full ALA response for: {original_name}")
        await self._redis_set(self._key_scientific(original_name), data)

        sci_name   = data.get("scientificName")
        vernacular = data.get("vernacularName")
        lsid       = data.get("taxonConceptID")

        if sci_name:
            await self._redis_set(self._key_scientific(sci_name), data)
        if vernacular:
            await self._redis_set(self._key_vernacular(vernacular), data)
        if data.get("synonymType") and original_name.lower() != (sci_name or "").lower():
            await self._redis_set(self._key_synonym(original_name), data)
        if lsid:
            await self._redis_set(self._key_lsid(lsid), data)

    # -------------------------------------------------------------------------
    # Redis-only resolution (no external API calls)
    # -------------------------------------------------------------------------

    async def _resolve_via_redis_only(self, name: str) -> Optional[Dict[str, Any]]:
        if self._is_lsid(name):
            cached = await self._redis_get(self._key_lsid(name))
            if cached:
                return cached

        for key in [
            self._key_scientific(name),
            self._key_vernacular(name),
            self._key_synonym(name),
        ]:
            cached = await self._redis_get(key)
            if cached:
                return cached

        # Negative cache
        no_match = await self._redis_get(self._key_no_match(name))
        if no_match:
            return None

        return None

    # -------------------------------------------------------------------------
    # Validation helpers
    # -------------------------------------------------------------------------

    def _is_valid_vernacular(self, d: Optional[Dict]) -> bool:
        if not d or not d.get("success"):
            return False
        if d.get("issues") == ["noMatch"]:
            return False
        return (
            d.get("matchType") == "vernacularMatch"
            and d.get("nameType") in ["INFORMAL", "COMMON"]
        )

    def _is_valid_scientific(self, d: Optional[Dict]) -> bool:
        if not d or not d.get("success"):
            return False
        if d.get("issues") == ["noMatch"]:
            return False
        if d.get("nameType") not in ["SCIENTIFIC", "DOUBTFUL"]:
            return False
        return d.get("matchType") in [
            "exactMatch",
            "phraseMatch",
            "taxonIdMatch",
            "higherMatch",
        ]

    # -------------------------------------------------------------------------
    # Core resolution — single species name → raw ALA record
    # -------------------------------------------------------------------------

    async def resolve_species_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a species name to a full ALA record.
        Redis first, then ALA scientific + vernacular APIs.
        """
        cached = await self._resolve_via_redis_only(name)
        if cached:
            logger.warning(f"CACHE HIT: Resolved '{name}' from Redis")
            return cached

        # LSID passthrough — not in cache, return minimal record
        if self._is_lsid(name):
            logger.warning(f"LSID not cached, returning minimal record: {name}")
            return {
                "scientificName": None,
                "taxonConceptID": name,
                "rank": None,
                "vernacularName": None,
                "issues": ["noIssue"],
            }

        # Call both ALA endpoints
        logger.warning(f"CACHE MISS: Calling ALA APIs for '{name}'")

        sci_params  = NameMatchingSearchParams(q=name)
        vern_params = NameMatchingSearchParams(q=name)

        sci_data, vern_data = await asyncio.gather(
            self.ala_logic.search_scientific_name(sci_params),
            self.ala_logic.search_vernacular_name(vern_params),
        )

        # Prefer vernacular (stricter, safer)
        if self._is_valid_vernacular(vern_data):
            logger.warning(f"ALA SUCCESS: Vernacular match for '{name}'")
            await self._store_full_response(name, vern_data)
            return vern_data

        if self._is_valid_scientific(sci_data):
            logger.warning(f"ALA SUCCESS: Scientific match for '{name}'")
            await self._store_full_response(name, sci_data)
            return sci_data

        # No valid match — negative cache
        logger.warning(f"NO MATCH: '{name}' not found — caching negative result")
        await self._redis_set(self._key_no_match(name), {"noMatch": True})
        return None

    # -------------------------------------------------------------------------
    # PUBLIC: Resolve a single species → ResolvedSpecies
    # -------------------------------------------------------------------------

    async def resolve_one(self, name: str) -> ResolvedSpecies:
        record = await self.resolve_species_name(name)

        if not record:
            return ResolvedSpecies(
                original_name=name,
                resolved=False,
                clarification_needed=True,
                clarification_question=(
                    f"I couldn't identify '{name}'. "
                    "Please provide the scientific name or a clearer common name."
                ),
            )

        # Warn if resolved at genus level — taxaCount will count entire genus
        rank = record.get("rank")
        if rank and rank.lower() == "genus":
            logger.warning(
                f"[RESOLVER] '{name}' resolved to genus '{record.get('scientificName')}' "
                f"— taxa count will include all species in this genus"
            )

        return ResolvedSpecies(
            original_name=name,
            lsid=record.get("taxonConceptID"),
            scientific_name=record.get("scientificName"),
            vernacular_name=record.get("vernacularName"),
            rank=rank,
            kingdom=record.get("kingdom"),
            family=record.get("family"),
            genus=record.get("genus"),
            resolved=True,
        )

    # -------------------------------------------------------------------------
    # PUBLIC: Resolve all species in parallel → ResolutionResult
    # -------------------------------------------------------------------------

    async def resolve_all(self, species_names: list[str]) -> ResolutionResult:
        """
        Resolve all species names in parallel.
        Called by the agent when PlannerOutput.requires_lsid=True.
        """
        if not species_names:
            return ResolutionResult()

        results = await asyncio.gather(
            *[self.resolve_one(name) for name in species_names]
        )

        unresolved = [r for r in results if not r.resolved]
        clarification_needed = len(unresolved) > 0

        clarification_question = None
        if clarification_needed:
            names = ", ".join(f"'{r.original_name}'" for r in unresolved)
            clarification_question = (
                f"I couldn't identify the following species: {names}. "
                "Please provide scientific names or clearer common names."
            )

        return ResolutionResult(
            species=list(results),
            clarification_needed=clarification_needed,
            clarification_question=clarification_question,
        )