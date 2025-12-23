curl -X POST http://localhost:8000/run_research \
  -H "Content-Type: application/json" \
  -d '{"query": "remote work impact", "top_k_sources": 3}' | jq .
