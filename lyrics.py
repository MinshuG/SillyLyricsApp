import time
from logging import Logger

logger = Logger("lyrics")

class Lyrics:
    def __init__(self, lyrics_list: list):
        self.lyrics = lyrics_list
        self.start_time = None
        self.pause_time = None

    @property
    def elapsed_time(self): # ns
        if self.start_time is None:
            return 0
        if self.pause_time is not None:
            return self.pause_time - self.start_time
        return time.time_ns() - self.start_time

    @elapsed_time.setter # ns
    def elapsed_time(self, value):
        value = value * 1000000 # ms to ns
        if self.pause_time is None:
            self.start_time = time.time_ns() - value
        else:
            self.pause_time = self.start_time + value # ?

    @property
    def elapsed_time_ms(self):
        return self.elapsed_time / 1000000

    def play(self):
        if self.pause_time:
            self.start_time = time.time_ns()

    def pause(self):
        if self.pause_time is None and self.start_time is not None:
            self.pause_time = time.time_ns()
        if self.start_time is None:
            t = time.time_ns()
            self.pause_time = t
            self.start_time = t

    def resume(self):
        if self.start_time is None:
            self.start_time = time.time_ns()
        if self.pause_time is not None:
            self.elapsed_time += time.time_ns() - self.pause_time
            self.pause_time = None

    def seek(self, time: float):
        # print(f"Seeking to {time}")
        if self.start_time is None:
            raise Exception("Cannot seek when not playing because me can't figure out the math") # sadge
        self.elapsed_time = time
        # if (self.elapsed_time - time) < 0.001:
        #     breakpoint()
        # print(f"Seeked to {self.elapsed_time}")

    def get_current_lyrics(self) -> str:
        # ns to ms
        elapsed_time = self.elapsed_time / 1000000

        if elapsed_time < self.lyrics[0]["startTime"]:
            return "..."

        for i, line in enumerate(self.lyrics):
            line_time = line["startTime"]
            lyric = line["text"]
            if elapsed_time > line_time:
                if i + 1 < len(self.lyrics):
                    next_line_time = self.lyrics[i + 1]["startTime"]
                    if elapsed_time < next_line_time:
                        return lyric
                else:
                    return lyric
        return "..."

    def get_current_lyrics_index(self) -> int:
        # ns to ms
        elapsed_time = self.elapsed_time / 1000000

        if elapsed_time < self.lyrics[0]["startTime"]:
            return -1

        for i, line in enumerate(self.lyrics):
            line_time = line["startTime"]
            if elapsed_time > line_time:
                if i + 1 < len(self.lyrics):
                    next_line_time = self.lyrics[i + 1]["startTime"]
                    if elapsed_time < next_line_time:
                        return i
                else:
                    return i
        return -1

    def get_next_lyrics_line(self) -> str:
        index = self.get_current_lyrics_index() + 1

        if index < len(self.lyrics):
            return self.lyrics[index]["text"]
        else:
            return ""
        
    def get_prev_lyrics_line(self) -> str:
        index = self.get_current_lyrics_index() - 1

        if index >= 0:
            return self.lyrics[index]["text"]
        else:
            return ""

    def get_total_duration(self) -> float:
        last_line = self.lyrics[-1]
        total_duration = last_line["startTime"]
        return total_duration

    def get_current_time(self) -> float:
        if self.start_time is None:
            return 0.0
        elif self.pause_time is not None:
            return self.elapsed_time
        else:
            return self.elapsed_time + (time.time_ns() - self.start_time)


class LyricsException(Exception):
    pass

class LyricsNotFoundException(LyricsException):
    pass

