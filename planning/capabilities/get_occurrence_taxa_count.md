# get_occurrence_taxa_count

## Purpose
Get a single total occurrence record count for one or more specific species.
Use when the user wants a precise count, optionally filtered by location or time.

## When to use
- User asks "how many records" for a specific species
- User wants a count filtered by state and/or year
- User wants to compare total counts across multiple species
- User wants a precise number, not a breakdown

## When NOT to use
- User wants counts grouped by category → use get_occurrence_breakdown
- User wants individual records → use search_species_occurrences
- No species mentioned → use get_occurrence_breakdown instead

## Returns
- Total record count per species

## Examples
- "how many koala records are there"
- "how many platypus records in Queensland"
- "how many koala records since 2020"
- "compare total records for koala vs wombat"
- "how many Tasmanian Devil records between 2015 and 2020"