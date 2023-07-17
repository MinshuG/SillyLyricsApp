import re
import requests
import urllib.parse
from lyrics import LyricsNotFoundException


class ProviderNetease:
    requestHeader = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0"
    }

    @staticmethod
    def find_lyrics(song):
        title = song.title
        artist = song.artist

        searchURL = "https://music.xianqiao.wang/neteaseapiv2/search?limit=10&type=1&keywords="
        lyricURL = "https://music.xianqiao.wang/neteaseapiv2/lyric?id="

        # strip off (feat. xxx) from title
        cleanTitle = re.sub(r"\(.*\)", "", title).strip()
        del title

        finalURL = searchURL + urllib.parse.quote(f"{cleanTitle} {artist}")
        # print(finalURL)
        searchResults = requests.get(finalURL, data=None, headers= ProviderNetease.requestHeader)
        items = searchResults.json().get("result", {}).get("songs", None)
        if not items or len(items) == 0:
            return None
            raise LyricsNotFoundException("Cannot find track")

        itemId = 0
        if len(items) > 0:
            for i in range(len(items)):
                if items[i]["name"].lower() == cleanTitle.lower() and items[i]["artists"][0]["name"].lower() == artist.lower():
                    lyric_resp = requests.get(lyricURL + str(items[i]["id"]),data= None, headers=ProviderNetease.requestHeader)
                    if lyric_resp.json()["lrc"]["lyric"] == "":
                        continue
                    print("Lyrics URL: " + lyricURL + str(items[i]["id"]))
                    return lyric_resp.json()
        return None
        raise LyricsNotFoundException("Cannot find track")

    creditInfo = [
        "\\s?作?\\s*词|\\s?作?\\s*曲|\\s?编\\s*曲?|\\s?监\\s*制?",
        ".*编写|.*和音|.*和声|.*合声|.*提琴|.*录|.*工程|.*工作室|.*设计|.*剪辑|.*制作|.*发行|.*出品|.*后期|.*混音|.*缩混",
        "原唱|翻唱|题字|文案|海报|古筝|二胡|钢琴|吉他|贝斯|笛子|鼓|弦乐",
        "lrc|publish|vocal|guitar|program|produce|write|mix"
    ]
    creditInfoRegExp = re.compile(f"^({'|'.join(creditInfo)}).*(:|：)", re.I)

    @staticmethod
    def containCredits(text):
        return bool(ProviderNetease.creditInfoRegExp.search(text))

    @staticmethod
    def parseTimestamp(line: str):
        # "[00:00.000] 作词 : Benny Blanco/Nathan Perez/Khalid Robinson/Ashley Frangipane/Ed Sheeran"

        time_match = re.findall(r"\[(\d+:\d+\.\d+)\]", line)
        if not time_match or len(time_match) == 0:
            return {
                "time": None,
                "text": None
            }

        textIndex = line.index("]")

        # lyricist
        if line[textIndex+1:].find(":") > -1:
            return {
            "time": None,
            "text": None
        }
        # if not time_match or len(time_match) == 1:
        #     return {"text": line, "time": None}

        text = ""
        if textIndex > -1:
            text = line[textIndex + 1:]
            text = text.strip().replace("]", "")

        time = time_match[0]

        return {"time": time, "text": text}

    @staticmethod
    def breakdownLine(text):
        components = re.split(r"\(\d+,(\d+)\)", text)
        result = []
        for i in range(1, len(components), 2):
            if components[i + 1] == " ":
                continue
            result.append({
                "word": components[i + 1] + " ",
                "time": int(components[i])
            })
        return result

    @staticmethod
    def getKaraoke(list):
        lyricStr = list.klyric.lyric if list and list.klyric else None

        if not lyricStr:
            return None

        lines = lyricStr.splitlines()
        karaoke = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parsed = ProviderNetease.parseTimestamp(line)
            if not parsed["time"] or not parsed["text"]:
                continue

            key, value = parsed["time"].split(",") if parsed["time"] else []
            start = float(key) if key else None
            durr = float(value) if value else None

            if start is not None and durr is not None and not ProviderNetease.containCredits(parsed["text"]):
                karaoke.append({
                    "startTime": start,
                    "text": ProviderNetease.breakdownLine(parsed["text"])
                })

        if not karaoke:
            return None

        return karaoke

    @staticmethod
    def get_synced(song, list):
        lyricStr = list["lrc"]["lyric"] if list and list["lrc"] else None
        noLyrics = False

        if not lyricStr:
            return None

        lines = lyricStr.splitlines()
        lyrics = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parsed = ProviderNetease.parseTimestamp(line)
            if parsed["text"] == "纯音乐, 请欣赏":
                noLyrics = True
            if not parsed["time"] or not parsed["text"]:
                continue

            key, value = parsed["time"].split(":") if parsed["time"] else []
            min = float(key) if key else None
            sec = float(value) if value else None

            if min is not None and sec is not None and not ProviderNetease.containCredits(parsed["text"]):
                lyrics.append({
                    "startTime": (min * 60 + sec) * 1000,
                    "text": parsed["text"] or ""
                })

        if not lyrics or noLyrics:
            return None

        return lyrics

    @staticmethod
    def getTranslation(list):
        lyricStr = list.tlyric.lyric if list and list.tlyric else None

        if not lyricStr:
            return None

        lines = lyricStr.splitlines()
        translation = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parsed = ProviderNetease.parseTimestamp(line)
            if not parsed["time"] or not parsed["text"]:
                continue

            key, value = parsed["time"].split(":") if parsed["time"] else []
            min = float(key) if key else None
            sec = float(value) if value else None

            if min is not None and sec is not None and not ProviderNetease.containCredits(parsed["text"]):
                translation.append({
                    "startTime": (min * 60 + sec) * 1000,
                    "text": parsed["text"] or ""
                })

        if not translation:
            return None

        return translation

    @staticmethod
    def getUnsynced(list):
        lyricStr = list.lrc.lyric if list and list.lrc else None
        noLyrics = False

        if not lyricStr:
            return None

        lines = lyricStr.splitlines()
        lyrics = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parsed = ProviderNetease.parseTimestamp(line)
            if parsed["text"] == "纯音乐, 请欣赏":
                noLyrics = True
            if not parsed["text"] or ProviderNetease.containCredits(parsed["text"]):
                continue
            lyrics.append(parsed)

        if not lyrics or noLyrics:
            return None

        return lyrics

# # js exports lol
# ProviderNetease = {
#     "findLyrics": ProviderNetease.findLyrics,
#     "getKaraoke": ProviderNetease.getKaraoke,
#     "getSynced": ProviderNetease.getSynced,
#     "getUnsynced": ProviderNetease.getUnsynced,
#     "getTranslation": ProviderNetease.getTranslation
# }
