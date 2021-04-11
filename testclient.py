from valorant.client import Client

client = Client(region="na")
client.hook()
print(client.fetch_contract_definitions())