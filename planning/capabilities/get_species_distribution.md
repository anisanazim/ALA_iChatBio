# get_species_distribution

## Purpose
Get the expert geographic distribution range for a species including
area size, map image, and polygon geometry.

## When to use
- User wants to know where a species lives or its geographic range
- User wants a distribution map
- User wants to know the size of a species habitat
- User wants to know if a species is endemic
- User wants an expert-drawn range map

## When NOT to use
- User wants individual occurrence records with coordinates → use search_species_occurrences
- User wants counts by state → use get_occurrence_breakdown

## Returns
- Expert range polygon
- Range size in square kilometres
- Ready-made distribution map image
- Endemic status

## Examples
- "where does the Tasmanian Devil live"
- "show me the koala's distribution"
- "how large is the platypus habitat"
- "is the quokka endemic to Australia"
- "show me a distribution map for the wombat"