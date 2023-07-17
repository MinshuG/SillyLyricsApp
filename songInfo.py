
class SongInfo:
  def __init__(self, title, artist, album, duration, uri):
    self.title = title
    self.artist = artist
    self.album = album
    self.duration = duration
    self.uri = uri

  def __repr__(self):
    return f"{self.title} - {self.artist} - {self.album} - {self.duration} - {self.uri}"

  def __eq__(self, other):
    if isinstance(other, SongInfo):
      return self.title == other.title and self.artist == other.artist and self.album == other.album and self.duration == other.duration and self.uri == other.uri
    return False

  def __hash__(self):
    return hash((self.title, self.artist, self.album, self.duration, self.uri))

