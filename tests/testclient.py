from valclient.client import Client

client = Client(region="na")
client.hook()
print(client.fetch_active_story())