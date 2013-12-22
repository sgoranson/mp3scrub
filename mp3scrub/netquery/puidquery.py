'''Wrappers for musicbrainz secret PUID generator and looker-upper'''

from musicbrainz2.webservice import Query, TrackFilter, RequestError, WebServiceError
import musicdns, musicdns.cache
import sys, os, time
from mp3scrub import globalz
from mp3scrub.util import mylog 

class PUIDQuery():
     
    def __init__(self):
        musicdns.initialize()
        self.cache = musicdns.cache.MusicDNSCache()
        self.query = Query()

    def getPUID(self,mp3fn):
        ''' hash generator '''

        try:
            puid, _ = self.cache.getpuid(mp3fn.encode('utf-8'), globalz.MUSICDNS_KEY)

        except IOError as e:
            mylog.ERR('couldnt get puid for: %s reason: %s' % (mp3fn, e.message))
            puid = ''

        except TypeError as e:
            mylog.ERR('couldnt get puid for: %s reason: %s' % (mp3fn, e.message))
            puid = ''

        finally:
            return puid 

    def lookupPUID(self,puid):
        ''' after generating puid, attempt to look it up online '''

        (artistStr, albumStr, trackStr, trackNum) = ('','','', -1)

        if not puid:
            mylog.ERR('null puid')
            return (artistStr, albumStr, trackStr, trackNum)

        try:
            # limit 1 query per second according to doc
            time.sleep(1)
            filter = TrackFilter(puid=puid)
            results = self.query.getTracks(filter)

        except RequestError: 
            mylog.ERR('400 error on puid %s' % puid)
            return (artistStr, albumStr, trackStr, trackNum)

        except WebServiceError: 
            mylog.ERR('503 error on puid %s' % puid)
            return (artistStr, albumStr, trackStr, trackNum)

        except: 
            mylog.ERR('uknown query error on puid %s' % puid)
            return (artistStr, albumStr, trackStr, trackNum)

        if results:
            # return best match
            artistStr = results[0].getTrack().getArtist().getName()
            trackStr = results[0].getTrack().getTitle()
            albums = results[0].getTrack().getReleases()

            if albums:
                albumStr = albums[0].getTitle()
                trackNum = albums[0].getTracksOffset()

        mylog.DBG1(10,'puid return \'%s\' \'%s\' \'%s\' \'%s\'' % 
                      (artistStr, albumStr, trackStr, trackNum))

        return (artistStr, albumStr, trackStr, trackNum)

    def lookupTrack(self,mp3fn):
        ''' gen and lookup in one swell function '''
   
        puid = self.getPUID(mp3fn)
        return self.lookupPUID(puid) 
       
if __name__ == '__main__':

    try:
        listfn = sys.argv[1]
        filez = listfn.split(',') 
    except IndexError:
        print 'please specify argv[1]'
        exit()

    lookupObj = PUIDQuery()

    for fn in filez:
        (artistStr, albumStr, trackStr, trackNum) = lookupObj.lookupTrack(fn)
        print ' '.join((artistStr, albumStr, trackStr, str(trackNum)))
