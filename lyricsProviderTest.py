from SwSpotify import spotify

from provider.neteaseProvider import ProviderNetease

import asyncio
import json

from winrt.windows.media.control import \
    GlobalSystemMediaTransportControlsSessionManager as MediaManager


async def get_media_info():
    sessions = await MediaManager.request_async()

    # This source_app_user_model_id check and if statement is optional
    # Use it if you want to only get a certain player/program's media
    # (e.g. only chrome.exe's media not any other program's).

    # To get the ID, use a breakpoint() to run sessions.get_current_session()
    # while the media you want to get is playing.
    # Then set TARGET_ID to the string this call returns.

    current_session = sessions.get_current_session()
    if current_session:  # there needs to be a media session running
        if current_session.source_app_user_model_id == 'Spotify.exe':  # TARGET_ID
            info = await current_session.try_get_media_properties_async()

            # song_attr[0] != '_' ignores system attributes
            info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if song_attr[0] != '_'}

            # converts winrt vector to list
            info_dict['genres'] = list(info_dict['genres'])

            return info_dict

    # It could be possible to select a program from a list of current
    # available ones. I just haven't implemented this here for my use case.
    # See references for more information.
    raise Exception('TARGET_PROGRAM is not the current media session')


def test():
    current_track = spotify.current()
    print(current_track)

    lyrics_resp = ProviderNetease.findLyrics(current_track[0], current_track[1], "").json()
    
    synced = ProviderNetease.getSynced(lyrics_resp)

    

    with open(f"lyrics-cache/{current_track[0]}-{current_track[1]}.json", "w", encoding="utf-8") as f:
        json.dump(synced, f, ensure_ascii=False, indent=4)
    # print(synced)




if __name__ == '__main__':
    test()
    # import asyncio
    # asyncio.run(get_media_info())
