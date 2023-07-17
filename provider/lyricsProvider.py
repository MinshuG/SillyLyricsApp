from external.mxlrc import Song


class LyricsProvider:
    def __init__(self, providers: list):
        self.name = "LyricsProvider"
        self.provider = providers

    def getLyrics(self, song: Song):
        for provider in self.provider:
            lyrics = provider.find_lyrics(song)
            if lyrics:
                synced = provider.get_synced(song, lyrics)
                if synced:
                    return synced
        return None
