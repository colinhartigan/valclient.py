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
from .resources import queues

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
                    return self.fetch(endpoint=endpoint, endpoint_type=endpoint_type)
            else:
                return data
        else:
            raise Exception("Request returned NoneType")

    def post(self, endpoint="/", endpoint_type="pd", json_data={}, params={}) -> dict:
        '''Post data to a pd/glz endpoint'''
        response = requests.post(
            f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}', headers=self.headers, json=json_data, params=params)
        data = json.loads(response.text)

        if data is not None:
            return data
        else:
            raise Exception("Request returned NoneType")



    # actual methods that people will use

    # local endpoints
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

    # contracts endpoints
    def fetch_contracts(self) -> dict:
        '''
        Contracts_Fetch
        Get the active contracts for active user
        '''
        data = self.fetch(
            endpoint=f"/contracts/v1/contracts/{self.puuid}", endpoint_type="pd")
        return data

    def activate_contract(self, contract_id) -> dict:
        '''
        Contracts_Activate
        Activate a contract from an ID
        NOTE: Returns same information as fetch_contract_definitions()
        '''
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

    # coregame endpoints
    def coregame_fetch_player(self) -> dict:
        '''
        CoreGame_FetchPlayer
        Get brief details about the uesr's active match
        NOTE: Will always return a 404 unless match is ACTIVE (not in pregame)
        '''
        data = self.fetch(
            endpoint=f"/core-game/v1/players/{self.puuid}", endpoint_type="glz")
        return data

    def coregame_fetch_match(self, match_id) -> dict:
        '''
        CoreGame_FetchMatch
        Get general match details
        '''
        data = self.fetch(
            endpoint=f"/core-game/v1/matches/{match_id}", endpoint_type="glz")
        return data

    def coregame_fetch_match_loadouts(self, match_id) -> dict:
        '''
        CoreGame_FetchMatchLoadouts
        Get all players' skin loadouts
        NOTE: I'm not sure if this actually works, might return a NoneType
        '''
        data = self.fetch(
            endpoint=f"/core-game/v1/matches/{match_id}/loadouts", endpoint_type="glz")
        return data

    # matches endpoints
    def fetch_match_details(self, match_id) -> dict:
        '''
        MatchDetails_FetchMatchDetails
        Fetch full details from a match
        '''
        data = self.fetch(
            endpoint=f"/match-details/v1/matches/{match_id}", endpoint_type="pd")
        return data

    def fetch_match_history(self, puuid=None, start_index=0, end_index=15, queue_id="") -> dict:
        '''
        MatchHistory_FetchMatchHistory
        Fetch match history for a certain player
        Queues (leave blank for all): competitive, custom, deathmatch, ggteam (escalation), snowball, spikerush, unrated
        '''
        self.__check_queue_type(queue_id)
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(endpoint=f"/match-history/v1/history/{puuid}?startIndex={start_index}&endIndex={end_index}" + (
            f"&queue={queue_id}" if queue_id != "" else ""), endpoint_type="pd")
        return data

    # MMR endpoints
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
        self.__check_queue_type(queue_id)
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(endpoint=f"/mmr/v1/players/{puuid}/competitiveupdates?startIndex={start_index}&endIndex={end_index}" + (
            f"&queue={queue_id}" if queue_id != "" else ""), endpoint_type="pd")
        return data

    def fetch_leaderboard(self, season_id) -> dict:
        '''
        MMR_FetchLeaderboard
        Fetch the leaderboard
        '''
        data = self.fetch(
            endpoint=f"/mmr/v1/leaderboards/affinity/ap/queue/competitive/season/{season_id}", endpoint_type="pd")
        return data

    # personalization endpoints
    def fetch_player_loadout(self, puuid=None) -> dict:
        '''
        playerLoadoutUpdate
        Fetch a player's skin/flair loadout
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.fetch(endpoint=f"/personalization/v2/players/{puuid}/playerloadout", endpoint_type="pd")
        return data

    # party endpoints
    def fetch_party_from_player(self, puuid=None) -> dict:
        '''
        Party_FetchPlayer
        Fetch data about a player's current party
        '''
        puuid = self.puuid if puuid is None else puuid 
        data = self.fetch(endpoint=f"/parties/v1/players/{puuid}", endpoint_type="glz")
        return data

    def fetch_party(self, party_id) -> dict:
        '''
        Party_FetchParty
        Fetch data about a party from a party uuid
        '''
        data = self.fetch(endpoint=f"/parties/v1/parties/{party_id}", endpoint_type="glz")
        return data

    def fetch_party_muc_token(self, party_id) -> dict:
        '''
        Party_FetchMUCToken
        Fetch MUC token for party
        '''
        data = self.fetch(endpoint=f"/parties/v1/parties/{party_id}", endpoint_type="glz")
        return data

    def fetch_party_custom_game_configs(self, party_id) -> dict:
        '''
        Party_FetchCustomGameConfigs
        Fetch information about active queues/maps/modes/servers
        '''
        data = self.fetch(endpoint=f"/parties/v1/parties/customgameconfigs", endpoint_type="glz")
        return data 

    def set_party_queue(self, party_id) -> dict:
        # TODO: this.
        '''
        Party_ChangeQueue
        '''
        pass

    def enter_matchmaking_queue(self, party_id) -> dict:
        '''
        Party_EnterMatchmakingQueue
        Join the matchmaking queue 
        '''
        data = self.post(endpoint=f"/parties/v1/parties/{party_id}/matchmaking/join", endpoint_type="glz")
        return data

    def refresh_competitive_tier(self, party_id, puuid=None) -> dict:
        '''
        Party_RefreshCompetitiveTier
        ???
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.post(endpoint=f"/parties/v1/parties/{party_id}/members/{puuid}/refreshCompetitiveTier", endpoint_type="glz")
        return data

    def refresh_player_identity(self, party_id, puuid=None) -> dict:
        '''
        Party_RefreshPlayerIdentity
        ???
        '''
        puuid = self.puuid if puuid is None else puuid
        data = self.post(endpoint=f"/parties/v1/parties/{party_id}/members/{puuid}/refreshPlayerIdentity", endpoint_type="glz")
        return data

    def set_party_accessibility(self, party_id) -> dict:
        # TODO: figure out how this damn thing works
        '''
        Party_SetAccessibility
        '''
        data = self.post(endpoint=f"/parties/v1/parties/{party_id}/accessibility", endpoint_type="glz", params={"Accessibility":"OPEN"})
        return data



    # local utility functions
    def __check_queue_type(self, queue_id) -> None:
        if not queue_id in queues:
            raise ValueError("Invalid queue type")

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