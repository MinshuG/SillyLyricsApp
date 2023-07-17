from logging import Logger
from typing import TYPE_CHECKING
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler
from datetime import datetime
from dataclasses import dataclass
from external.mxlrc import Song


if TYPE_CHECKING:
    from main import TransparentLyricsApp

logger = Logger("spotify")

@dataclass
class TrackInfo:
    song: Song
    playback_time: int
    is_playing: bool



class QtCacheHandler(CacheHandler):

    def __init__(self, app: 'TransparentLyricsApp'):
        self.app = app

    def get_cached_token(self):
        token_info = None
        try:
            token_info = self.app.config.token_info
        except KeyError:
            Logger.debug("Token not found in the session")

        return token_info

    def save_token_to_cache(self, token_info):
        try:
            self.app.config.token_info = token_info
            self.app.save_config()
        except Exception as e:
            Logger.warning("Error saving token to cache: " + str(e))


class SpotifyPlayer:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.sp = None

    def authenticate(self, cache_handler=None):
        scope = "user-read-playback-state"
        auth_manager = SpotifyOAuth(client_id=self.client_id, client_secret=self.client_secret, redirect_uri=self.redirect_uri, scope=scope, cache_handler=cache_handler)
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    def highjack_auth(self):
        return "Bearer ..."

    def get_lyrics(self, uri):
        url = f"https://spclient.wg.spotify.com/color-lyrics/v2/track/{uri.split(':')[2]}/image/spotify%3Aimage%3Aab67616d0000b2730504fdf58bae8cd52dd13047?format=json&vocalRemoval=true&market=from_token"
        backup_auth = self.sp._auth_headers
        self.sp._auth_headers = self.highjack_auth
        try:
            lyrics = self.sp._get(url)
        finally:
            self.sp._auth_headers = backup_auth # restore original auth headers method

        return lyrics

    def get_current_playing_info(self):
        if self.sp is None:
            raise Exception("Spotify authentication required. Call the 'authenticate' method first.")

        current_playing = self.sp.current_user_playing_track()
        current_time = datetime.now()

        if current_playing is not None and 'item' in current_playing:
            track = current_playing['item']
            if track is None:
                return None
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            album_name = track['album']['name']
            uri = track['uri']
            track_duration = track['duration_ms']

            playback_time = current_playing['progress_ms']
            is_playing = current_playing['is_playing']
            song = Song(artist_name, track_name, album_name, uri)
            # playback_time -= 100 # 1 second delay

            # lyrics = self.get_lyrics(uri)

            return TrackInfo(song, playback_time, is_playing)
        else:
            return None

# spotify_player = SpotifyPlayer("ccdc1d4e962048a09696011fe94c7c25", "02cf7c64044e482bad7c44e8100a4acb", "http://localhost:1231")
# spotify_player.authenticate()
# current_info = spotify_player.get_current_playing_info()

# if current_info is not None:
#     print("Currently playing:", current_info.track_name, "by", current_info.artist_name)
#     print("Current playback time:", current_info.playback_time, "ms")
# else:
#     print("No track is currently playing.")


