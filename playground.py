from valorant.client import Client

client = Client(region="na")
client.hook()

while True:
    method = int(input("get or post? (1/2) "))
    endp = input("what endpoint? ")
    typ = input("what type? ")
    if method == 1:
        print(client.fetch(endp,typ))
    else:
        print(client.post(endp,typ))