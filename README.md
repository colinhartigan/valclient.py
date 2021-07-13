# valclient.py

### API wrapper for VALORANT's client API

## Example

```python
from valclient.client import Client

client = Client(region="na")
client.activate()

# get MatchID of latest match
history = client.fetch_match_history(queue_id="unrated")
print(history["History"][0]["MatchID"])
```

## Docs

Check out [Techdoodle's awesome documentation](https://github.com/techchrism/valorant-api-docs/tree/trunk/docs)
