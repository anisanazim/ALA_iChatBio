# Response Schema: lookup_species_info
**Tool:** lookup_species_info  
**Endpoint:** `GET /species/search`  
**ALA Service:** Biodiversity Information Explorer (BIE)

---

## Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| guid | string | LSID / taxon concept ID |
| scientificName | string | Full scientific name |
| nameComplete | string | Scientific name with authorship |
| commonNameSingle | string | Primary common name |
| rank | string | Taxonomic rank (species, genus, family etc.) |
| kingdom | string | Kingdom classification |
| phylum | string | Phylum classification |
| class_s | string | Class classification |
| order_s | string | Order classification |
| family_s | string | Family classification |
| genus_s | string | Genus classification |
| image | string | Representative species image URL |
| imageUrl | string | Direct image URL (PNG/JPG) |
| occurrenceCount | int | Total ALA occurrence records for this taxon |
| conservationStatusAUS_s | string | Australian federal conservation status |
| conservationStatusQLD_s | string | Queensland state conservation status |
| conservationStatusNSW_s | string | New South Wales conservation status |
| conservationStatusVIC_s | string | Victoria conservation status |
| conservationStatusWA_s | string | Western Australia conservation status |
| conservationStatusTAS_s | string | Tasmania conservation status |
| conservationStatusSA_s | string | South Australia conservation status |
| conservationStatusNT_s | string | Northern Territory conservation status |
| conservationStatusACT_s | string | ACT conservation status |
| isThreatened_s | string | Threatened species flag |
| isInvasive_s | string | Invasive species flag |
| establishmentMeans | string | Native / introduced / vagrant |
| vernacularName_s | string | Additional vernacular names |
---