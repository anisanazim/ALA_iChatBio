# Response Schema: get_species_distribution
**Tool:** get_species_distribution  
**Endpoint:** `GET /spatial-service/distribution/lsids/{lsid}`  
**ALA Service:** Spatial Service

---

## Key Response Fields

The response is a list — one entry per expert distribution area.

### Per Distribution Area

| Field | Type | Description |
|-------|------|-------------|
| geom_idx | int | Unique geometry index — used as image ID |
| lsid | string | LSID for the taxon |
| scientific_name | string | Scientific name |
| common_name | string | Common name |
| area_name | string | Name of the distribution area |
| area_km | float | Area of the distribution in km² |
| imageUrl | string | Direct PNG map image URL — ready to display |
| wmsurl | string | WMS URL for interactive map layers |
| endemic | boolean | True if endemic to this area |
| data_resource_uid | string | Data resource identifier |
| metadata_u | string | Metadata URL |
| geom | string | WKT geometry (MULTIPOLYGON) |

---

## Note

`imageUrl` is a ready-made PNG map — return this directly to the user. No separate image fetch call is needed. This is expert-compiled range data based on ecological knowledge, not individual sighting records. For actual observed locations use `search_species_occurrences` instead.