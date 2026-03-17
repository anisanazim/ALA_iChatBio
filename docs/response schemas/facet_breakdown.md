# Response Schema: get_occurrence_breakdown
**Tool:** get_occurrence_breakdown  
**Endpoint:** `GET /occurrences/occurrences/facets`  
**ALA Service:** Occurrence Facets

---

## Key Response Fields

### Top Level

| Field | Type | Description |
|-------|------|-------------|
| facetResults | array | One entry per requested facet field |

### Per Facet Entry

| Field | Type | Description |
|-------|------|-------------|
| fieldName | string | The facet field name (e.g. "state", "year") |
| count | int | Total number of distinct values for this facet |
| fieldResult | array | List of value + count pairs |

### Per fieldResult Item

| Field | Type | Description |
|-------|------|-------------|
| label | string | Human-readable value label |
| i18nCode | string | Internationalisation code |
| count | int | Number of occurrence records with this value |
| fq | string | Filter query string to apply this value |

---

## Supported Facet Fields

| Facet | Returns |
|-------|---------|
| state | Breakdown by Australian state/territory |
| year | Breakdown by year |
| month | Breakdown by month |
| basis_of_record | Breakdown by record type |
| species | Top species by record count |
| genus | Top genera by record count |
| family | Top families by record count |
| kingdom | Breakdown by kingdom |
| institution_code | Breakdown by institution |
| data_resource_uid | Breakdown by data provider |
| multimedia | Records with/without images |

---