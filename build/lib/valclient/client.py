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

    def post(self, endpoint="/", endpoint_type="pd", json_data={}) -> dict:
        '''Post data to a pd/glz endpoint'''
        response = requests.post(
            f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}', headers=self.headers, json=json_data)
        data = json.loads(response.text)

        if data is not None:
            return data
        else:
            raise Exception("Request returned NoneType")

    # --------------------------------------------------------------------------------------------------

    # local endpoints
    def fetch_presence(self, puuid=None) -> dict:
        '''
        Get the user's current VALORANT presence state data
        NOTE: Only works on self or active user's friends
        '''
        puuid = self.__check_puuid(puuid)
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
        puuid = self.__check_puuid(puuid)
        data = self.fetch(endpoint=f"/match-history/v1/history/{puuid}?startIndex={start_index}&endIndex={end_index}" + (
            f"&queue={queue_id}" if queue_id != "" else ""), endpoint_type="pd")
        return data

    # MMR endpoints
    def fetch_mmr(self, puuid=None) -> dict:
        '''
        MMR_FetchPlayer
        Fetch a player's MMR data for all queues/seasons
        '''
        puuid = self.__check_puuid(puuid)
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
        puuid = self.__check_puuid(puuid)
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
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/personalization/v2/players/{puuid}/playerloadout", endpoint_type="pd")
        return data

    # party endpoints
    def fetch_party_from_puuid(self, puuid=None) -> dict:
        '''
        Party_FetchPlayer
        Fetch data about a player's current party
        '''
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/parties/v1/players/{puuid}", endpoint_type="glz")
        return data

    def fetch_party_from_partyid(self, party_id=None) -> dict:
        '''
        Party_FetchParty
        Fetch data about a party from a party uuid
        '''
        party_id = self.__check_party_id(party_id)
        data = self.fetch(
            endpoint=f"/parties/v1/parties/{party_id}", endpoint_type="glz")
        return data

    def fetch_party_custom_game_configs(self, party_id=None) -> dict:
        '''
        Party_FetchCustomGameConfigs
        Fetch information about active queues/maps/modes/servers
        '''
        party_id = self.__check_party_id(party_id)
        data = self.fetch(
            endpoint=f"/parties/v1/parties/customgameconfigs", endpoint_type="glz")
        return data

    def enter_matchmaking_queue(self, party_id=None) -> dict:
        '''
        Party_EnterMatchmakingQueue
        Join the matchmaking queue 
        '''
        party_id = self.__check_party_id(party_id)
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/matchmaking/join", endpoint_type="glz")
        return data

    def set_party_accessibility(self, party_id=None, state="OPEN") -> dict:
        '''
        Party_SetAccessibility
        Set party accessibility to OPEN or CLOSED
        '''
        party_id = self.__check_party_id(party_id)
        data = self.post(endpoint=f"/parties/v1/parties/{party_id}/accessibility",
                         endpoint_type="glz", json_data={"Accessibility": f"{state}"})
        return data

    def set_party_queue(self, party_id=None, queue_id="unrated") -> dict:
        '''
        Party_MakeDefault
        Set party's active queue
        Queues: competitive, custom, deathmatch, ggteam (escalation), spikerush, unrated
        '''
        self.__check_queue_type(queue_id)
        party_id = self.__check_party_id(party_id)
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/makedefault?queueID={queue_id}", endpoint_type="glz")
        return data

    def make_custom_game(self, party_id=None) -> dict:
        '''
        Party_MakePartyInfoCustomGame
        Create a custom game
        '''
        party_id = self.__check_party_id(party_id)
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/makecustomgame", endpoint_type="glz")
        return data

    def set_custom_game_settings(self, party_id=None, map="Ascent", mode="/Game/GameModes/Bomb/BombGameMode.BombGameMode_C", server="aresriot.aws-rclusterprod-use1-1.na-gp-ashburn-1") -> dict:
        '''
        Party_SetCustomGameSettings
        NOTE: Maps are specified by their internal names
        i think this usually returns None???
        '''
        party_id = self.__check_party_id(party_id)
        data = self.post(endpoint=f"/parties/v1/parties/{party_id}/customgamesettings", endpoint_type="glz", json_data={
            "map": f"/Game/Maps/{map}/{map}",
            "Mode": mode,
            "GamePod": server,
        })
        return data

    def join_party(self, party_id) -> dict:
        '''
        Party_PlayerJoin
        Join a party from its ID
        NOTE: party must be OPEN
        '''
        data = self.post(
            endpoint=f"/parties/v1/players/{self.puuid}/joinparty/{party_id}", endpoint_type="glz")
        return data

    def leave_party(self, party_id=None) -> dict:
        '''
        Party_PlayerLeave
        Leave a party from its ID
        '''
        party_id = self.__check_party_id(party_id)
        data = self.post(
            endpoint=f"/parties/v1/players/{self.puuid}/joinparty/{party_id}", endpoint_type="glz")
        return data

    # pregame endpoints
    def fetch_pregame_from_puuid(self, puuid=None) -> dict:
        '''
        Pregame_GetPlayer
        Fetch basic match information during pregame
        '''
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/pregame/v1/players/{puuid}", endpoint_type="glz")
        return data

    def fetch_pregame_from_matchid(self, match_id) -> dict:
        '''
        Pregame_GetMatch
        Fetch agent select information and other basic match information
        '''
        data = self.fetch(
            endpoint=f"/pregame/v1/matches/{match_id}", endpoint_type="glz")
        return data

    def fetch_loadouts_in_pregame(self, match_id) -> dict:
        '''
        Pregame_GetMatchLoadouts
        Fetch skin loadouts for all players
        '''
        data = self.fetch(
            endpoint=f"/pregame/v1/matches/{match_id}/loadouts", endpoint_type="glz")
        return data

    def select_character(self, match_id, character_id) -> dict:
        '''
        Pregame_SelectCharacter
        Select an agent during pregame
        '''
        data = self.post(
            endpoint=f"/pregame/v1/matches/{match_id}/select/{character_id}", endpoint_type="glz")
        return data

    def lock_character(self, match_id, character_id) -> dict:
        '''
        Pregame_LockCharacter
        Lock an agent during pregame
        '''
        data = self.post(
            endpoint=f"/pregame/v1/matches/{match_id}/lock/{character_id}", endpoint_type="glz")
        return data

    # penalties endpoints
    def fetch_penalties(self) -> dict:
        '''
        Restrictions_FetchPlayerRestrictionsV2
        Fetch any queue penalties for the current user
        '''
        data = self.fetch(
            endpoint="/restrictions/v2/penalties", endpoint_type="pd")
        return data

    # session endpoints
    def fetch_session(self, puuid=None) -> dict:
        '''

        '''
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/session/v1/sessions/{puuid}", endpoint_type="glz")
        return data

    # store endpoints
    def fetch_store_entitlements(self, puuid=None, item_type="e7c63390-eda7-46e0-bb7a-a6abdacd2433") -> dict:
        '''
        Store_getEntitlements
        ???
        '''
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/store/v1/entitlements/{puuid}/{item_type}", endpoint_type="pd")
        return data

    def fetch_store_offers(self) -> dict:
        '''
        Store_GetOffers
        Fetch all possible store offers
        '''
        data = self.fetch(endpoint=f"/store/v1/offers", endpoint_type="pd")
        return data

    def fetch_wallet(self, puuid=None) -> dict:
        '''
        Store_GetWallet
        Fetch wallet balances
        '''
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/store/v1/wallet/{puuid}", endpoint_type="pd")
        return data

    def fetch_storefront(self, puuid=None) -> dict:
        '''
        Store_GetStorefrontV2
        Fetch storefront
        '''
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/store/v2/storefront/{puuid}", endpoint_type="pd")
        return data


    # local utility functions
    def __check_puuid(self, puuid) -> str:
        '''If puuid passed into method is None make it current user's puuid'''
        return self.puuid if puuid is None else puuid

    def __check_party_id(self, party_id) -> str:
        '''If party ID passed into method is None make it user's current party'''
        return self.__get_current_party_id() if party_id is None else party_id

    def __get_current_party_id(self) -> str:
        '''Get the user's current party ID'''
        party = self.fetch_party_from_puuid()
        return party["CurrentPartyID"]

    def __check_queue_type(self, queue_id) -> None:
        '''Check if queue id is valid'''
        if not queue_id in queues:
            raise ValueError("Invalid queue type")

    def __build_urls(self) -> str:
        '''Generate URLs based on region/shard'''
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
