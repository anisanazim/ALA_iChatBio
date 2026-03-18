import asyncio
import requests
import cloudscraper
from urllib.parse import urlencode

from common.config import get_config_value
from models.bie import SpeciesBieSearchParams
from models.facets import OccurrenceFacetsParams
from models.name_matching import NameMatchingSearchParams
from models.occurrence import OccurrenceSearchParams
from models.taxa_count import OccurrenceTaxaCountParams


class ALA:
    """
    HTTP layer for the Atlas of Living Australia APIs.

    Single responsibility: build URLs and execute HTTP requests.

    Does NOT:
    - Extract parameters from natural language
    - Resolve species names
    - Convert user-friendly params to API params (that is the router's job)
    """

    def __init__(self):
        self.ala_api_base_url = get_config_value(
            "ALA_API_URL", "https://api.ala.org.au"
        )
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        })

    # -------------------------------------------------------------------------
    # Name matching (used by resolver)
    # -------------------------------------------------------------------------

    async def search_scientific_name(self, params: NameMatchingSearchParams) -> dict:
        """Search for a scientific name using the namematching API."""
        query_string = urlencode({"q": params.q})
        url = f"{self.ala_api_base_url}/namematching/api/search?{query_string}"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.execute_request(url))
    
    async def search_vernacular_name(self, params: NameMatchingSearchParams) -> dict:
        """Search for a vernacular/common name using the namematching API."""
        query_string = urlencode({"vernacularName": params.q})
        url = f"{self.ala_api_base_url}/namematching/api/searchByVernacularName?{query_string}"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.execute_request(url))

    # -------------------------------------------------------------------------
    # URL builders
    # -------------------------------------------------------------------------

    def build_occurrence_url(self, params: OccurrenceSearchParams) -> str:
        """Build URL for GET /occurrences/occurrences/search"""
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        query_string = urlencode(param_dict, doseq=True, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/occurrences/occurrences/search?{query_string}"

    def build_occurrence_facets_url(self, params: OccurrenceFacetsParams) -> str:
        """Build URL for GET /occurrences/occurrences/facets"""
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        query_string = urlencode(param_dict, doseq=True, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/occurrences/occurrences/facets?{query_string}"

    def build_occurrence_taxa_count_url(self, params: OccurrenceTaxaCountParams) -> str:
        """Build URL for GET /occurrences/occurrences/taxaCount"""
        api_params = {"guids": params.guids}

        if params.fq:
            api_params["fq"] = params.fq

        if params.separator != "\n":
            api_params["separator"] = params.separator

        query_string = urlencode(api_params, doseq=True, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/occurrences/occurrences/taxaCount?{query_string}"

    def build_species_bie_search_url(self, params: SpeciesBieSearchParams) -> str:
        """Build URL for GET /species/search"""
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        query_string = urlencode(param_dict, doseq=True, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/species/search?{query_string}"

    def build_spatial_distribution_by_lsid_url(self, lsid: str) -> str:
        """Build URL for GET /spatial-service/distribution/lsids/{lsid}"""
        encoded_lsid = requests.utils.quote(lsid, safe="")
        return f"{self.ala_api_base_url}/spatial-service/distribution/lsids/{encoded_lsid}"

    # -------------------------------------------------------------------------
    # HTTP execution
    # -------------------------------------------------------------------------

    def execute_request(self, url: str) -> dict:
        """Execute GET request and return JSON response."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            if not response.text or not response.text.strip():
                return {}

            try:
                return response.json()
            except ValueError:
                return {}

        except requests.exceptions.Timeout:
            raise ConnectionError(
                "API took too long to respond. "
                "Consider refining your request to reduce response time."
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API request failed: {e}")

    def execute_post_request(self, url: str, data: dict) -> dict:
        """Execute POST request with JSON data."""
        try:
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                raise ConnectionError(
                    f"API response was not JSON. "
                    f"Response: {response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"POST request failed: {e}")