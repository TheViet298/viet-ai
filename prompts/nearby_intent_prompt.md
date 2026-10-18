---
owner: VinFast ServiceFlow AI Team
version: v1.0
variables: [user_query, conversation_context]
contract: Return structured schema with find_nearby and category; never invent locations
eval_cases: tests/test_agents/test_prompt_artifacts.py
rollback: git revert or disable nearby intent node
---
Classify whether the current user is asking to find a physical VinFast location.
Use conversation meaning, not just the word charging. Charging instructions, pricing,
definitions, technical diagnosis and negated search requests are not nearby searches.
Supported categories: CHARGING_STATION, SHOWROOM, SERVICE_WORKSHOP, OTHER, ALL.
ALL means the location category needs clarification. Restaurants/hotels are unsupported.
Return only the requested structured schema. Never invent locations, coordinates,
distances, availability or navigation links. If uncertain, find_nearby=false.
