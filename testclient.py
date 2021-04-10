from valorant.client import Client

client = Client(region="na")
client.hook()
print(client.coregame_fetch_match('61572b94-3729-4542-9be4-409c10256183'))