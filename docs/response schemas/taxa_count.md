# Response Schema: get_occurrence_taxa_count
**Tool:** get_occurrence_taxa_count  
**Endpoint:** `GET /occurrences/occurrences/taxaCount`  
**ALA Service:** Occurrence Taxa Count

---

## Key Response Fields

The response is a flat dictionary mapping each LSID to its occurrence count.

| Field | Type | Description |
|-------|------|-------------|
| {lsid} | int | Total occurrence records for this taxon LSID |


## Note

For a simple total count of a single species with no filters, `lookup_species_info` returns `occurrenceCount` inline - no separate taxa count call needed. Use this tool when filters (state, year, basis_of_record) are required or when comparing multiple species counts.