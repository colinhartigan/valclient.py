import requests
import re

class Auth:

    def __init__(self,auth):
        self.username = auth['username']
        self.password = auth['password']

    def authenticate(self):
        session = requests.session()
        data = {
            'client_id': 'play-valorant-web-prod',
            'nonce': '1',
            'redirect_uri': 'https://playvalorant.com/opt_in',
            'response_type': 'token id_token',
        }
        r = session.post('https://auth.riotgames.com/api/v1/authorization', json=data)

        # print(r.text)
        data = {
            'type': 'auth',
            'username': self.username,
            'password': self.password
        }
        r = session.put('https://auth.riotgames.com/api/v1/authorization', json=data)
        pattern = re.compile('access_token=((?:[a-zA-Z]|\d|\.|-|_)*).*id_token=((?:[a-zA-Z]|\d|\.|-|_)*).*expires_in=(\d*)')
        data = pattern.findall(r.json()['response']['parameters']['uri'])[0] 
        access_token = data[0]
        # print('Access Token: ' + access_token)

        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        r = session.post('https://entitlements.auth.riotgames.com/api/token/v1', headers=headers, json={})
        entitlements_token = r.json()['entitlements_token']
        # print('Entitlements Token: ' + entitlements_token)

        r = session.post('https://auth.riotgames.com/userinfo', headers=headers, json={})
        user_id = r.json()['sub']
        # print('User ID: ' + user_id)
        headers['X-Riot-Entitlements-JWT'] = entitlements_token
        session.close()
        return user_id, headers, {}