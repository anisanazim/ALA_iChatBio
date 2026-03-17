# ALA iChatBio Agent

Natural language interface for querying the [Atlas of Living Australia](https://www.ala.org.au/) (ALA) biodiversity database. Built on the iChatBio platform using a structured 5-stage AI pipeline.

**GitHub**: https://github.com/anisanazim/ALA_iChatBio

---

## Architecture

Queries are processed through a linear, deterministic pipeline:

```
User Query
    ↓
[PLANNER]    → intent, tools, species names, requires_lsid
    ↓
[EXTRACTOR]  → typed params (state, years, facets, species as written)
    ↓
[RESOLVER]   → LSID, scientific name, rank per species
    ↓
[ROUTER]     → typed API params ready for each tool
    ↓
[EXECUTOR]   → artifacts + replies streamed to user
```


This pipeline uses **Instructor + Pydantic** for typed, validated outputs at every stage with failure handling at each step

---

## Project Structure

```
ALA/
├── agent.py                        # Entry point - wires pipeline together
├── agent_server.py                 # iChatBio server startup
├── ala_logic.py                    # HTTP layer - URL builders + execute_request
│
├── planning/
│   ├── __init__.py
│   ├── models.py                   # PlannerOutput, ToolPlan, IntentType, QueryType
│   ├── planner.py                  # ALAPlanner - LLM intent classification
│   ├── registry.py                 # ToolCapabilityRegistry - loads .md files
│   └── capabilities/
│       ├── search_species_occurrences.md
│       ├── get_occurrence_breakdown.md
│       ├── get_occurrence_taxa_count.md
│       ├── lookup_species_info.md
│       └── get_species_distribution.md
│
├── extraction/
│   ├── __init__.py
│   ├── extractor.py                # ALAExtractor - per-intent LLM extraction
│   ├── models.py                   # ExtractionResult union type
│   └── schemas/
│       ├── base.py                 # ExtractionBase - shared clarification fields
│       ├── occurrence_search.py    # OccurrenceSearchExtraction
│       ├── facet_breakdown.py      # FacetBreakdownExtraction
│       ├── taxa_count.py           # TaxaCountExtraction
│       ├── taxonomy.py             # TaxonomyExtraction
│       └── distribution.py         # DistributionExtraction
│
├── resolution/
│   ├── __init__.py
│   ├── resolver.py                 # ALAParameterResolver - Redis-backed species resolution
│   └── models.py                   # ResolvedSpecies, ResolutionResult
│
├── routing/
│   ├── __init__.py
│   └── router.py                   # ALARouter - pure Python param conversion
│
├── execution/
│   ├── __init__.py
│   ├── executor.py                 # ALAExecutor - tool dispatch + phase execution
│   └── tools/
│       ├── occurrence_search.py    # run_occurrence_search
│       ├── facet_breakdown.py      # run_facet_breakdown
│       ├── taxa_count.py           # run_taxa_count
│       ├── taxonomy.py             # run_taxonomy
│       └── distribution.py         # run_distribution
│
├── models/                         # Pure API contract models
│   ├── occurrence.py               # OccurrenceSearchParams
│   ├── facets.py                   # OccurrenceFacetsParams
│   ├── taxa_count.py               # OccurrenceTaxaCountParams
│   ├── bie.py                      # SpeciesBieSearchParams
│   ├── distribution.py             # SpatialDistributionByLsidParams
│   └── name_matching.py            # NameMatchingSearchParams
│
├── common/
│    ├── config.py                   # get_config_value - env/yaml config loader
│    └── types.py                    # Shared type imports
│
└── docs/
    └── response_schemas/
        ├── occurrence_search.md
        ├── facet_breakdown.md
        ├── taxa_count.md
        ├── lookup_species_info.md
        └── distribution.md
```

---

## Supported Intents

| Intent | Tool | Endpoint | Needs LSID |
|--------|------|----------|------------|
| `occurrence_search` | search_species_occurrences | /occurrences/search | No |
| `facet_breakdown` | get_occurrence_breakdown | /occurrences/facets | No |
| `taxa_count` | get_occurrence_taxa_count | /occurrences/taxaCount | Yes |
| `taxonomy` | lookup_species_info | /species/search | No |
| `distribution` | get_species_distribution | /spatial-service/distribution/lsids | Yes |

---

## Failure Handling

| Stage | Failure | Handling |
|-------|---------|----------|
| Planner | Ambiguous query | Ask user for clarification |
| Planner | Out of scope | Decline gracefully |
| Extractor | Missing required param | Ask user for clarification |
| Extractor | LLM validation failure | Instructor retries (×2), then safe fallback |
| Resolver | Species not found | Ask user for scientific name |
| Router | No LSID for LSID-required tool | Raise with clear message |
| Executor | Must-call tool fails | Stop pipeline immediately |
| Executor | Optional tool fails | Log and continue |

---

## Setup

### Requirements
- Python 3.10+
- Redis running on localhost:6379
- OpenAI API key

### Install
```bash
pip install -r requirements.txt
npm install -g docx
```

### Configuration
Create `env.yaml` in the project root:
```yaml
OPENAI_API_KEY: your-key-here
OPENAI_BASE_URL: https://api.ai.it.ufl.edu
ALA_API_URL: https://api.ala.org.au
```

### Run
```bash
python agent_server.py
```
Server starts at `http://0.0.0.0:9999`

---

## Example Queries

```
# Occurrence search
Show me koala sightings in Queensland since 2020
Find platypus observations near Sydney with images only

# Facet breakdown
Break down koala records by state
What years have the most wombat sightings?
Break down rainbow bee-eater records by state, year and record type

# Taxa count
How many koala records are in ALA?
How many records exist for koala and wombat?

# Taxonomy
Tell me about the koala
What family does the platypus belong to?

# Distribution
Show me the distribution map for the koala
What is the geographic range of the platypus?
```

---

## Key Design Decisions

- **Per-intent extraction schemas** - each intent has its own Pydantic schema. Schema enforces relevance, not prompt instructions
- **Router as validation boundary** - no raw LLM output reaches the ALA API. Router converts typed extraction → typed API params with correct Solr syntax
- **Resolver is Redis-first** - scientific names, vernacular names, synonyms, and LSIDs are all cached. Negative cache prevents repeat failed lookups
- **Executor phases** - must-call tools stop the pipeline on failure; optional tools log and continue
- **ala_logic.py is HTTP only** - URL builders and execute_request.