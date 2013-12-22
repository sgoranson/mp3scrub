'''classes to encapsulate music objects. Used to cache last.fm results, used
   in the tagging algorithm, and used to persist tag edits. i.e. everywhere :)
 


    Artist [name] 
        has a list of:

        Album [name, mbid, rank, total_tracks]
            has a list of:

            Track [ name, track_num ]  



    MP3File [path]
        Track #respresents the file b4 tag cleaning
        Track #respresents the file after tag cleaning
'''

from mp3scrub import globalz
from mp3scrub.util import mylog

class Artist(object):
    '''Artist metadata. has a list of albums.'''

    def __init__(self):
        self.name = None
        self.albums = []

    def addAlbum(self, album_obj):
        self.albums.append(album_obj)

    def __eq__(self, other):
        if self.name == other.name:
            return True
        else:
            return False

    def __unicode__(self):
        header_str = u'ARTIST: \'%s\'' % self.name

        album_strs = [ unicode(x) for x in self.albums ]
        album_strs = u'\n'.join(album_strs)
        album_strs = album_strs.replace('\n','\n' + ' '*5)
        album_str = u'ALBUMS: \n' + ' '*5 + album_strs

        return header_str + '\n' + album_str

       
class Album(object):
    '''album metadata. has a list of Tracks.''' 

    def __init__(self, _artist=None, _name=None, _mbid=None, _rank=0, _total_tracks=0):
        self.tracks = []
        self.name = _name
        self.artist = _artist 
        self.mbid = _mbid
        self.total_tracks = _total_tracks
        self.rank = _rank

    def setTotalTracks(self, arg):
        # allow throw on bad input, needs to be an int
        self._total_tracks = int(arg)

    def getTotalTracks(self):
        return self._total_tracks

    total_tracks = property(getTotalTracks, setTotalTracks)

    def __eq__(self, other):
        if self.name == other.name:
            return True
        else:
            return False

    def copy(self):
        trk_copy = []
        for t in self.tracks:
            trk_copy.append(t.copy())

        album_copy = Album(self.artist, self.name, self.mbid, self.rank, self.total_tracks)
        album_copy.tracks = trk_copy

        return album_copy

    def setRank(self, arg):
        # allow throw on bad input, needs to be an int
        try:
            self._rank = int(arg)
        except ValueError:
            mylog.INFO('invalid rank: arg: %s' % (arg))
            self._rank = 1


    def getRank(self):
        return self._rank

    rank = property(getRank, setRank)


    def addTrack(self, track_obj):
        self.tracks.append(track_obj)

    def __unicode__(self):
        header_str = (u'name: \'%s\' mbid: %s rank: %d total_tracks: %d' % 
                    (self.name, self.mbid, self.rank, self.total_tracks))
     
        #trackStrs = [ ' '*5 + str(x) for x in self.tracks ]
        #trackStr = "TRACKS: \n" + '\n'.join(trackStrs)
        #return header_str + '\n' + trackStr
        return header_str 
        


class Track(object):
    '''Track metadata.'''
     
    def __init__(self, _artist='', _album=None, _name='', _track_num='', _path=''):

        self.artist = unicode(_artist)
        self.name = unicode(_name)
        self.albums = []
        self.album = unicode(_album) if _album else None
        self.path =  unicode(_path) 
        self._track_num_int = _track_num if _track_num else -1

    def setTrackNum(self, arg):
        # allow throw on bad input, needs to be an int
        if not arg: arg = -1 

        try:
            self._track_num_int = int(arg)
        except ValueError:
            mylog.INFO('invalid track#: %s path: %s' % (arg, self.path))
            self._track_num_int = arg

       
    def getTrackNum(self):
        return self._track_num_int

    track_num = property(getTrackNum, setTrackNum)

    def __eq__(self, other):
        # names can have minor differences; use 1 Track per 1 MP3 file
        if self.path == other.path:
            return True
        else:
            return False

    # you can use self.album as a single definite album name, or 
    # self.albums as a list of potential album names
    def setAlbum(self, album_str):
        del self.albums[:]
        sarg = unicode(album_str)
        self.albums.append(sarg)

    def getAlbum(self):
        if self.albums:
            return self.albums[0]
        else:
            return None

    album = property(getAlbum, setAlbum)

    def copy(self):
        trk = Track(_artist=self.artist, _name=self.name, _track_num=self.track_num, _path=self.path)

        trk.albums = self.albums[:]
        return trk

    def addAlbum(self, album_str):
        sarg = unicode(album_str)
        self.albums.append(sarg)

    def __unicode__(self):
        album_strs = [ u'\'%s\'' % unicode(x) for x in self.albums ]
        album_str = u' albums: ' + u' '.join(album_strs)
        prefix = u'name: \'%s\' trackno: %s' % (self.name, self.track_num)
        prefix += album_str
        return prefix


 
class MP3File(object):
    '''MP3File is used in tracking the tag changes to an mp3 file, before and after
    a tag has been changed. It has 2 Track objects: track before changes, and track
    after changes.'''
     
    @staticmethod
    def getFieldLabels():
        '''used by the grid in the gui for labelling'''

        ret = ('OriginalArtist', 'CleanArtist', 'OriginalAlbum', 
               'CleanAlbum', 'OriginalTrack', 'CleanTrack', 'OriginalTrackNum',
               'CleanTrackNum', 'Path', 'Method1', 'Method2', 'FieldsChanged', 'Result')
        return ret

    class QRY_RESULT:
        '''why was a guess not made?'''

        UNKNOWN = 'unknown'
        ARTIST_NOT_FOUND = 'artist not found'
        ARTIST_BAD_MATCH = 'artist bad match'
        TRACK_NOT_FOUND = 'track not found'
        NO_CHANGE = 'nothing changed'
        FIELDS_CHANGED = 'fields changed'
        NET_ERROR = 'network error'
        NO_GUESS = 'id attempts failed'
        OK = 'success'

    class METHOD:
        '''how did we determine a guess?'''

        UNKNOWN = 'unknown'
        HASHED = 'musicbrainz'
        ID3ID = 'lastfm'
        FAILEDHASH = 'badmusicbrainz'
        SECONDPASSFAIL = 'secondpassfail'

    def __init__(self, orig_track=None, clean_track=None, result=QRY_RESULT.UNKNOWN, 
                       fields_changed=0, method=METHOD.UNKNOWN, is_dup_flag=False,
                       my_path=''):
     
        self.orig_track = orig_track.copy() if orig_track else Track()
        self.clean_track = clean_track.copy() if clean_track else Track()

        self.result = result
        self.fields_changed = fields_changed
        self.method1 = method
        self.method2 = method
        self.is_dup = is_dup_flag
        self.orig_track.path = my_path

    def __unicode__(self):
        ret = 'OLD: ' + unicode(self.orig_track) + '\n'
        ret += 'NEW: ' + unicode(self.clean_track) + '\n'
        return ret

    def getFieldList(self):
        ret = (self.orig_track.artist, self.clean_track.artist, 
               self.orig_track.album, self.clean_track.album, self.orig_track.name,
               self.clean_track.name, self.orig_track.track_num, self.clean_track.track_num,
               self.orig_track.path, self.method1, self.method2, self.fields_changed, self.result) 
        return ret

    fieldList = property(getFieldList)


    def updateResults(self):
        '''internal code used to track what fields have changed pre and post tag changes.

        bitfields:
         artist changed: 1 
         album changed: 2 
         title changed: 4 
         track_num changed: 8
        '''

        ret = 0

        if self.orig_track.artist.lower() != self.clean_track.artist.lower():
            ret |= 1

        if self.orig_track.album.lower() != self.clean_track.album.lower():
            ret |= 2

        if self.orig_track.name.lower() != self.clean_track.name.lower():
            ret |= 4

        if self.orig_track.track_num != self.clean_track.track_num:
            ret |= 8

        self.fields_changed = ret

        if ret:
            self.result = MP3File.QRY_RESULT.FIELDS_CHANGED
        else:
            self.result = MP3File.QRY_RESULT.NO_CHANGE

