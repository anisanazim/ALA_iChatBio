# search_species_occurrences

## Purpose
Find individual occurrence records from the ALA database with coordinates,
dates, collectors, images, and data quality information.

## When to use
- User wants to see individual sighting or observation records
- User wants to find, show, list, or browse occurrences
- User wants records with photos or images attached
- User wants records from a specific institution or collector
- User wants records filtered by basis of record (e.g. preserved specimens)
- User wants photographs or images from observations of a species or taxonomic group
- User asks about a broad taxonomic group (birds, mammals, reptiles, frogs) with no specific species

## When NOT to use
- User wants a count or total number → use get_occurrence_taxa_count
- User wants a breakdown or distribution by category → use get_occurrence_breakdown
- User wants to know about a species (taxonomy, description) → use lookup_species_info
- User wants geographic range or expert distribution → use get_species_distribution

## Returns
- Individual occurrence records with coordinates, dates, collectors
- Species images inline when available
- Data quality flags
- Institution and data source attribution
- imageUrl, largeImageUrl, smallImageUrl — observation photo URLs when record has images
- kingdom, family, genus fields for taxonomic filtering

## Examples
- "show me koala sightings in Queensland"
- "find platypus observations after 2020"
- "list wombat records from the Australian Museum"
- "show me preserved specimens of Tasmanian Devil"
- "find koala sightings with photos"
- "show me photographs of birds in New South Wales"
- "find images of mammals in Queensland"
- "show me reptile records with photos in Victoria"