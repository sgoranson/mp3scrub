'''Module to use google to fix spelling in artist names.

    This is risky, but it works surprisingly well. You do a query for 'artistname wiki',
    and 90% of the time the first hit will be the wikipedia page for that artist with 
    perfect spelling. Of course you need to validate that it's the page you think it is,
    but if it's not, you just move on and let musicbrainz take care of the track instead.

    Why not use last.fm? because it just doesn't work that well for spelling mistakes. e.g.
    go to last.fm, type in 'ozzy osborne', and observe the poor results.
'''
 
import urllib2
import simplejson
import types, sys, urllib
import re, unicodedata
from mp3scrub.util import mylog, strtool


def trav(x):
    '''debug function for json output'''
         
    if isinstance(x, types.ListType):
        ret = ''
        for i in x:
            ret += (trav(i) + ' ')
        return ret

    elif isinstance(x, types.DictType):
        ret = ''
        for k,v in x.items():
            ret += ('%s => %s\n\n' % (k, trav(v)))
        return ret

    else:
        return x

def getresp(search_str):
    '''do the low level HTTP query'''

    results = None 

    q = urllib.urlencode({'q' : search_str})

    url = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&' + q
    mylog.DBG1(9,'googURL: %s' % url)

    try:
        request = urllib2.Request(
            url, None, {'Referer': 'http://1024.us'})
        response = urllib2.urlopen(request)

        # Process the JSON string.
        results = simplejson.load(response)

        response.close()

    except urllib2.URLError:
        mylog.ERR('google query failed...possible connection down')
    
    return results

def googquery(search_str):
    '''do a query for "artist_str wiki", get back json results, and
       loop through the results till we find a legit wiki page.

       returns '' if not found, corrected artistStr if found
    '''

    ret_obj = ''
    net_error = False

    results = getresp(search_str + ' wiki')

    if results:

        resp = results.get(u'responseData')

        if resp:
            reslist = resp.get(u'results')

            if reslist:
                found = False

                for res in reslist:
                    title = res.get(u'titleNoFormatting')
                    mylog.DBG(title)

                    found = re.search('wikipedia', title, re.IGNORECASE)

                    if found:
                        trim = re.search(r'(.*?)\s+\-\s+W', title)

                        if trim:
                            ret_obj = trim.group(1)
                            ret_obj = re.sub(r'\(.*?\)', '', ret_obj).strip()
                            break
                        else:
                            mylog.ERR('no trim in wikistr %s', search_str)

                if not found:
                    mylog.ERR('no wikistr for \'%s\'' % search_str)
            else:
                mylog.ERR('no results for \'%s\'' % search_str)
        else:
            mylog.ERR('no responsedata for \'%s\'' % search_str)
    else:       
        net_error = True

    return (net_error, strtool.unescape((ret_obj)))

if __name__ == '__main__':
   werd = ''
   try:
      werd = sys.argv[1]
   except IndexError:
      print >> sys.stderr, 'usage: %s searchstr' % sys.argv[0]
      exit(1)

   res = googquery(werd)
   print res.encode('utf-8')
