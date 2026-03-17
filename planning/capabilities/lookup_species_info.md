# lookup_species_info

## Purpose
Look up taxonomy, profile, and identity information about a species.
The knowledge tool — answers "what is this species" not "where is it found."

## When to use
- User wants to know about a species (description, classification, names)
- User asks "what is" or "tell me about" a species
- User provides an indigenous or vernacular name and wants identification
- User wants full taxonomic classification
- User asks for an image, picture, or photo of a species
- User asks "what does X look like"
- User asks "show me X"
- LSID discovery fallback when resolver fails



## When NOT to use
- User wants occurrence records → use search_species_occurrences
- User wants record counts → use get_occurrence_taxa_count
- User wants geographic range → use get_species_distribution

## Returns
- Full taxonomy with classification at every rank
- Scientific name with authorship
- Common names including indigenous names
- Occurrence count inline
- Representative species image
- Conservation status (Australian federal + state level)
- Threatened species flag
- Iconic species flag

## Examples
- "tell me about the koala"
- "what is Phascolarctos cinereus"
- "what is Guba" (indigenous name)
- "describe the platypus"
- "what family does the wombat belong to"
- "is the Tasmanian Tiger extinct"