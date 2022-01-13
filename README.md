# valclient.py

### API wrapper for VALORANT's client API

[![Discord](https://img.shields.io/badge/discord-join-7389D8?style=flat&logo=discord)](https://discord.gg/uGuswsZwAT)
[![Downloads](https://pepy.tech/badge/valclient)](https://pepy.tech/project/valclient)

## Installation
```python
pip install valclient
```

## Example

```python
from valclient.client import Client

client = Client(region="na")
client.activate()

# get MatchID of latest match
history = client.fetch_match_history(queue_id="unrated")
print(history["History"][0]["MatchID"])
```

## Notes
- don't use this to make anything that's obviously against TOS (i.e. automatic agent selecting program)
- just don't be dumb :)

## Docs

Check out [Techdoodle's extensive documentation](https://github.com/techchrism/valorant-api-docs/tree/trunk/docs). Most of the endpoints are implemented in this wrapper, but if you find another one/I'm missing one, [open an issue](https://github.com/colinhartigan/valclient.py/issues)!
