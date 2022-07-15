# module imports
import typing as t
import requests
import os
import base64
import urllib3
import json

# imports for modules used in the package
from .resources import regions
from .resources import region_shard_override, shard_region_override
from .resources import base_endpoint
from .resources import base_endpoint_glz
from .resources import base_endpoint_local
from .resources import base_endpoint_shared
from .resources import queues

from .auth import Auth

# exceptions
from .exceptions import ResponseError, HandshakeError, LockfileError, PhaseError

# disable urllib3 warnings that might arise from making requests to 127.0.0.1
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Client:
    def __init__(self, region: t.Text="na", auth: t.Optional[t.Mapping]=None):
        """
        NOTE: when using manual auth, local endpoints will not be available
        auth format:
        {
            "username":"usernamehere",
            "password":"passwordhere"
        }
        """
        if auth is None:
            self.lockfile_path = os.path.join(
                os.getenv("LOCALAPPDATA"), R"Riot Games\Riot Client\Config\lockfile"
            )

        self.puuid = ""
        self.player_name = ""
        self.player_tag = ""
        self.lockfile = {}
        self.headers = {}
        self.local_headers = {}
        self.region = region
        self.shard = region
        self.auth = None
        self.client_platform = "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"

        if auth is not None:
            self.auth = Auth(auth)

        if region in regions:
            self.region = region
        else:
            raise ValueError(f"Invalid region, valid regions are: {regions}")

        if self.region in region_shard_override.keys():
            self.shard = region_shard_override[self.region]
        if self.shard in shard_region_override.keys():
            self.region = shard_region_override[self.shard]

        self.base_url, self.base_url_glz, self.base_url_shared = self.__build_urls()

    def activate(self) -> None:
        """Activate the client and get authorization"""
        try:
            if self.auth is None:
                self.lockfile = self.__get_lockfile()
                self.puuid, self.headers, self.local_headers = self.__get_headers()

                session = self.rnet_fetch_chat_session()
                self.player_name = session["game_name"]
                self.player_tag = session["game_tag"]
            else:
                self.puuid, self.headers, self.local_headers = self.auth.authenticate()
        except:
            raise HandshakeError("Unable to activate; is VALORANT running?")

    @staticmethod
    def fetch_regions() -> t.List:
        """Fetch valid regions"""
        return regions

    def __verify_status_code(self, status_code, exceptions={}):
        """Verify that the request was successful according to exceptions"""
        if status_code in exceptions.keys():
            response_exception = exceptions[status_code]
            raise response_exception[0](response_exception[1])

    def fetch(
        self, endpoint="/", endpoint_type="pd", exceptions={}
    ) -> dict:  # exception: code: {Exception, Message}
        """Get data from a pd/glz/local endpoint"""
        data = None
        if endpoint_type in ["pd", "glz", "shared"]:
            response = requests.get(
                f'{self.base_url_glz if endpoint_type == "glz" else self.base_url if endpoint_type == "pd" else self.base_url_shared if endpoint_type == "shared" else self.base_url}{endpoint}',
                headers=self.headers,
            )

            # custom exceptions for http status codes
            self.__verify_status_code(response.status_code, exceptions)

            try:
                data = json.loads(response.text)
            except:  # as no data is set, an exception will be raised later in the method
                pass

        elif endpoint_type == "local":
            response = requests.get(
                "https://127.0.0.1:{port}{endpoint}".format(
                    port=self.lockfile["port"], endpoint=endpoint
                ),
                headers=self.local_headers,
                verify=False,
            )

            # custom exceptions for http status codes
            self.__verify_status_code(response.status_code, exceptions)

            try:
                data = response.json()
            except:  # as no data is set, an exception will be raised later in the method
                pass

        if data is None:
            raise ResponseError("Request returned NoneType")

        if "httpStatus" not in data:
            return data
        if data["httpStatus"] == 400:
            # if headers expire (i dont think they ever do but jic), refresh em!
            if self.auth is None:
                self.puuid, self.headers, self.local_headers = self.__get_headers()
            else:
                self.puuid, self.headers, self.local_headers = self.auth.authenticate()
            return self.fetch(endpoint=endpoint, endpoint_type=endpoint_type)

    def post(
        self, endpoint="/", endpoint_type="pd", json_data={}, exceptions={}
    ) -> dict:
        """Post data to a pd/glz endpoint"""
        data = None
        response = requests.post(
            f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}',
            headers=self.headers,
            json=json_data,
        )

        # custom exceptions for http status codes
        self.__verify_status_code(response.status_code, exceptions)

        try:
            data = json.loads(response.text)
        except:
            data = None

        return data

    def put(
        self, endpoint="/", endpoint_type="pd", json_data={}, exceptions={}
    ) -> dict:
        response = requests.put(
            f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}',
            headers=self.headers,
            data=json.dumps(json_data),
        )
        data = json.loads(response.text)

        # custom exceptions for http status codes
        self.__verify_status_code(response.status_code, exceptions)

        if data is not None:
            return data
        else:
            raise ResponseError("Request returned NoneType")

    def delete(
        self, endpoint="/", endpoint_type="pd", json_data={}, exceptions={}
    ) -> dict:
        response = requests.delete(
            f'{self.base_url_glz if endpoint_type == "glz" else self.base_url}{endpoint}',
            headers=self.headers,
            data=json.dumps(json_data),
        )
        data = json.loads(response.text)

        # custom exceptions for http status codes
        self.__verify_status_code(response.status_code, exceptions)

        if data is not None:
            return data
        else:
            raise ResponseError("Request returned NoneType")

    # --------------------------------------------------------------------------------------------------

    # PVP endpoints
    def fetch_content(self) -> t.Mapping[str, t.Any]:
        """
        Content_FetchContent
        Get names and ids for game content such as agents, maps, guns, etc.
        """
        data = self.fetch(
            endpoint="/content-service/v3/content", endpoint_type="shared"
        )
        return data

    def fetch_account_xp(self) -> t.Mapping[str, t.Any]:
        """
        AccountXP_GetPlayer
        Get the account level, XP, and XP history for the active player
        """
        data = self.fetch(
            endpoint=f"/account-xp/v1/players/{self.puuid}", endpoint_type="pd"
        )
        return data

    def fetch_player_loadout(self) -> t.Mapping[str, t.Any]:
        """
        playerLoadoutUpdate
        Get the player's current loadout
        """
        data = self.fetch(
            endpoint=f"/personalization/v2/players/{self.puuid}/playerloadout",
            endpoint_type="pd",
        )
        return data

    def put_player_loadout(self, loadout: t.Mapping) -> t.Mapping[str, t.Any]:
        """
        playerLoadoutUpdate
        Use the values from client.fetch_player_loadout() excluding properties like subject and version. Loadout changes take effect when starting a new game
        """
        data = self.put(
            endpoint=f"/personalization/v2/players/{self.puuid}/playerloadout",
            endpoint_type="pd",
            json_data=loadout,
        )
        return data

    def fetch_mmr(self, puuid: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        MMR_FetchPlayer
        Get the match making rating for a player
        """
        puuid = self.__check_puuid(puuid)
        data = self.fetch(endpoint=f"/mmr/v1/players/{puuid}", endpoint_type="pd")
        return data

    def fetch_match_history(
        self,
        puuid: t.Optional[t.Text] = None,
        start_index: int = 0,
        end_index: int = 15,
        queue_id: t.Text = "null",
    ) -> dict:
        """
        MatchHistory_FetchMatchHistory
        Get recent matches for a player
        There are 3 optional query parameters: start_index, end_index, and queue_id. queue can be one of null, competitive, custom, deathmatch, ggteam, newmap, onefa, snowball, spikerush, or unrated.
        """
        self.__check_queue_type(queue_id)
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/match-history/v1/history/{puuid}?startIndex={start_index}&endIndex={end_index}"
            + (f"&queue={queue_id}" if queue_id != "null" else ""),
            endpoint_type="pd",
        )
        return data

    def fetch_match_details(self, match_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Get the full info for a previous match
        Includes everything that the in-game match details screen shows including damage and kill positions, same as the official API w/ a production key
        """
        data = self.fetch(
            endpoint=f"/match-details/v1/matches/{match_id}", endpoint_type="pd"
        )
        return data

    def fetch_competitive_updates(
        self,
        puuid: t.Optional[t.Text] = None,
        start_index: int = 0,
        end_index: int = 15,
        queue_id: t.Text = "competitive",
    ) -> dict:
        """
        MMR_FetchCompetitiveUpdates
        Get recent games and how they changed ranking
        There are 3 optional query parameters: start_index, end_index, and queue_id. queue can be one of null, competitive, custom, deathmatch, ggteam, newmap, onefa, snowball, spikerush, or unrated.
        """
        self.__check_queue_type(queue_id)
        puuid = self.__check_puuid(puuid)
        data = self.fetch(
            endpoint=f"/mmr/v1/players/{puuid}/competitiveupdates?startIndex={start_index}&endIndex={end_index}"
            + (f"&queue={queue_id}" if queue_id != "" else ""),
            endpoint_type="pd",
        )
        return data

    def fetch_leaderboard(
        self, season: t.Text, start_index: int = 0, size: int = 25, region: t.Text = "na"
    ) -> dict:
        """
        MMR_FetchLeaderboard
        Get the competitive leaderboard for a given season
        The query parameter query can be added to search for a username.
        """
        if season == "":
            season = self.__get_live_season()
        data = self.fetch(
            f"/mmr/v1/leaderboards/affinity/{region}/queue/competitive/season/{season}?startIndex={start_index}&size={size}",
            endpoint_type="pd",
        )
        return data

    def fetch_player_restrictions(self) -> t.Mapping[str, t.Any]:
        """
        Restrictions_FetchPlayerRestrictionsV2
        Checks for any gameplay penalties on the account
        """
        data = self.fetch(f"/restrictions/v3/penalties", endpoint_type="pd")
        return data

    def fetch_item_progression_definitions(self) -> t.Mapping[str, t.Any]:
        """
        ItemProgressionDefinitionsV2_Fetch
        Get details for item upgrades
        """
        data = self.fetch("/contract-definitions/v3/item-upgrades", endpoint_type="pd")
        return data

    def fetch_config(self) -> t.Mapping[str, t.Any]:
        """
        Config_FetchConfig
        Get various internal game configuration settings set by Riot
        """
        data = self.fetch(f"/v1/config/{self.region}", endpoint_type="shared")
        return data

    # store endpoints
    def store_fetch_offers(self) -> t.Mapping[str, t.Any]:
        """
        Store_GetOffers
        Get prices for all store items
        """
        data = self.fetch("/store/v1/offers/", endpoint_type="pd")
        return data

    def store_fetch_storefront(self) -> t.Mapping[str, t.Any]:
        """
        Store_GetStorefrontV2
        Get the currently available items in the store
        """
        data = self.fetch(f"/store/v2/storefront/{self.puuid}", endpoint_type="pd")
        return data

    def store_fetch_wallet(self) -> t.Mapping[str, t.Any]:
        """
        Store_GetWallet
        Get amount of Valorant points and Radianite the player has
        Valorant points have the id 85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741 and Radianite points have the id e59aa87c-4cbf-517a-5983-6e81511be9b7
        """
        data = self.fetch(f"/store/v1/wallet/{self.puuid}", endpoint_type="pd")
        return data

    def store_fetch_order(self, order_id: str) -> t.Mapping[str, t.Any]:
        """
        Store_GetOrder
        {order id}: The ID of the order. Can be obtained when creating an order.
        """
        data = self.fetch(f"/store/v1/order/{order_id}", endpoint_type="pd")
        return data

    def store_fetch_entitlements(
        self, item_type: t.Text = "e7c63390-eda7-46e0-bb7a-a6abdacd2433"
    ) -> t.Mapping[str, t.Any]:
        """
        Store_GetEntitlements
        List what the player owns (agents, skins, buddies, ect.)
        Correlate with the UUIDs in client.fetch_content() to know what items are owned

        NOTE: uuid to item type
        "e7c63390-eda7-46e0-bb7a-a6abdacd2433": "skin_level",
        "3ad1b2b2-acdb-4524-852f-954a76ddae0a": "skin_chroma",
        "01bb38e1-da47-4e6a-9b3d-945fe4655707": "agent",
        "f85cb6f7-33e5-4dc8-b609-ec7212301948": "contract_definition",
        "dd3bf334-87f3-40bd-b043-682a57a8dc3a": "buddy",
        "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475": "spray",
        "3f296c07-64c3-494c-923b-fe692a4fa1bd": "player_card",
        "de7caa6b-adf7-4588-bbd1-143831e786c6": "player_title",
        """
        data = self.fetch(
            endpoint=f"/store/v1/entitlements/{self.puuid}/{item_type}",
            endpoint_type="pd",
        )
        return data

    # party endpoints
    def party_fetch_player(self) -> t.Mapping[str, t.Any]:
        """
        Party_FetchPlayer
        Get the Party ID that a given player belongs to
        """
        data = self.fetch(
            endpoint=f"/parties/v1/players/{self.puuid}", endpoint_type="glz"
        )
        return data

    def party_remove_player(self, puuid: t.Text) -> t.NoReturn:
        """
        Party_RemovePlayer
        Removes a player from the current party
        """
        puuid = self.__check_puuid(puuid)
        data = self.delete(endpoint=f"/parties/v1/players/{puuid}", endpoint_type="glz")
        return data

    def fetch_party(self) -> t.Mapping[str, t.Any]:
        """
        Party_FetchParty
        Get details about a given party id
        """
        party_id = self.__get_current_party_id()
        data = self.fetch(
            endpoint=f"/parties/v1/parties/{party_id}", endpoint_type="glz"
        )
        return data

    def party_set_member_ready(self, ready: bool) -> t.Mapping[str, t.Any]:
        """
        Party_SetMemberReady
        Sets whether a party member is ready for queueing or not
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/members/{self.puuid}/setReady",
            endpoint_type="glz",
            json_data={"ready": ready},
        )
        return data

    def party_refresh_competitive_tier(self) -> t.Mapping[str, t.Any]:
        """
        Party_RefreshCompetitiveTier
        Refreshes the competitive tier for a player
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/members/{self.puuid}/refreshCompetitiveTier",
            endpoint_type="glz",
        )
        return data

    def party_refresh_player_identity(self) -> t.Mapping[str, t.Any]:
        """
        Party_RefreshPlayerIdentity
        Refreshes the identity for a player
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/members/{self.puuid}/refreshPlayerIdentity",
            endpoint_type="glz",
        )
        return data

    def party_refresh_pings(self) -> t.Mapping[str, t.Any]:
        """
        Party_RefreshPings
        Refreshes the pings for a player
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/members/{self.puuid}/refreshPings",
            endpoint_type="glz",
        )
        return data

    def party_change_queue(self, queue_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Party_ChangeQueue
        Sets the matchmaking queue for the party
        """
        self.__check_queue_type(queue_id)
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/queue",
            endpoint_type="glz",
            json_data={"queueID": queue_id},
        )
        return data

    def party_start_custom_game(self) -> t.Mapping[str, t.Any]:
        """
        Party_StartCustomGame
        Starts a custom game
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/startcustomgame",
            endpoint_type="glz",
        )
        return data

    def party_enter_matchmaking_queue(self) -> t.Mapping[str, t.Any]:
        """
        Party_EnterMatchmakingQueue
        Enters the matchmaking queue
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/matchmaking/join",
            endpoint_type="glz",
        )
        return data

    def party_leave_matchmaking_queue(self) -> t.Mapping[str, t.Any]:
        """
        Party_LeaveMatchmakingQueue
        Leaves the matchmaking queue
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/matchmaking/leave",
            endpoint_type="glz",
        )
        return data

    def set_party_accessibility(self, open: bool) -> t.Mapping[str, t.Any]:
        """
        Party_SetAccessibility
        Changes the party accessibility to be open or closed
        """
        state = "OPEN" if open else "CLOSED"
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/accessibility",
            endpoint_type="glz",
            json_data={"accessibility": state},
        )
        return data

    def party_set_custom_game_settings(self, settings: t.Mapping) -> t.Mapping[str, t.Any]:
        """
        Party_SetCustomGameSettings
        Changes the settings for a custom game

        settings:
        {
            "Map": "/Game/Maps/Triad/Triad", # map url
            "Mode": "/Game/GameModes/Bomb/BombGameMode.BombGameMode_C", # url to gamemode
            "UseBots": true, # this isn't used anymore :(
            "GamePod": "aresriot.aws-rclusterprod-use1-1.na-gp-ashburn-awsedge-1", # server
            "GameRules": null # idk what this is for
        }
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/customgamesettings",
            endpoint_type="glz",
            json_data=settings,
        )
        return data

    def party_invite_by_display_name(self, name: t.Text, tag: t.Text) -> t.Mapping[str, t.Any]:
        """
        Party_InviteToPartyByDisplayName
        Invites a player to the party with their display name

        omit the "#" in tag
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/invites/name/{name}/tag/{tag}",
            endpoint_type="glz",
        )
        return data

    def party_request_to_join(self, party_id: t.Text, other_puuid: t.Text) -> t.Mapping[str, t.Any]:
        """
        Party_RequestToJoinParty
        Requests to join a party
        """
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/request",
            endpoint_type="glz",
            json_data={"Subjects": [other_puuid]},
        )
        return data

    def party_decline_request(self, request_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Party_DeclineRequest
        Declines a party request

        {request id}: The ID of the party request. Can be found from the Requests array on the Party_FetchParty endpoint.
        """
        party_id = self.__get_current_party_id()
        data = self.post(
            endpoint=f"/parties/v1/parties/{party_id}/request/{request_id}/decline",
            endpoint_type="glz",
        )
        return data

    def party_join(self, party_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Party_PlayerJoin
        Join a party
        """
        data = self.post(
            endpoint=f"/parties/v1/players/{self.puuid}/joinparty/{party_id}",
            endpoint_type="glz",
        )
        return data

    def party_leave(self, party_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Party_PlayerLeave
        Leave a party
        """
        data = self.post(
            endpoint=f"/parties/v1/players/{self.puuid}/leaveparty/{party_id}",
            endpoint_type="glz",
        )
        return data

    def party_fetch_custom_game_configs(self) -> t.Mapping[str, t.Any]:
        """
        Party_FetchCustomGameConfigs
        Get information about the available gamemodes
        """
        data = self.fetch(
            endpoint="/parties/v1/parties/customgameconfigs", endpoint_type="glz"
        )
        return data

    def party_fetch_muc_token(self) -> t.Mapping[str, t.Any]:
        """
        Party_FetchMUCToken
        Get a token for party chat
        """
        party_id = self.__get_current_party_id()
        data = self.fetch(
            endpoint=f"/parties/v1/parties/{party_id}/muctoken", endpoint_type="glz"
        )
        return data

    def party_fetch_voice_token(self) -> t.Mapping[str, t.Any]:
        """
        Party_FetchVoiceToken
        Get a token for party voice
        """
        party_id = self.__get_current_party_id()
        data = self.fetch(
            endpoint=f"/parties/v1/parties/{party_id}/voicetoken", endpoint_type="glz"
        )
        return data

    # live game endpoints
    def coregame_fetch_player(self) -> t.Mapping[str, t.Any]:
        """
        CoreGame_FetchPlayer
        Get the game ID for an ongoing game the player is in
        """
        data = self.fetch(
            endpoint=f"/core-game/v1/players/{self.puuid}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a core-game"]},
        )
        return data

    def coregame_fetch_match(self, match_id: str = None) -> t.Mapping[str, t.Any]:
        """
        CoreGame_FetchMatch
        Get information about an ongoing game
        """
        match_id = self.__coregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/core-game/v1/matches/{match_id}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a core-game"]},
        )
        return data

    def coregame_fetch_match_loadouts(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        CoreGame_FetchMatchLoadouts
        Get player skins and sprays for an ongoing game
        """
        match_id = self.__coregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/core-game/v1/matches/{match_id}/loadouts",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a core-game"]},
        )
        return data

    def coregame_fetch_team_chat_muc_token(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        CoreGame_FetchTeamChatMUCToken
        Get a token for team chat
        """
        match_id = self.__coregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/core-game/v1/matches/{match_id}/teamchatmuctoken",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a core-game"]},
        )
        return data

    def coregame_fetch_allchat_muc_token(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        CoreGame_FetchAllChatMUCToken
        Get a token for all chat
        """
        match_id = self.__coregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/core-game/v1/matches/{match_id}/allchatmuctoken",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a core-game"]},
        )
        return data

    def coregame_disassociate_player(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        CoreGame_DisassociatePlayer
        Leave an in-progress game
        """
        match_id = self.__coregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/core-game/v1/players/{self.puuid}/disassociate/{match_id}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a core-game"]},
        )
        return data

    # pregame endpoints
    def pregame_fetch_player(self) -> t.Mapping[str, t.Any]:
        """
        Pregame_GetPlayer
        Get the ID of a game in the pre-game stage
        """
        data = self.fetch(
            endpoint=f"/pregame/v1/players/{self.puuid}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_fetch_match(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_GetMatch
        Get info for a game in the pre-game stage
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/pregame/v1/matches/{match_id}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_fetch_match_loadouts(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_GetMatchLoadouts
        Get player skins and sprays for a game in the pre-game stage
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/pregame/v1/matches/{match_id}/loadouts",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_fetch_chat_token(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_FetchChatToken
        Get a chat token
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/pregame/v1/matches/{match_id}/chattoken",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_fetch_voice_token(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_FetchVoiceToken
        Get a voice token
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.fetch(
            endpoint=f"/pregame/v1/matches/{match_id}/voicetoken",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_select_character(self, agent_id: t.Text, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_SelectCharacter
        Select an agent

        don't use this for instalocking :)
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.post(
            endpoint=f"/pregame/v1/matches/{match_id}/select/{agent_id}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_lock_character(self, agent_id: t.Text, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_LockCharacter
        Lock in an agent

        don't use this for instalocking :)
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.post(
            endpoint=f"/pregame/v1/matches/{match_id}/lock/{agent_id}",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    def pregame_quit_match(self, match_id: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        Pregame_QuitMatch
        Quit a match in the pre-game stage
        """
        match_id = self.__pregame_check_match_id(match_id)
        data = self.post(
            endpoint=f"/pregame/v1/matches/{match_id}/quit",
            endpoint_type="glz",
            exceptions={404: [PhaseError, "You are not in a pre-game"]},
        )
        return data

    # contracts endpoints
    def contracts_fetch_definitions(self) -> t.Mapping[str, t.Any]:
        """
        ContractDefinitions_Fetch
        Get names and descriptions for contracts
        """
        data = self.fetch(
            endpoint="/contract-definitions/v3/definitions", endpoint_type="pd"
        )
        return data

    def contracts_fetch(self) -> t.Mapping[str, t.Any]:
        """
        Contracts_Fetch
        Get a list of contracts and completion status including match history
        """
        data = self.fetch(
            endpoint=f"/contracts/v1/contracts/{self.puuid}", endpoint_type="pd"
        )
        return data

    def contracts_activate(self, contract_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Contracts_Activate
        Activate a particular contract

        {contract id}: The ID of the contract to activate. Can be found from the ContractDefinitions_Fetch endpoint.
        """
        data = self.post(
            endpoint=f"/contracts/v1/contracts/{self.puuid}/special/{contract_id}",
            endpoint_type="pd",
        )
        return data

    def contracts_fetch_active_story(self) -> t.Mapping[str, t.Any]:
        """
        ContractDefinitions_FetchActiveStory
        Get the battlepass contracts
        """
        data = self.fetch(
            endpoint=f"/contract-definitions/v3/definitions/story", endpoint_type="pd"
        )
        return data

    def itemprogress_fetch_definitions(self) -> t.Mapping[str, t.Any]:
        """
        ItemProgressDefinitionsV2_Fetch
        Fetch definitions for skin upgrade progressions
        """
        data = self.fetch(
            endpoint=f"/contract-definitions/v3/item-upgrades", endpoint_type="pd"
        )
        return data

    def contracts_unlock_item_progress(self, progression_id: t.Text) -> t.Mapping[str, t.Any]:
        """
        Contracts_UnlockItemProgressV2
        Unlock an item progression
        """
        data = self.post(
            endpoint=f"/contracts/v2/item-upgrades/{progression_id}/{self.puuid}",
            endpoint_type="pd",
        )
        return data

    # session endpoints
    def session_fetch(self) -> dict:
        """
        Session_Get
        Get information about the current game session
        """
        data = self.fetch(
            endpoint=f"/session/v1/sessions/{self.puuid}", endpoint_type="glz"
        )
        return data

    def session_reconnect(self) -> dict:
        """
        Session_ReConnect
        """
        data = self.fetch(
            endpoint=f"/session/v1/sessions/{self.puuid}/reconnect", endpoint_type="glz"
        )
        return data

    # local riotclient endpoints
    def fetch_presence(self, puuid: t.Optional[t.Text] = None) -> t.Mapping[str, t.Any]:
        """
        PRESENCE_RNet_GET
        NOTE: Only works on self or active user's friends
        """
        puuid = self.__check_puuid(puuid)
        data = self.fetch(endpoint="/chat/v4/presences", endpoint_type="local")
        try:
            for presence in data["presences"]:
                if presence["puuid"] == puuid:
                    return json.loads(base64.b64decode(presence["private"]))
        except:
            return None

    def fetch_all_friend_presences(self) -> t.Mapping[str, t.Any]:
        """
        PRESENCE_RNet_GET_ALL
        Get a list of online friends and their activity
        private is a base64-encoded JSON string that contains useful information such as party and in-progress game score.
        """
        data = self.fetch(endpoint="/chat/v4/presences", endpoint_type="local")
        return data

    def riotclient_session_fetch_sessions(self) -> t.Mapping[str, t.Any]:
        """
        RiotClientSession_FetchSessions
        Gets info about the running Valorant process including start arguments
        """
        data = self.fetch(
            endpoint="/product-session/v1/external-sessions", endpoint_type="local"
        )
        return data

    def rnet_fetch_active_alias(self) -> t.Mapping[str, t.Any]:
        """
        PlayerAlias_RNet_GetActiveAlias
        Gets the player username and tagline
        """
        data = self.fetch(
            endpoint="/player-account/aliases/v1/active", endpoint_type="local"
        )
        return data

    def rso_rnet_fetch_entitlements_token(self) -> t.Mapping[str, t.Any]:
        """
        RSO_RNet_GetEntitlementsToken
        Gets both the token and entitlement for API usage
        accessToken is used as the token and token is used as the entitlement.
        PBE access can be checked through here
        """
        data = self.fetch(
            endpoint="/player-account/aliases/v1/active", endpoint_type="local"
        )
        return data

    def rnet_fetch_chat_session(self) -> t.Mapping[str, t.Any]:
        """
        TEXT_CHAT_RNet_FetchSession
        Get the current session including player name and PUUID
        """
        data = self.fetch(endpoint="/chat/v1/session", endpoint_type="local")
        return data

    def rnet_fetch_all_friends(self) -> t.Mapping[str, t.Any]:
        """
        CHATFRIENDS_RNet_GET_ALL
        Get a list of friends
        """
        data = self.fetch(endpoint="/chat/v4/friends", endpoint_type="local")
        return data

    def rnet_fetch_settings(self) -> t.Mapping[str, t.Any]:
        """
        RiotKV_RNet_GetSettings
        Get client settings
        """
        data = self.fetch(
            endpoint="/player-preferences/v1/data-json/Ares.PlayerSettings",
            endpoint_type="local",
        )
        return data

    def rnet_fetch_friend_requests(self) -> t.Mapping[str, t.Any]:
        """
        FRIENDS_RNet_FetchFriendRequests
        Get pending friend requests
        """
        data = self.fetch(endpoint="/chat/v4/friendrequests", endpoint_type="local")
        return data

    # local utility functions
    def __get_live_season(self) -> str:
        """Get the UUID of the live competitive season"""
        return self.fetch_mmr()["LatestCompetitiveUpdate"]["SeasonID"]

    def __check_puuid(self, puuid) -> str:
        """If puuid passed into method is None make it current user's puuid"""
        return self.puuid if puuid is None else puuid

    def __check_party_id(self, party_id) -> str:
        """If party ID passed into method is None make it user's current party"""
        return self.__get_current_party_id() if party_id is None else party_id

    def __get_current_party_id(self) -> str:
        """Get the user's current party ID"""
        party = self.party_fetch_player()
        return party["CurrentPartyID"]

    def __coregame_check_match_id(self, match_id) -> str:
        """Check if a match id was passed into the method"""
        return self.coregame_fetch_player()["MatchID"] if match_id is None else match_id

    def __pregame_check_match_id(self, match_id) -> str:
        return self.pregame_fetch_player()["MatchID"] if match_id is None else match_id

    def __check_queue_type(self, queue_id) -> t.NoReturn:
        """Check if queue id is valid"""
        if queue_id not in queues:
            raise ValueError("Invalid queue type")

    def __build_urls(self) -> str:
        """Generate URLs based on region/shard"""
        base_url = base_endpoint.format(shard=self.shard)
        base_url_glz = base_endpoint_glz.format(shard=self.shard, region=self.region)
        base_url_shared = base_endpoint_shared.format(shard=self.shard)
        return base_url, base_url_glz, base_url_shared

    def __get_headers(self) -> t.Tuple[t.Text, t.Mapping[t.Text, t.Any]]:
        """Get authorization headers to make requests"""
        try:
            if self.auth is None:
                return self.__get_auth_headers()
            puuid, headers, _ = self.auth.authenticate()
            headers["X-Riot-ClientPlatform"] = (self.client_platform,)
            headers["X-Riot-ClientVersion"] = self.__get_current_version()
            return puuid, headers, None

        except Exception as e:
            print(e)
            raise HandshakeError("Unable to get headers; is VALORANT running?")

    def __get_auth_headers(self) -> t.Tuple[t.Text, t.Mapping[t.Text, t.Any]]: 
        # headers for pd/glz endpoints
        local_headers = {
            "Authorization": (
                "Basic "
                + base64.b64encode(
                    ("riot:" + self.lockfile["password"]).encode()
                ).decode()
            )
        }
        response = requests.get(
            "https://127.0.0.1:{port}/entitlements/v1/token".format(
                port=self.lockfile["port"]
            ),
            headers=local_headers,
            verify=False,
        )
        entitlements = response.json()
        puuid = entitlements["subject"]
        headers = {
            "Authorization": f"Bearer {entitlements['accessToken']}",
            "X-Riot-Entitlements-JWT": entitlements["token"],
            "X-Riot-ClientPlatform": self.client_platform,
            "X-Riot-ClientVersion": self.__get_current_version(),
        }
        return puuid, headers, local_headers

    def __get_current_version(self) -> str:
        data = requests.get("https://valorant-api.com/v1/version")
        data = data.json()["data"]
        return f"{data['branch']}-shipping-{data['buildVersion']}-{data['version'].split('.')[3]}"  # return formatted version string

    def __get_lockfile(self) -> t.Optional[t.Mapping[str, t.Any]]:
        try:
            with open(self.lockfile_path) as lockfile:
                data = lockfile.read().split(":")
                keys = ["name", "PID", "port", "password", "protocol"]
                return dict(zip(keys, data))
        except:
            raise LockfileError("Lockfile not found")
