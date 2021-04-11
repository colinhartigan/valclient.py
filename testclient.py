from valorant.client import Client

client = Client(region="na")
client.hook()
print(client.set_party_accessibility("22800558-8fc5-40fd-8ca0-97179236cf77"))