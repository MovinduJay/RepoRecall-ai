# Retrieval evaluation datasets

Store curated JSON datasets here. Each case must contain a real historical bug query and
one or more GitHub records that are verified fixes. Do not infer relevance from retrieval
results, because that would make the evaluation circular.

```json
{
  "version": 1,
  "repository": "owner/repository",
  "cases": [
    {
      "case_id": "stable-human-readable-id",
      "query": "Issue title and body used as the search query",
      "relevant_evidence": [
        {"source_type": "pull_request", "source_id": "184"},
        {"source_type": "commit", "source_id": "full-commit-sha"}
      ],
      "notes": "How the issue-to-fix relationship was verified"
    }
  ]
}
```

Run all retrieval strategies and save the detailed report:

```bash
python -m app.scripts.evaluate_retrieval REPOSITORY_UUID evaluation_data/dataset.json \
  --k 10 --output evaluation_data/results.json
```
