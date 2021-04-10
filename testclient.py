from valorant.client import Client

client = Client(region="na")
client.hook()
print(client.coregame_fetch_player())