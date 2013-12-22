'''
 this is a module (used as a singleton) that keeps track of the artists, albums,
 and tracks we've found so far in the mp3 collection. Keeping track of these is 
 key to the algorithm of choosing correct album names (see refineGuessCache).

 internally there are 3 global dicts. 
     ARTIST_META_CACHE: just to cache the lastfm calls for ALL artist/album/track info
     TRACK_GUESS_CACHE: 
     ALBUM_GUESS_CACHE: these two dicts keep track of the same info (the artists, albums,
                 tracks, and associated mp3 path names). I use 2 dicts because it
                 makes the refineGuessCache algorithm much easier. 
'''

import sys, pickle, os

from mp3scrub.util import strtool, mylog
from mp3scrub import globalz
from mp3scrub.util.musicTypes import Artist, Album, Track
from mp3scrub.netquery import lastfmquery, googquery

# track_cache['artist_name']['mp3Path'] = (Track obj)
TRACK_GUESS_CACHE = {}

# album_cache['artist_name']['albumName'] = Album obj
ALBUM_GUESS_CACHE = {}

# artist_cache['artist_name'] = Artist obj
ARTIST_META_CACHE = {}

# google artist lookup cache
GOOG_META_CACHE = {}


def clearCache():
   ''' reset all the cache '''    
   TRACK_GUESS_CACHE.clear()
   ALBUM_GUESS_CACHE.clear()


def _updateArtistCache(fixed_artist_str):
   ''' 
       input:   clean artist name.
       output:  ArtistObj
       details: will update the local cache so we only query lastfm once per artist.
   '''

   # load up the artist info from last.fm

   if not fixed_artist_str in ARTIST_META_CACHE:
      mylog.INFO('looking up %s metadata...' % fixed_artist_str)
      ARTIST_META_CACHE[fixed_artist_str] = lastfmquery.getAllArtistInfo(fixed_artist_str) 

   return ARTIST_META_CACHE[fixed_artist_str]


def _updateTrackGuesses(artist_name, path_name, track_obj):
   if not TRACK_GUESS_CACHE.get(artist_name):
      TRACK_GUESS_CACHE[artist_name] = {}

   if not TRACK_GUESS_CACHE[artist_name].get(path_name):
      # only using track_obj as a trackname/trackno bean
      TRACK_GUESS_CACHE[artist_name][path_name] = track_obj.copy() 
      del TRACK_GUESS_CACHE[artist_name][path_name].albums[:]

   TRACK_GUESS_CACHE[artist_name][path_name].addAlbum(track_obj.album)


def _updateAlbumGuesses(artist_name, track_obj, album_obj):
   if not ALBUM_GUESS_CACHE.get(artist_name):
      ALBUM_GUESS_CACHE[artist_name] = {}   

   if not ALBUM_GUESS_CACHE[artist_name].get(album_obj.name):
      ALBUM_GUESS_CACHE[artist_name][album_obj.name] = album_obj.copy()
      del ALBUM_GUESS_CACHE[artist_name][album_obj.name].tracks[:]

   mylog.DBG1(4,'ALGDBG: adding track \'%s\' to album \'%s\'...' % 
             (track_obj.name, album_obj.name))

   ALBUM_GUESS_CACHE[artist_name][album_obj.name].addTrack(track_obj.copy())

def getRawArtistInfo(artist_str):
   _updateArtistCache(artist_str)

   return ARTIST_META_CACHE[artist_str]

def updateGuessCache(path_str, id3_track_str, fixed_artist_str):
   ''' called once per new mp3 processed. adds all possible track/album matches to a list
       that will be further narrowed down later to one match.
   '''

   found_track = False

   # lookup the full artist/album info if haven't already
   artist_obj = _updateArtistCache(fixed_artist_str)

   # we loop through all the tracks, looking for the one with the least difference 
   # from id3_track_str. see strtool for more info
   for i,album_obj in enumerate(artist_obj.albums):

      if i > globalz.ALBUM_GUESS_LIMIT: break

      if not album_obj.name: 
         mylog.DBG('null album length for artist \'%s\' track \'%s\'' % 
                   (fixed_artist_str, id3_track_str))
         continue 

      guess_album_obj = album_obj.copy()


      # remove junky parens. see strtool for details
      clean_id3_track_str = strtool.removeTrackJunk(id3_track_str)

      best_track_matches = []

      # loop through all the track in this album, searching for the specified track
      for track_obj in album_obj.tracks:

         targ_track_str = strtool.removeTrackJunk(track_obj.name) 

         mylog.DBG1(10,'comparing mytrack_obj: \'%s\' guesstrack: \'%s\' guessalbum: \'%s\'' % 
                       (clean_id3_track_str, targ_track_str, album_obj.name))


         dist = strtool.trackCompare(clean_id3_track_str, targ_track_str)

         if dist != -1:
            mylog.DBG1(10,'track match: \'%s\' guesstrack: \'%s\' guessalbum: \'%s\'' % 
                          (clean_id3_track_str, targ_track_str, album_obj.name))

            guess_track_obj = Track(_album=album_obj.name, _name=targ_track_str, 
                                    _track_num=track_obj.track_num, _path=path_str)

            best_track_matches.append((dist, guess_track_obj))

      # if we found a match...
      if best_track_matches:
         # return the track with the least dist from id3's trackName  
         best_track_matches.sort()

         best_track_obj = best_track_matches[0][1]

         _updateTrackGuesses(artist_obj.name, path_str, best_track_obj)
         _updateAlbumGuesses(artist_obj.name, best_track_obj, guess_album_obj)

         del best_track_matches
         found_track = True

   return found_track


def refineGuessCache():
   ''' narrow down album guesses after everythings been processed.

       REFINE STEPS
       1. sort your albums from best to worst, ranked by: 
                     (%complete * %complete * albumRank * total_tracks)
      
       2. look at all your tracks from your current top album.
           a) remove all these tracks from lesser albums (cause they're a 
              worse match)
           b) add the current top album to a 'processed' list, so we don't 
              process it again
           c) since removing tracks from lesser albums will change their 
              %complete rank, resort by going back to step 1
      
       3. repeat until all albums processed
   '''
   def removeTrackElsewhere(track_obj, keep_album_str, alb_ptr, trkPtr):
      ''' helper function that keeps a track in one album but removes it everywhere else '''

      mylog.DBG1(10,'keeping %s in %s\n' % (track_obj.name, keep_album_str))

      modded = False

      if globalz.LOG_DEBUG > 8: 
         for i,alb in enumerate(alb_ptr):
            for y, trk in enumerate(alb_ptr[alb].tracks):
               mylog.DBG1(8,'albName: \'%s\' albptrTrk1 %d: \'%s\'\n' % (alb, y, unicode(trk.name)))

      # delete the current track in every album that's not here
      for del_album in alb_ptr:
         if del_album == keep_album_str: continue

         # delete track from all other albums in album cache
         for t in alb_ptr[del_album].tracks:
            if track_obj == t:
               while t in alb_ptr[del_album].tracks:
                  alb_ptr[del_album].tracks.remove(t)

            modded = True

      # delete all other albums from TRACK_GUESS_CACHE
      if keep_album_str in trkPtr[track_obj.path].albums:
         trkPtr[track_obj.path].album = keep_album_str
      else:
         del trkPtr[track_obj.path].albums[:]

      if globalz.LOG_DEBUG > 8: 
         for i,alb in enumerate(alb_ptr):
            for y, trk in enumerate(alb_ptr[alb].tracks):
               mylog.DBG1(8,'albName2: \'%s\' albptrTrk %d: \'%s\'\n' % (alb, y, unicode(trk.name)))

      return modded

   def reSortAlbums(my_albums, alb_ptr, skip_albums):
      ''' sort album list by appropriateness'''

      if my_albums: del my_albums[:]

      for album in alb_ptr:
         ptr = alb_ptr[album]
         tracks_found = len(ptr.tracks)
            
         if album in skip_albums: continue 
         if tracks_found == 0: continue

         # easiest to calculate % here
         ptr.pct_complete = float(tracks_found) / ptr.total_tracks
         ptr.pct_score = (ptr.pct_complete * ptr.pct_complete * ptr.rank * tracks_found)

         mylog.DBG1(4,'ALGDBG: artist: %s album: %s complete: %f rank: %d found: %d' %
                      (ptr.artist, ptr.name, ptr.pct_complete, ptr.rank, tracks_found))

         my_albums.append((ptr.pct_score, album))

      my_albums.sort(reverse=True)


   # iterate through the potential album list
   for artist in sorted(ALBUM_GUESS_CACHE):

      albums_ptr = ALBUM_GUESS_CACHE[artist]
      tracks_ptr = TRACK_GUESS_CACHE[artist]
    

      sort_all_albums = []

      reSortAlbums(sort_all_albums, albums_ptr, [])

      processed_albums = []

      while sort_all_albums:

         resort = False

         for _, better_album in sort_all_albums:
            if resort: break

            ptr = albums_ptr[better_album]

            for trk in ptr.tracks[:]:

               # delete the current trk in every album that's not here
               removeTrackElsewhere(trk, better_album, albums_ptr, tracks_ptr)
               processed_albums.append(better_album)
               reSortAlbums(sort_all_albums, albums_ptr, processed_albums)
               resort = True
                  

def searchGuessCache(artist_str, path_str):
   ''' given an artistname and path, see if we found a guess '''
   ret = None

   mylog.DBG1(10,'searching for artist %s and path %s\n' % (artist_str, path_str))

   # see if we found a guess Track for the mp3
   artist_obj = TRACK_GUESS_CACHE.get(artist_str)

   if artist_obj:
      ret = artist_obj.get(path_str)

      if not ret or not ret.album:
         mylog.ERR('no album found for MP3 %s\n' % (path_str))
         ret = None

   return ret


def dbgPrint(fileDes):
   def uniP(*x):
      for i in x:
         print >> fileDes, unicode(x).encode('utf-8')
   
   for artist in ARTIST_META_CACHE:
      uniP('ARTIST: ', artist)

      alb_ptr = ARTIST_META_CACHE[artist].albums

      for a in alb_ptr:
         uniP('ALBUM: {0:30} ==> {1}\n'.format('', unicode(a)))
         for t in a.tracks:
            uniP('{0:>35} {1:>30}\n'.format('TRACK:', unicode(t)))
      uniP('\n\n\n')

      uniP('TRACK INFO:')
      for trk in TRACK_GUESS_CACHE:
         for t in TRACK_GUESS_CACHE[trk]:
            uniP('{0:30} ==> {1}'.format(t, unicode(TRACK_GUESS_CACHE[trk][t])))
      uniP('\n\n\n')

      uniP('ALBUM INFO:')
      for alb in ALBUM_GUESS_CACHE:
         for a in ALBUM_GUESS_CACHE[alb]:
            #print >> fileDes, 'ALBUM: {0:30} ==> {1}\n'.format(a, str(ALBUM_GUESS_CACHE[alb][a]))
            for t in ALBUM_GUESS_CACHE[alb][a].tracks:
               uniP('{0:>35} {1:>30}\n'.format('TRACK:', unicode(t)))
      uniP('\n\n\n')

def undump():
   ''' if we've already queried artist info in the past, load it up, son! '''

   global ARTIST_META_CACHE
   global GOOG_META_CACHE

   if os.path.exists(globalz.PICKLE_FILE):
      with open(globalz.PICKLE_FILE,'rb') as fl:
         try:
            ARTIST_META_CACHE = pickle.load(fl)
            GOOG_META_CACHE = pickle.load(fl)
         except:
            mylog.ERR('error loading pickle file, continuing...')
            ARTIST_META_CACHE = {}
            GOOG_META_CACHE = {}
            os.remove(globalz.PICKLE_FILE)

def dump():
   ''' save off the artist info we've found for next time '''
   with open(globalz.PICKLE_FILE,'wb') as fl:
      pickle.dump(ARTIST_META_CACHE, fl,-1)
      pickle.dump(GOOG_META_CACHE, fl,-1)



def queryGoogCache(artist_name):
   ''' cache google queries to avoid web io '''
 
   ret_pack = GOOG_META_CACHE.get(artist_name)

   if not ret_pack: 
      mylog.DBG1(10,'GOOG_META_CACHE: not found key \'%s\'' % (artist_name))

      GOOG_META_CACHE[artist_name] = googquery.googquery(unicode(artist_name).encode('utf-8'))
      ret_pack = GOOG_META_CACHE.get(artist_name)

   else:
      mylog.DBG1(10,'GOOG_META_CACHE: found key \'%s\' val: \'%s\'' % (artist_name, unicode(ret_pack)))

   return ret_pack

####################################


if __name__ == '__main__':
   input_arg = ''
   processDir = False

   globalz.PICKLE_FILE = 'meh.pkl'

   # if we've already queried artist info in the past, load it up, son!
   undump()

   try:
      artist_str = sys.argv[1]
      track_str = sys.argv[2]
   except IndexError:
      print 'usage: %s artist_name track1, track2, track3' % sys.argv[0]
      exit(1)

   
   (net_error, real_artist_str) = queryGoogCache(artist_str)

   if net_error:
      print 'net connection failure'
      exit(1)

   tracks = track_str.split(',')
   for (i, track) in enumerate(tracks):
      updateGuessCache('%s%d' % (track, i), track, real_artist_str)


   refineGuessCache()
   dbgPrint(sys.stdout)

   # save off the artist info we've found for next time
   dump()
