# extraction/models.py
from typing import Union
from extraction.schemas.occurrence_search import OccurrenceSearchExtraction
from extraction.schemas.facet_breakdown import FacetBreakdownExtraction
from extraction.schemas.taxa_count import TaxaCountExtraction
from extraction.schemas.taxonomy import TaxonomyExtraction
from extraction.schemas.distribution import DistributionExtraction

ExtractionResult = Union[
    OccurrenceSearchExtraction,
    FacetBreakdownExtraction,
    TaxaCountExtraction,
    TaxonomyExtraction,
    DistributionExtraction,
]