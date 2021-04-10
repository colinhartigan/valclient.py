from valorant.client import Client

client = Client(region="na")
client.hook()

while True:
    endp = input("what endpoint? ")
    typ = input("what type? ")
    print(client.fetch(endp,typ))