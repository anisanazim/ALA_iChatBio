# get_occurrence_breakdown

## Purpose
Get analytical breakdowns of occurrence data grouped by one or more categories.
The primary analytics tool — handles most counting and distribution questions.

## When to use
- User wants counts grouped by a category (state, year, month, species, family etc.)
- User wants to know top N species, institutions, or locations
- User wants seasonal or temporal distribution
- User wants to compare record counts across categories
- User wants database-wide statistics with no species specified
- User wants to drill down into a category

## When NOT to use
- User wants a single total count for a specific species → use get_occurrence_taxa_count
- User wants individual records → use search_species_occurrences
- User wants species profile or taxonomy → use lookup_species_info

## Returns
- Count per category value
- Total number of distinct values

## Examples
- "breakdown koala records by state"
- "which states have the most platypus records"
- "monthly distribution of koala sightings"
- "top 10 species recorded in Queensland"
- "how many species are in the ALA database"
- "compare koala records by year"
- "which institutions have the most wombat records"
- "seasonal trend of rainbow bee-eater sightings"