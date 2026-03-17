# Response Schema: search_species_occurrences
**Tool:** search_species_occurrences  
**Endpoint:** `GET /occurrences/occurrences/search`  
**ALA Service:** Occurrence Search  
---

## Top Level

| Field | Type | Notes |
|-------|------|-------|
| totalRecords | int | Total matching records across all of ALA — not just the page returned |
| occurrences | array | Occurrence records for the current page |
| facetResults | array | Only present if facets were requested |

---

## Occurrence Record Fields

### Identity

| Field | Type | Notes |
|-------|------|-------|
| uuid | string | ALA's internal unique identifier for this occurrence record |
| occurrenceID | string | The original identifier assigned by the data provider — may differ from uuid |
| taxonConceptID | string | LSID for the matched taxon in ALA's taxonomy |
| speciesGuid | string | LSID at species rank — same as taxonConceptID when match is at species level |
| genusGuid | string | LSID at genus rank |

### Taxonomy

| Field | Type | Notes |
|-------|------|-------|
| scientificName | string | Matched scientific name from ALA taxonomy |
| raw_scientificName | string | Original name as submitted by the data provider — useful when ALA's matched name differs |
| vernacularName | string | Common name |
| taxonRank | string | Rank of the matched taxon (species, genus, family etc.) |
| taxonRankID | int | Numeric rank ID — 7000 = species |
| species | string | Species binomial — same as scientificName at species rank |
| kingdom / phylum / classs / order / family / genus | string | Full classification. Note: classs has triple-s — ALA workaround for Java/Solr reserved word conflict |
| speciesGroups | array | Broad groupings e.g. ["Animals", "Mammals"] — ALA-specific |

### Location

| Field | Type | Notes |
|-------|------|-------|
| decimalLatitude / decimalLongitude | float | WGS84 coordinates |
| stateProvince | string | Australian state or territory |
| latLong | string | Concatenated "-27.53148,153.282182" — convenience field |

### Event

| Field | Type | Notes |
|-------|------|-------|
| eventDate | long | Unix timestamp in milliseconds — convert with datetime.fromtimestamp(eventDate/1000) |
| year | int | Extracted year |
| month | string | Month as zero-padded string e.g. "02" — string not int |

### Record Provenance

| Field | Type | Notes |
|-------|------|-------|
| basisOfRecord | string | How the record was created. Values: HUMAN_OBSERVATION, PRESERVED_SPECIMEN, MACHINE_OBSERVATION, LIVING_SPECIMEN, FOSSIL_SPECIMEN, MATERIAL_SAMPLE |
| raw_basisOfRecord | string | Original basisOfRecord as submitted by provider e.g. "HumanObservation" — ALA normalises to UPPER_SNAKE_CASE in basisOfRecord |
| dataProviderName | string | Organisation that provided the data e.g. "Koala Action Group" |
| dataProviderUid | string | ALA internal ID for the data provider |
| dataResourceName | string | Specific dataset name e.g. "Koala Count" |
| dataResourceUid | string | ALA internal ID for the dataset |
| raw_institutionCode | string | Institution name as submitted by the provider — not standardised |
| recordedBy / collectors / collector | array | recordedBy. ALA duplicates observer names across all three fields 
| license | string | Creative Commons license string e.g. "CC-BY-NC 3.0 (Aus)" |

### Images

| Field | Type | Notes |
|-------|------|-------|
| image | string | UUID of the primary image |
| images | array | UUIDs of all images attached to this record |
| imageUrl | string | Full-resolution image via ALA image proxy |

### Conservation

| Field | Type | Notes |
|-------|------|-------|
| stateConservation | string | ALA-derived conservation status for the state where this record was collected e.g. "Endangered" |

### Data Quality

| Field | Type | Notes |
|-------|------|-------|
| assertions | array | ALA data quality flags. Common values: COORDINATE_ROUNDED (coordinates were rounded to protect locality), MISSING_TAXONRANK, COUNTRY_DERIVED_FROM_COORDINATES. Full list: https://github.com/AtlasOfLivingAustralia/ala-dataquality |

---