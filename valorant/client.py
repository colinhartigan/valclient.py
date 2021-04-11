# module imports
import requests
import os
import base64
import urllib3
import json

# imports for modules used in the package
from .resources import regions
from .resources import region_shard_override
from .resources import base_endpoint
from .resources import base_endpoint_glz
from .resources import base_endpoint_local

# disable urllib3 warnings that might arise from making requests to 127.0.0.1
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Client:

    def __init__(self, region="na"):
        self.lockfile_path = os.path.join(
            os.getenv('LOCALAPPDATA'), R'Riot Games\Riot Client\Config\lockfile')

        self.puuid = ""
        self.lockfile = {}
        self.headers = {}
        self.local_headers = {}
        self.region = region
        self.shard = region

        if region in regions:
            self.region = region
        else:
            raise ValueError(f"Invalid region, valid regions are: {regions}")

        if self.region in region_shard_override.keys():
            self.shard = region_shard_override[self.region]

        self.base_url, self.base_url_glz = self.__build_urls()

    def hook(self) -> None:
        '''Hook the client onto VALORANT'''
        try:
            self.lockfile = self.__get_lockfile()
            self.puuid, self.headers, self.local_headers = self.__get_headers()
        except:
            raise Exception("Unable to hook; is VALORANT running?")

    def fetch(self, endpoint="/", endpoint_type="pd") -> dict:
        '''Get data from a pd/glz/local endpoint'''
        if endpoint_type == "pd" or endpoint_type == "glz":
            response = requests.get(
                f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}', headers=self.headers)
            data = json.loads(response.text)

        elif endpoint_type == "local":
            response = requests.get("https://127.0.0.1:{port}{endpoint}".format(
                port=self.lockfile['port'], endpoint=endpoint), headers=self.local_headers, verify=False)
            data = response.json()

        if data is not None:
            if "httpStatus" in data:
                if data["httpStatus"] == 400:
                    # if headers expire (i dont think they ever do but jic), refresh em!
                    self.puuid, self.headers, self.local_headers = self.__get_headers()
                    return fetch(endpoint=endpoint, endpoint_type=endpoint_type)
            else:
                return data
        else:
            raise Exception("Request returned NoneType")

    def post(self, endpoint="/", endpoint_type="pd") -> dict:
        '''Post data to a pd/glz endpoint'''
        response = requests.post(
            f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}', headers=self.headers)
        data = json.loads(response.text)

        if data is not None:
            return data
        else:
            raise Exception("Request returned NoneType")

    # actual methods that people will use

    def fetch_presence(self, puuid=None) -> dict:
        '''
        Get the user's current VALORANT presence state data
        NOTE: Only works on self or active user's friends
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(endpoint="/chat/v4/presences", endpoint_type="local")
        for presence in data['presences']:
            if presence['puuid'] == puuid:
                return json.loads(base64.b64decode(presence['private']))

    def fetch_contracts(self) -> dict:
        '''
        Contracts_Fetch
        Get the active contracts for active user
        '''
        data = self.fetch(
            endpoint=f"/contracts/v1/contracts/{self.puuid}", endpoint_type="pd")
        return data

    def activate_contract(self, contract_id=None) -> dict:
        '''
        Contracts_Activate
        Activate a contract from an ID
        NOTE: Returns same information as fetch_contract_definitions()
        '''
        if contract_id is not None:
            data = self.post(
                endpoint=f"/contracts/v1/contracts/{self.puuid}/special/{contract_id}", endpoint_type="pd")
            return data

    def fetch_contract_definitions(self) -> dict:
        '''
        ContractDefinitions_Fetch
        Get the details about game contracts
        '''
        data = self.fetch(
            endpoint="/contract-definitions/v2/definitions", endpoint_type="pd")
        return data

    def fetch_active_story(self) -> dict:
        '''
        ContractDefinitions_FetchActiveStory
        Get details about the active battlepass
        '''
        data = self.fetch(
            endpoint="/contract-definitions/v2/definitions/story", endpoint_type="pd")
        return data

    def coregame_fetch_player(self) -> dict:
        '''
        CoreGame_FetchPlayer
        Get brief details about the uesr's active match
        NOTE: Will always return a 404 unless match is ACTIVE (not in pregame)
        '''
        data = self.fetch(
            endpoint=f"/core-game/v1/players/{self.puuid}", endpoint_type="glz")
        return data

    def coregame_fetch_match(self, match_id=None) -> dict:
        '''
        CoreGame_FetchMatch
        Get general match details
        '''
        if match_id is not None:
            data = self.fetch(
                endpoint=f"/core-game/v1/matches/{match_id}", endpoint_type="glz")
            return data
        else:
            raise ValueError("Expected a match id")

    def coregame_fetch_match_loadouts(self, match_id=None) -> dict:
        '''
        CoreGame_FetchMatchLoadouts
        Get all players' skin loadouts
        NOTE: I'm not sure if this actually works, might return a NoneType
        '''
        if match_id is not None:
            data = self.fetch(
                endpoint=f"/core-game/v1/matches/{match_id}/loadouts", endpoint_type="glz")
            return data
        else:
            raise ValueError("Expected a match id")

    def fetch_match_details(self, match_id=None) -> dict:
        '''
        MatchDetails_FetchMatchDetails
        Fetch full details from a match
        '''
        if match_id is not None:
            data = self.fetch(
                endpoint=f"/match-details/v1/matches/{match_id}", endpoint_type="pd")
            return data
        else:
            raise ValueError("Expected a match id")

    def fetch_match_history(self, puuid=None, start_index=0, end_index=15, queue_id="") -> dict:
        '''
        MatchHistory_FetchMatchHistory
        Fetch match history for a certain player
        Queues (leave blank for all): competitive, custom, deathmatch, ggteam (escalation), snowball, spikerush, unrated
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(endpoint=f"/match-history/v1/history/{puuid}?startIndex={start_index}&endIndex={end_index}" + (
            f"&queue={queue_id}" if queue_id != "" else ""), endpoint_type="pd")
        return data

    def fetch_mmr(self, puuid=None) -> dict:
        '''
        MMR_FetchPlayer
        Fetch a player's MMR data for all queues/seasons
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(
            endpoint=f"/mmr/v1/players/{puuid}", endpoint_type="pd")
        return data

    def fetch_competitive_updates(self, puuid=None, start_index=0, end_index=15, queue_id="") -> dict:
        '''
        MMR_FetchCompetitiveUpdates
        Fetch competitive updates match by match for a certain queue
        Queues (leave blank for all): competitive, custom, deathmatch, ggteam (escalation), snowball, spikerush, unrated
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(endpoint=f"/mmr/v1/players/{puuid}/competitiveupdates?startIndex={start_index}&endIndex={end_index}" + (
            f"&queue={queue_id}" if queue_id != "" else ""), endpoint_type="pd")
        return data

    def fetch_leaderboard(self, season_id=None) -> dict:
        '''
        MMR_FetchLeaderboard
        Fetch the leaderboard
        '''
        if season_id is None:
            data = self.fetch(
                endpoint=f"/mmr/v1/leaderboards/affinity/ap/queue/competitive/season/{season_id}", endpoint_type="pd")
            return data
        else:
            raise ValueError("Invalid season id")

    def fetch_player_loadout(self, puuid=None) -> dict:
        '''
        '''
        puuid = self.puuid if puuid is None else puuid

    # local utility functions

    def __build_urls(self) -> str:
        base_url = base_endpoint.format(shard=self.shard)
        base_url_glz = base_endpoint_glz.format(
            shard=self.shard, region=self.region)
        return base_url, base_url_glz

    def __get_headers(self) -> dict:
        '''Get authorization headers to make requests'''
        try:
            # headers for pd/glz endpoints
            local_headers = {}
            local_headers['Authorization'] = 'Basic ' + base64.b64encode(
                ('riot:' + self.lockfile['password']).encode()).decode()
            response = requests.get("https://127.0.0.1:{port}/entitlements/v1/token".format(
                port=self.lockfile['port']), headers=local_headers, verify=False)
            entitlements = response.json()
            puuid = entitlements['subject']
            headers = {
                'Authorization': f"Bearer {entitlements['accessToken']}",
                'X-Riot-Entitlements-JWT': entitlements['token'],
                'X-Riot-ClientPlatform': "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
                'X-Riot-ClientVersion': self.__get_current_version()
            }
            return puuid, headers, local_headers

        except Exception as e:
            print(e)
            raise Exception("Unable to get headers; is VALORANT running?")

    def __get_current_version(self) -> str:
        data = requests.get('https://valorant-api.com/v1/version')
        data = data.json()['data']
        version = f"{data['branch']}-shipping-{data['buildVersion']}-{data['version'].split('.')[3]}"
        return version

    def __get_lockfile(self) -> dict:
        try:
            with open(self.lockfile_path) as lockfile:
                data = lockfile.read().split(':')
                keys = ['name', 'PID', 'port', 'password', 'protocol']
                return dict(zip(keys, data))
        except:
            raise Exception("Lockfile not found")
