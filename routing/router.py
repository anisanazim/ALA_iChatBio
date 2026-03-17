from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from common.types import List
from extraction.models import ExtractionResult
from extraction.schemas.occurrence_search import OccurrenceSearchExtraction
from extraction.schemas.facet_breakdown import FacetBreakdownExtraction
from extraction.schemas.taxa_count import TaxaCountExtraction
from extraction.schemas.taxonomy import TaxonomyExtraction
from extraction.schemas.distribution import DistributionExtraction
from planning.models import PlannerOutput
from resolution.models import ResolutionResult, ResolvedSpecies

logger = logging.getLogger(__name__)

# Import API models
from models.occurrence import OccurrenceSearchParams
from models.facets import OccurrenceFacetsParams
from models.taxa_count import OccurrenceTaxaCountParams
from models.bie import SpeciesBieSearchParams
from models.distribution import SpatialDistributionByLsidParams


# ---------------------------------------------------------------------------
# Temporal helpers
# ---------------------------------------------------------------------------

def _current_year() -> int:
    return datetime.now().year


def _build_year_fq(
    year_exact: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    relative_years: Optional[int] = None,
) -> Optional[str]:
    """
    Convert typed year fields to Solr fq syntax.
    Returns a single fq string or None.
    """
    if relative_years:
        year_from = _current_year() - relative_years
        return f"year:[{year_from} TO *]"
    if year_exact:
        return f"year:{year_exact}"
    if year_from and year_to:
        return f"year:[{year_from} TO {year_to}]"
    if year_from:
        return f"year:[{year_from} TO *]"
    if year_to:
        return f"year:[* TO {year_to}]"
    return None


def _build_month_fq(months: Optional[List[int]]) -> Optional[str]:
    """Convert month list to Solr fq syntax."""
    if not months:
        return None
    if len(months) == 1:
        return f"month:{months[0]}"
    month_str = " OR ".join(str(m) for m in months)
    return f"month:({month_str})"


def _combine_fq(filters: List[Optional[str]]) -> List[str]:
    """Remove None values from fq filter list."""
    return [f for f in filters if f]


def _combine_fq_and(filters: List[Optional[str]]) -> Optional[str]:
    """
    Combine multiple fq filters with AND into a single string.
    Used for taxaCount which only accepts one fq param.
    """
    valid = [f for f in filters if f]
    if not valid:
        return None
    return " AND ".join(valid)


def _get_lsid(
    species_name: Optional[str],
    resolution: Optional[ResolutionResult],
) -> Optional[str]:
    """Get resolved LSID for a species name."""
    if not resolution or not species_name:
        return None
    for resolved in resolution.species:
        if resolved.original_name.lower() == species_name.lower():
            return resolved.lsid
    return None


def _get_resolved(
    species_name: Optional[str],
    resolution: Optional[ResolutionResult],
) -> Optional[ResolvedSpecies]:
    """Get full ResolvedSpecies for a species name."""
    if not resolution or not species_name:
        return None
    for resolved in resolution.species:
        if resolved.original_name.lower() == species_name.lower():
            return resolved
    return None


# ---------------------------------------------------------------------------
# Per-intent routing functions
# ---------------------------------------------------------------------------

def _route_occurrence_search(
    extraction: OccurrenceSearchExtraction,
    resolution: Optional[ResolutionResult],
) -> OccurrenceSearchParams:
    """Map OccurrenceSearchExtraction → OccurrenceSearchParams."""
    fq_filters = []

    # Species — use resolved scientific name if available, else raw name
    q = None
    if extraction.species:
        resolved = _get_resolved(extraction.species, resolution)
        q = resolved.scientific_name if resolved and resolved.scientific_name else extraction.species

    # State filter
    if extraction.state:
        fq_filters.append(f"state:{extraction.state}")

    # Temporal filters
    year_fq = _build_year_fq(
        year_exact=extraction.year_exact,
        year_from=extraction.year_from,
        year_to=extraction.year_to,
        relative_years=extraction.relative_years,
    )
    if year_fq:
        fq_filters.append(year_fq)

    # Month filter
    month_fq = _build_month_fq(extraction.months)
    if month_fq:
        fq_filters.append(month_fq)

    # Basis of record
    if extraction.basis_of_record:
        fq_filters.append(f"basis_of_record:{extraction.basis_of_record}")

    # Boolean filters
    if extraction.has_images:
        fq_filters.append("multimedia:Image")
    if extraction.has_coordinates:
        fq_filters.append("geospatial_kosher:true")

    # Taxonomic filters
    if extraction.kingdom:
        fq_filters.append(f"kingdom:{extraction.kingdom}")
    if extraction.family:
        fq_filters.append(f"family:{extraction.family}")
    if extraction.genus:
        fq_filters.append(f"genus:{extraction.genus}")

    combined_fq = _combine_fq(fq_filters)

    logger.warning(f"[ROUTER] occurrence_search → q={q}, fq={combined_fq}")

    return OccurrenceSearchParams(
        q=q,
        fq=combined_fq if combined_fq else None,
        lat=extraction.lat,
        lon=extraction.lon,
        radius=extraction.radius,
        pageSize=extraction.page_size or 20,
    )


def _route_facet_breakdown(
    extraction: FacetBreakdownExtraction,
    resolution: Optional[ResolutionResult],
) -> OccurrenceFacetsParams:
    """Map FacetBreakdownExtraction → OccurrenceFacetsParams."""
    fq_filters = []

    # Species
    q = None
    if extraction.species:
        resolved = _get_resolved(extraction.species, resolution)
        q = resolved.scientific_name if resolved and resolved.scientific_name else extraction.species

    # State filter
    if extraction.state:
        fq_filters.append(f"state:{extraction.state}")

    # Temporal filter
    year_fq = _build_year_fq(
        year_exact=extraction.year_exact,
        year_from=extraction.year_from,
        year_to=extraction.year_to,
        relative_years=extraction.relative_years,
    )
    if year_fq:
        fq_filters.append(year_fq)

    # Basis of record filter
    if extraction.basis_of_record:
        fq_filters.append(f"basis_of_record:{extraction.basis_of_record}")

    combined_fq = _combine_fq(fq_filters)

    logger.warning(f"[ROUTER] facet_breakdown → q={q}, facets={extraction.facets}, fq={combined_fq}")

    return OccurrenceFacetsParams(
        q=q,
        fq=combined_fq if combined_fq else None,
        facets=extraction.facets,
        fsort=extraction.fsort,
        flimit=extraction.flimit,
    )


def _route_taxa_count(
    extraction: TaxaCountExtraction,
    resolution: ResolutionResult,
) -> OccurrenceTaxaCountParams:
    """
    Map TaxaCountExtraction → OccurrenceTaxaCountParams.
    Requires resolution — LSIDs must be resolved before calling.
    Multiple fq filters combined with AND into single string.
    """
    # Build newline-separated LSIDs
    lsids = []
    for species_name in extraction.species:
        lsid = _get_lsid(species_name, resolution)
        if lsid:
            lsids.append(lsid)
        else:
            logger.warning(f"[ROUTER] No LSID found for '{species_name}' — skipping")

    if not lsids:
        raise ValueError(
            "No LSIDs resolved — cannot call taxaCount without at least one valid LSID."
        )

    guids = "\n".join(lsids)

    # Build single AND-combined fq string
    fq_filters = []

    if extraction.state:
        fq_filters.append(f"state:{extraction.state}")

    year_fq = _build_year_fq(
        year_exact=extraction.year_exact,
        year_from=extraction.year_from,
        year_to=extraction.year_to,
        relative_years=extraction.relative_years,
    )
    if year_fq:
        fq_filters.append(year_fq)

    fq = _combine_fq_and(fq_filters)

    logger.warning(f"[ROUTER] taxa_count → guids={lsids}, fq={fq}")

    return OccurrenceTaxaCountParams(
        guids=guids,
        fq=fq,
    )


def _route_taxonomy(
    extraction: TaxonomyExtraction,
) -> SpeciesBieSearchParams:
    """Map TaxonomyExtraction → SpeciesBieSearchParams."""
    logger.warning(f"[ROUTER] taxonomy → q={extraction.species}")

    return SpeciesBieSearchParams(
        q=extraction.species,
    )


def _route_distribution(
    extraction: DistributionExtraction,
    resolution: ResolutionResult,
) -> SpatialDistributionByLsidParams:
    """
    Map DistributionExtraction → SpatialDistributionByLsidParams.
    Requires resolution — LSID must be resolved before calling.
    """
    lsid = _get_lsid(extraction.species, resolution)

    if not lsid:
        raise ValueError(
            f"[ROUTER] Cannot route distribution — no LSID resolved for '{extraction.species}'"
        )

    logger.warning(f"[ROUTER] distribution → lsid={lsid}")

    return SpatialDistributionByLsidParams(lsid=lsid)


# ---------------------------------------------------------------------------
# PUBLIC: Main router entry point
# ---------------------------------------------------------------------------

class ALARouter:
    """
    Pure Python router. No LLM calls.

    Responsibility: map (PlannerOutput + ExtractionResult + ResolutionResult)
    → typed API params for each planned tool.

    Does not call APIs. Does not make decisions. Only maps.
    """

    def route(
        self,
        plan: PlannerOutput,
        extraction: ExtractionResult,
        resolution: Optional[ResolutionResult] = None,
    ) -> dict[str, object]:
        """
        Route extraction + resolution results to typed API params.

        Returns:
            Dict mapping tool_name → typed API params model
            e.g. {"search_species_occurrences": OccurrenceSearchParams(...)}
        """
        intent = plan.intent
        routed = {}

        logger.warning(f"[ROUTER] Routing intent: {intent}")

        if intent == "occurrence_search":
            routed["search_species_occurrences"] = _route_occurrence_search(
                extraction, resolution
            )

        elif intent == "facet_breakdown":
            routed["get_occurrence_breakdown"] = _route_facet_breakdown(
                extraction, resolution
            )

        elif intent == "taxa_count":
            routed["get_occurrence_taxa_count"] = _route_taxa_count(
                extraction, resolution
            )

        elif intent == "taxonomy":
            routed["lookup_species_info"] = _route_taxonomy(extraction)

        elif intent == "distribution":
            routed["get_species_distribution"] = _route_distribution(
                extraction, resolution
            )

        else:
            logger.warning(f"[ROUTER] No routing defined for intent: {intent}")

        return routed