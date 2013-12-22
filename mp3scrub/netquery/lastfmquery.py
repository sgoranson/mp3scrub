'''
   functions to request artist metadata from last.fm and parse the xml output.

   1. artistSearch - to get a likely artist name string given your artist string
   2. getArtistsAlbums - given string returned from #1, list of popular albums
   3. getAlbumDetails - given album_mbid #2, list of likely last.fm IDs
   4. getAlbumTracks - given id from #3, returns tracks 
'''

import urllib, urllib2, httplib, sys
from xml.dom.minidom import parseString 
import time
from mp3scrub import globalz
from mp3scrub.util.musicTypes import Artist, Album, Track
from mp3scrub.util import mylog, findxml


class XMLTAG:
   ALBUMNAME = 'name'
   ALBUMNODE = 'album'
   ALBUMARTIST = 'artist'
   ARTIST = 'artist'
   ARTISTNAME = 'name'
   TRACKNAME = 'title'
   TRACKNODE = 'track'
   TRACKLIST = 'trackList'
   ALBUMID = 'id'
   ALBUMMBID = 'mbid'
   ALBUMRANK = 'playcount'
  

def genericQuery(url):
    ''' low level HTTP request to last.fm. retries a few if failure.

        returns XML obj if ok, None if not 
    '''

    key = urllib.urlencode({'api_key' : globalz.API_KEY})
    url += ('&' + key)
    request = urllib2.Request(url, None, {'User-Agent': 'http://1024.us'})

    attempt = 1
    ret_str = ''
    dom_obj = None

    # don't hammer the site
    time.sleep(.1)
    
    while True:

        if attempt == 4: 
            mylog.ERR('MAX http error on \'%s\' returning None...' % url)   
            return None            

        mylog.DBG1(4,'url: %s attempt: %d' % (url, attempt))

        try:
            response = urllib2.urlopen(request)
            ret_str = response.read()
            response.close()
            break

        except (urllib2.HTTPError, httplib.BadStatusLine, urllib2.URLError): 
            mylog.ERR('http error on \'%s\', retrying...' % url)   
            attempt += 1
            time.sleep(2)

   
    try:
        my_dom = parseString(ret_str)
    except:
        mylog.ERR('xml dom error on \'%s\'. returning None' % url)   
        my_dom = None
  
    return my_dom 

def getAllArtistInfo(fixed_artist_str):
   ''' given a corrected artist name via prior api call (preferbly google), returns struct below 

       returns:

          ArtistObj
             AlbumObj1
                TrackObj1
                TrackObj2
                TrackObj3
             AlbumObj2
'''
   artist_obj = Artist()

   artist_hits = artistSearch(fixed_artist_str)

   if artist_hits:
      artist_obj.name = artist_hits[0]
   else:
      mylog.ERR('lastfm artist lookup for %s not found' % fixed_artist_str)
      return artist_obj


   ''' returns list of most popular [album_mbid] '''
   mbid_list = getArtistsAlbums(artist_obj.name)

   ''' get the details for each top album '''
   for album_mbid in mbid_list:
      mylog.DBG("getAllArtistInfo: searching for album mbid %s" % (album_mbid))
      mbid_matches = []

      try:
         mbid_matches = getAlbumDetails(album_mbid)
      except urllib2.HTTPError:
         mylog.ERR('HTTP err. cannot find album match for MBID %s' % (album_mbid))
         continue

      ''' annoying RESTfulness, gotta GET 234432 resources to find the track details needed '''
      for maybe_album in mbid_matches:

         mylog.DBG("getAllArtistInfo: potential album %s" % (maybe_album))
         artist_name = maybe_album.get('artist')
         album_str = maybe_album.get('name')
         album_id = maybe_album.get('id')
         album_rank = maybe_album.get('rank')

         album_obj = Album(artist_obj.name, album_str, album_id, album_rank)

         if album_str and album_id: 

            tracks = getAlbumTracks(album_id)

            for track in tracks:
               track_obj = Track(_album=album_str, _name=track[0], _track_num=track[1])
               album_obj.addTrack(track_obj) 
               album_obj.total_tracks += 1

            artist_obj.addAlbum(album_obj)
            break

   return artist_obj

def getAlbumDetails(album_mbid):
    ''' given an album mbid, returns a list of potential album_id matches. 
        it will be in a { artist, id, name } dict because you still need to verify
        it belongs to the expected artist.
    '''

    album_mbid_url = urllib.urlencode({'mbid' : album_mbid})
    url = 'http://ws.audioscrobbler.com/2.0/?method=album.getinfo&' + album_mbid_url
    my_dom = genericQuery(url)

    if not my_dom: 
        mylog.ERR('bad DOM for %s' % album_mbid_url)
        return []

    album_nodes = my_dom.getElementsByTagName(XMLTAG.ALBUMNODE)
    album_strs = []

    hits = 0
    for album_node in album_nodes:
        if hits == globalz.MAX_POTENTIAL_ALBUM_MATCH: break
        hits += 1

        album_info = {'artist' : '', 'id' : '', 'name' : ''}
        album_info['artist'] = findxml.safeChildGet(album_node, XMLTAG.ALBUMARTIST)
        album_info['id'] = findxml.safeChildGet(album_node, XMLTAG.ALBUMID)
        album_info['name'] = findxml.safeChildGet(album_node, XMLTAG.ALBUMNAME)
        album_info['rank'] = findxml.safeChildGet(album_node, XMLTAG.ALBUMRANK)
        mylog.DBG1(4, "getAlbumDetails: for album %s appending potential name %s" % 
                  (album_mbid, album_info.get('name')))

        album_strs.append(album_info)

    del my_dom

    return album_strs

def getAlbumTracks(album_id):
    ''' given an album number, returns the track listing for that album.
        album numbers are obtained from getAlbumDetails. 
    '''

    url = 'http://ws.audioscrobbler.com/2.0/?method=playlist.fetch&playlistURL=lastfm://playlist/album/' + album_id

    my_dom = genericQuery(url)
    if not my_dom: 
        mylog.ERR('bad DOM for %s' % album_id)
        return []

    tracks = []

    track_root = my_dom.getElementsByTagName(XMLTAG.TRACKLIST) 

    if track_root:
        track_nodes = track_root[0].getElementsByTagName(XMLTAG.TRACKNODE) 
        track_num = 1
        for track_node in track_nodes:
            track_str = findxml.safeChildGet(track_node, XMLTAG.TRACKNAME)

            mylog.DBG("getAlbumTracks: appending track %s number: %s" % (track_str, str(track_num)))
            tracks.append((track_str, track_num))
            track_num += 1

        del my_dom

    return tracks

def artistSearch(artist_str):
    ''' given an atrist name, returns likely name matches '''

    artist_url = urllib.urlencode({'artist' : artist_str.encode('utf-8')})


    url = 'http://ws.audioscrobbler.com/2.0/?method=artist.search&' + artist_url

    my_dom = genericQuery(url)
    if not my_dom: 
        mylog.ERR('bad DOM for %s' % artist_str)
        return []

    artist_nodes = my_dom.getElementsByTagName(XMLTAG.ARTIST)
    artist_names = []

    for artist_node in artist_nodes:
        fixed_artist_str = findxml.safeChildGet(artist_node, XMLTAG.ARTISTNAME)
        if fixed_artist_str:
            artist_names.append(fixed_artist_str)

    del my_dom

    return artist_names

def getArtistsAlbums(artist_str):
    ''' given an artist name, returns strings of popular albums with their MBIDs '''

    artist_url = urllib.urlencode({'artist' : artist_str.encode('utf-8')})

    url = unicode(u'http://ws.audioscrobbler.com/2.0/?method=artist.gettopalbums&' + artist_url).encode('utf-8')

    my_dom = genericQuery(url)
    if not my_dom: 
        mylog.ERR('bad DOM for %s' % artist_str)
        return []

    album_mbids = []

    album_nodes = my_dom.getElementsByTagName(XMLTAG.ALBUMNODE)

    hits = 0
    for album_node in album_nodes:
        if hits == globalz.MAX_ALBUM_MATCH: break
        hits += 1

        mbid = findxml.safeChildGet(album_node, XMLTAG.ALBUMMBID)
        if mbid:
            mylog.DBG("getArtistsAlbums: for artist %s appending album mbid %s" % (artist_str, mbid))
            album_mbids.append(mbid)

    del my_dom

    return album_mbids


def printEach(x):
    for y in x:
       print '[ ',
       for z in y:
           print z.encode('utf-8'), ' ',
       print ']\n\n\n'

if __name__ == '__main__':
   werd = ''
   try:
      werd = sys.argv[2]
      type = sys.argv[1]
   except IndexError:
      sys.exit('usage: %s [ARTISTALBUMS|ALBUM|ARTIST|TRACKS|ALL] artist_str' % sys.argv[0])

   if type == 'ARTISTALBUMS':
      printEach(getArtistsAlbums(werd))
   elif type == 'ARTIST':
      printEach(artistSearch(werd))
   elif type == 'TRACKS':
      printEach(getAlbumTracks(werd))
   elif type == 'ALBUM':
      printEach(getAlbumDetails(werd))
   elif type == 'ALL':
      all = getAllArtistInfo(werd)
      print all
   else:
      sys.exit('usage: %s [ARTISTALBUMS|ALBUM|ARTIST|TRACKS|ALL] artist_str' % sys.argv[0])

