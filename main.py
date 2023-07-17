import json
import os
import sys
import time
import math
from PyQt6 import QtGui

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from config import Config
from external.mxlrc import Musixmatch, Song
from lyrics import Lyrics
from provider.lyricsProvider import LyricsProvider
from provider.neteaseProvider import ProviderNetease
from songInfo import SongInfo
from sp import SpotifyPlayer, QtCacheHandler


import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from dotenv import load_dotenv

load_dotenv()


MAX_FONT_SIZE = 50
MAX_LINES = 3

# QThread for fetching lyrics in the background
class LyricsFetcher(QThread):
    lyrics_fetched = pyqtSignal(Lyrics)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider = ProviderNetease()

    def run(self):
        lyrics = self.provider.getLyrics()
        self.lyrics_fetched.emit(lyrics)

def linear_interpolate(a, b, t):
    return a + t * (b - a)

def cubic_interpolate(a, b, t):
    return a + t * t * (3 - 2 * t) * (b - a)

def smoothstep_interpolate(a, b, t):
    return a + t * t * (3 - 2 * t) * (b - a)

def smootherstep_interpolate(a, b, t):
    return a + t * t * t * (t * (t * 6 - 15) + 10) * (b - a)

def cosine_interpolate(a, b, t):
    t = (1 - math.cos(t * math.pi)) / 2
    return a + t * (b - a)

def hermite_interpolate(a, b, t, tension=0, bias=0):
    t2 = t * t
    t3 = t2 * t
    m0 = (b - a) * (1 + bias) * (1 - tension) / 2
    m0 += (b - a) * (1 - bias) * (1 - tension) / 2
    m1 = (b - a) * (1 + bias) * (1 - tension) / 2
    m1 += (b - a) * (1 - bias) * (1 - tension) / 2
    a0 = 2 * t3 - 3 * t2 + 1
    a1 = t3 - 2 * t2 + t
    a2 = t3 - t2
    a3 = -2 * t3 + 3 * t2
    return a0 * a + a1 * m0 + a2 * m1 + a3 * b

def interpolate(a, b, t):
    return linear_interpolate(a, b, t)

# struct WINCOMPATTRDATA
#         {
#             int nAttribute;
#             PVOID pData;
#             ULONG ulDataSize;
#         };



def set_window_blur(window):
    from blurWindow import GlobalBlur
    if window.isWindow():
        hwnd = window.winId()
        GlobalBlur(hwnd, 0xFF000000, False, True, window)
        return
    return
    from ctypes import windll, c_int, c_bool, c_ulong, POINTER, sizeof, WINFUNCTYPE, Structure, c_void_p, pointer
    if window.isWindow():
        hwnd = window.winId()
        hModule = windll.kernel32.LoadLibraryW("user32.dll")
        if hModule:
            class ACCENTPOLICY(Structure):
                _fields_ = [
                    ("nAccentState", c_int),
                    ("nFlags", c_int),
                    ("nColor", c_int),
                    ("nAnimationId", c_int)
                ]

            class WINCOMPATTRDATA(Structure):
                _fields_ = [
                    ("nAttribute", c_int),
                    ("pData",  POINTER(c_int)),
                    ("ulDataSize", c_ulong)
                ]

            SetWindowCompositionAttribute = windll.user32.SetWindowCompositionAttribute

            if SetWindowCompositionAttribute:
                policy = ACCENTPOLICY(3, 0, 0, 0)
                data = WINCOMPATTRDATA(19, pointer(policy), sizeof(policy))
                SetWindowCompositionAttribute(hwnd, data)
            windll.kernel32.FreeLibrary(hModule)


class TransparentLyricsApp(QWidget):
    config = Config()
    lyricsProvider = LyricsProvider([ProviderNetease(), Musixmatch()]) # ProviderNetease()

    def __init__(self):
        super().__init__()
        try:
            self.load_config()
            self.load_properties_from_config()
            # raise Exception("This line should not be executed")
        except Exception as e:
            # warn user about invalid config file
            QMessageBox.warning(self, "Warning", f"Invalid config file. Using default values.\nError:\n {e}", QMessageBox.StandardButton.Ok)
            self.config = Config()

        self.draggable = False
        self.resizeable = False
        self.is_transparent = True
        self.offset = QPoint()
        self.setWindowTitle("LyricsApp")

        self.current_track = None
        self.current_lyrics = None
        self.playback_status = None

        # Set up a QTimer for updating the lyrics
        self.lyrics_timer = QTimer()
        self.lyrics_timer.timeout.connect(self.update_lyrics)

        # Start the timer
        self.lyrics_timer.start(1) # (ms) 0.001 seconds

        # Set up a QTimer for updating the current track
        self.track_timer = QTimer()
        self.track_timer.timeout.connect(self.update_current_track)

        # Start the timer
        self.track_timer.start(1000) # (ms) 1 seconds
    
        self.init_ui()
        # set_window_blur(self)

        self.Spotify = SpotifyPlayer(os.getenv("SP_CLIENT_ID"), os.getenv("SP_CLIENT_SECRET"), os.getenv("SP_REDIRECT_URI"))
        self.Spotify.authenticate(cache_handler=QtCacheHandler(self))

    def init_ui(self):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        # self.effect = QGraphicsBlurEffect()
        # self.effect.setBlurRadius(10)
        # Create a QVBoxLayout for the widget
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setObjectName("LyricsAppLayout")
        self.setLayout(layout)
        self.update_transparency(0)
        
        self.setObjectName("LyricsApp")
        self.borderRadius = 50

        # set stylesheet rounded corners
        self.setStyleSheet(f"""
        #{layout.objectName()} {{
        
            background-color: rgba(77, 0, 0, 255);
            border-radius: {self.borderRadius}px;
        }}""")

    def update_transparency(self, title_bar_height=29):
        # self.hide()
        # # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # self.show()
        # return
        # print(f"Updating transparency {self.is_transparent=}")
        self.hide()
        if self.is_transparent:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)    
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTransparentForInput)

            self.move(self.pos().x(), self.pos().y() + title_bar_height)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowTransparentForInput)
            # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

            self.move(self.pos().x(), self.pos().y() - title_bar_height)

        self.show()

    def update_current_track(self):
        # Get the current track from the player
        track = None 

        # try:
        # from SwSpotify import spotify, SpotifyNotRunning, SpotifyPaused

        playback_status = self.Spotify.get_current_playing_info()
        self.playback_status = playback_status
        # current_track = spotify.get_info_windows()
        if playback_status is None:
            self.current_lyrics = None
            self.setWindowTitle("LyricsApp - No Player Connected")
            return
        current_track = playback_status.song.title, playback_status.song.album
        track = f"{current_track[0]} - {current_track[1]}"
    
        if track == self.current_track:
            if self.current_lyrics is None:
                return # we don't have lyrics
            if playback_status.is_playing and self.current_lyrics.pause_time is not None: # resume playback if it was paused
                self.current_lyrics.resume()
                self.current_lyrics.seek(playback_status.playback_time)
                return

            # if playing and lyrics are playing, seek to current playback time if off by more than .2 second
            if playback_status.is_playing and self.current_lyrics.pause_time is None and abs(self.current_lyrics.elapsed_time_ms - playback_status.playback_time) > 200:
                self.current_lyrics.resume()
                self.current_lyrics.seek(playback_status.playback_time)
                self.update()
                return
            if not playback_status.is_playing:
                self.current_lyrics.pause()
                self.current_lyrics.seek(playback_status.playback_time)
            return
        self.show_lyrics(f"Fetching lyrics")
        import time
        start_time = time.time_ns()
        # try:
        if self.fetch_lyrics(playback_status.song):
            self.current_track = track
        else:
            self.current_track = track
            self.current_lyrics = None
            return
        # except Exception as e:
        #     self.show_lyrics(f"Error: {e}")
        #     self.current_lyrics = None
        #     return

        if playback_status.is_playing:
            self.current_lyrics.resume()
            self.current_lyrics.seek(playback_status.playback_time)
        else:
            self.current_lyrics.pause()
            self.current_lyrics.seek(playback_status.playback_time)

        self.current_track = track
        window_title = f"LyricsApp - {track}"
        if self.current_lyrics:
            if self.current_lyrics.pause_time is not None:
                window_title += " (Paused)"
        self.setWindowTitle(window_title)

    def fetch_lyrics(self, song: Song):
        # Fetch lyrics for the current track
        self.current_lyrics = None

        title = song.title
        artist = song.artist

        cache_folder = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation), "LyricsApp", "lyrics-cache")
        os.makedirs(cache_folder, exist_ok=True)
        

        # Check if the lyrics are cached
        cache_path = os.path.join(cache_folder, f"{title}-{artist}.json")
        from pathvalidate import sanitize_filepath
        cache_path= sanitize_filepath(cache_path)
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                synced = json.load(f)
                self.current_lyrics = Lyrics(synced)
                print(f"got the lyrics for {title} - {artist} (cache)")
                return True

        lyrics_resp = self.lyricsProvider.getLyrics(song)
        if lyrics_resp is None:
            return False
        synced = lyrics_resp

        if synced:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(synced, f, ensure_ascii=False, indent=4)
            self.current_lyrics = Lyrics(synced)
            print("got the lyrics for ", title, " - ", artist)
            return True
        else:
            return False

    def update_lyrics(self):
        if self.current_lyrics is None:
            self.show_lyrics("No Lyrics found")
            return

        # # Animation for fading out the current lyrics
        # fade_out_animation = QPropertyAnimation(self.lyrics_label, b"opacity")
        # fade_out_animation.setStartValue(1.0)
        # fade_out_animation.setEndValue(0.0)
        # fade_out_animation.setDuration(self.animation_duration)
        # fade_out_animation.setEasingCurve(QEasingCurve.Type.InQuad)

        # # Animation for fading in the next lyrics
        # fade_in_animation = QPropertyAnimation(self.lyrics_label, b"opacity")
        # fade_in_animation.setStartValue(0.0)
        # fade_in_animation.setEndValue(1.0)
        # fade_in_animation.setDuration(self.animation_duration)
        # fade_in_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Get the current time
        current_time = QDateTime.currentDateTime()

        # lyric = self.current_lyrics.get_current_lyrics()
        # Show the updated lyrics
        self.show_lyrics("")

    def load_config(self):
        if os.path.exists(self.get_config_file_path()):
            with open(self.get_config_file_path(), "r") as file:
                config_data = json.load(file)
                self.config = Config.from_dict(config_data)
        else:
            self.config = Config()

    def get_config_file_path(self):
        appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        config_dir = os.path.join(appdata_path, "LyricsApp")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "config.json")

    def save_config(self):
        import tempfile
        tmp = tempfile.NamedTemporaryFile("w", delete=False)
        json.dump(self.config.to_dict(), tmp)
        tmp.close()
        os.replace(tmp.name, self.get_config_file_path())

    def load_properties_from_config(self):
        config = self.config
        screen_geometry = QGuiApplication.primaryScreen().size()
        # print(f"{screen_geometry=}")
        # print(config.w_location_x, config.w_location_y)
        self.move(min(screen_geometry.width()-200, config.w_location_x), min(screen_geometry.height()-200, config.w_location_y))
        # print(f"{self.pos()=}")
        self.resize(config.w_width, config.w_height)

    def show_lyrics(self, lyrics_text):
        self.update()

    def drawText(self, painter: QPainter, rect: QRectF, text):
        font_temp = QFont(painter.font()) # consistent font size for all lines
        font_temp.setPointSize(self.config.font_size)
        font_temp.setBold(True)
        metrics = QtGui.QFontMetricsF(font_temp)
        space = metrics.horizontalAdvance(" ")
        width = rect.width()

        metrics2 = QtGui.QFontMetricsF(painter.font()) # why do we have two metrics?
        # has something to do with text wrappping

        # fix line
        def fixLine(line):
            # replace invisible space with space
            line = line.replace("\xa0", " ")
            
            return line
        
        text = fixLine(text)

        def lineWidth(line):
            return sum([word[1] for word in line]) + space * (len(line) - 1)

        def canFit(line, word):
            return lineWidth(line + [word]) < width

        def forceSplit(word):
            charSize = [metrics.horizontalAdvance(c) for c in word[0]]
            for i in reversed(range(1,len(charSize))):
                if sum(charSize[:i]) < width:
                    return [(word, metrics.horizontalAdvance(word)) for word in [word[0][:i], word[0][i:]]]

        queue = [(word, metrics.horizontalAdvance(word), metrics2.horizontalAdvance(word)) for word in text.split(" ")]
        lines = []
        line = []

        while len(queue) > 0:
            word = queue.pop(0)
            if canFit(line, word):
                line.append(word)
            else:
                if len(line) == 0:
                    word1, word2 = forceSplit(word)
                    line.append(word1)
                    lines.append(line)
                    line = []
                    queue.insert(0, word2)
                else:
                    lines.append(line)
                    line = []
                    queue.insert(0, word)

        if len(line) > 0:
            lines.append(line)
            line = []


        painter.save()

        painter.setClipRect(rect)

        space = metrics2.horizontalAdvance(" ")

        def lineWidth2(line):
            return sum([word[2] for word in line]) + space * (len(line) - 1)
        
        
        # get center position
        x = rect.x() + (rect.width() - lineWidth2(lines[0])) / 2
        y = rect.y() + metrics2.height()

        for line in lines:
            x = rect.x() + (rect.width() - lineWidth2(line)) / 2 
            text = " ".join([word[0] for word in line])
            # draw rectange for debug
            # draw gradient behind text

            brush, pen = painter.brush(), painter.pen()
            gradient = QLinearGradient(x, y - metrics2.height(), x, y)
            gradient.setColorAt(0, QColor(0, 0, 0, 20))
            gradient.setColorAt(1, QColor(0, 0, 0, 50))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)

            # painter.drawRect(x, y - metrics2.height(), lineWidth2(line), metrics2.height())
            painter.drawRoundedRect(int(x - x*.08), int(y - metrics2.height()+metrics2.descent()), int(lineWidth2(line) + 2 * (x*.08)), int(metrics2.height()), 5, 5)

            painter.setBrush(brush)
            painter.setPen(pen)

            painter.drawText(int(x), int(y), text)
            y += metrics.leading() + metrics.height()

        painter.restore()
        return y

    @property
    def line_changed(self):
        return self.checkpoint_lyric != self.current_lyrics.get_current_lyrics()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle
        # rect_path = QPainterPath()
        # rect_path.addRoundedRect(QRectF(self.rect()), 10, 10)
        # painter.fillPath(rect_path, QColor(0, 0, 0, 0))

        # Set the lyrics text color
        painter.setPen(QColor(255, 255, 255))

        # Set the lyrics text font
        font = QFont()
        font.setPointSize(self.config.font_size)
        font.setBold(True)
        painter.setFont(font)

        # Calculate the lyrics text position
        text_height = self.fontMetrics().height()
        text_rect = QRectF(self.rect().adjusted(10, 10, -10, -10))

        # Draw the lyrics text
        self.checkpoint_lyric = getattr(self, "checkpoint_lyric", None)
        self.reset_timer = getattr(self, "reset_timer", True)
        self.transition_timer = getattr(self, "transition_timer", None)
        if self.current_lyrics is not None:
            current_lyric = self.current_lyrics.get_current_lyrics()
            next_lyric = self.current_lyrics.get_next_lyrics_line()
            if self.checkpoint_lyric is None:
                self.checkpoint_lyric = current_lyric

            if self.line_changed:
                self.reset_timer = True
                self.checkpoint_lyric = current_lyric

            if self.reset_timer:
                self.transition_timer = time.time_ns()/1e9 # ms
                self.reset_timer = False

            if self.transition_timer is None: # no transition
                y_offset = self.drawText(painter, text_rect, current_lyric)
                text_rect.adjust(0, int(y_offset), 0, 0)
                font.setPointSize(int(self.config.font_size//1.2))
                painter.setFont(font)
                painter.setPen(QColor(150, 150, 150, 200))
                if self.current_lyrics.pause_time is not None:
                    t_font = QFont(font)
                    t_font.setPointSize(int(self.config.font_size//1.5))
                    t_font.setItalic(True)
                    painter.setFont(t_font)
                    self.drawText(painter, text_rect, "Paused")
                    painter.setFont(font)
                else:
                    self.drawText(painter, text_rect, next_lyric)
            else: # transition
                transition_progress = min((time.time_ns()/1e9 - self.transition_timer) / .3, 1)

                new_rect = QRectF(text_rect)
                offset = -interpolate(1, 500, transition_progress)
                new_rect.adjust(0.0, offset, 0.0, 0.0)
                y_offset = self.drawText(painter, new_rect, self.current_lyrics.get_prev_lyrics_line()) # launch it to heaven

                font.setPointSizeF(interpolate(self.config.font_size/1.2, self.config.font_size, transition_progress))
                painter.setFont(font)
                painter.setPen(QColor(int(interpolate(150, 255, transition_progress)), int(interpolate(150, 255, transition_progress)), int(interpolate(150, 255, transition_progress)), int(interpolate(200, 255, transition_progress))))

                text_rect.adjust(0.0, interpolate(y_offset-offset, 0.0, transition_progress), 0.0, 0.0)
                self.drawText(painter, text_rect, self.current_lyrics.get_current_lyrics()) # 2nd line to first
                if transition_progress >= 1:
                    # print("End Transition")
                    self.transition_timer = None
                    self.checkpoint_lyric = current_lyric # update checkpoint
                    self.reset_timer = False
                    font.setPointSize(self.config.font_size)
                    painter.setFont(font)
                    painter.setPen(QColor(255, 255, 255))
                self.update()
            # painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, self.current_lyrics.get_current_lyrics())
        else:
            y_offset = self.drawText(painter, text_rect, "No Lyrics found")
            text_rect.adjust(0, int(y_offset), 0, 0)
            t_font = QFont(font)
            t_font.setPointSize(int(self.config.font_size//2))
            t_font.setItalic(True)
            painter.setFont(t_font)
            self.drawText(painter, text_rect, "▶ " + self.current_track if self.current_track else "No Track Playing")
            painter.setFont(font)
            # painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "No Lyrics found")

        painter.end()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.draggable = True
            self.offset = event.pos()
        # elif event.pos().y() >= self.height() - 10 and event.pos().x() >= self.width() - 10:
        #         self.resizeable = True
        #         self.offset = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.draggable:
            self.move(self.mapToParent(event.pos() - self.offset))

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.draggable = False
            # self.resizeable = False
            self.save_config()

    def keyPressEvent(self, event: QKeyEvent):
        # print(event.key(), event.text(), event.modifiers())
        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Minus:
                self.decrease_font_size()
                event.accept()
            elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
                self.increase_font_size()
                event.accept()
            # disable transparency with ctrl+t
            if event.key() == Qt.Key.Key_T:
                self.is_transparent = not self.is_transparent
                self.update_transparency()
                event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.save_config()
            self.close()
            event.accept()

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.config.w_width = self.width()
        self.config.w_height = self.height()
        a0.accept()
        self.save_config()
        return super().resizeEvent(a0)
    
    def moveEvent(self, event: QMoveEvent) -> None:
        self.config.w_location_x = self.pos().x()
        self.config.w_location_y = self.pos().y()
        event.accept()
        self.save_config()
        return super().moveEvent(event)

    def increase_font_size(self):
        self.config.font_size += 1
        self.save_config()

    def decrease_font_size(self):
        if self.config.font_size > 5:
            self.config.font_size -= 1
            self.save_config()

if __name__ == '__main__':
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    app = QApplication(sys.argv)

    transparent_lyrics_app = TransparentLyricsApp()
    transparent_lyrics_app.show_lyrics("No Lyrics Found")

    sys.exit(app.exec())
