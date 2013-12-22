'''you have two ways to guess a file's identity: hash it and use musicbrainz, or
   use the existing tags and try to guess at what they were trying to mean.

    a few kinds of string functions for parsing XML back from last.fm, id3 tags,
    string distances, hueristics for fuzzy tag matching, etc... 
'''

import re, htmlentitydefs 
import sys
import unicodedata
from mp3scrub import globalz
from mp3scrub.util import mylog

def safeUni(uni_str):
    return unicodedata.normalize('NFKD', unicode(uni_str)).encode('ascii','ignore')

def unescape(text):
    ''' Removes HTML or XML character references and entities from a text string.
    source: http://effbot.org/zone/re-sub.htm
    '''
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is

    return re.sub("&#?\w+;", fixup, text)


def trackCompare(my_str, real_str):
    ''' the idea is to find the best matching track, not just the first match.
    so this will return the stddist on a potential match, or -1 on no match
    '''

    clean_my_str = sanitizeTrackStr(my_str)
    clean_real_str = sanitizeTrackStr(real_str)

    dist = strDist(clean_my_str, clean_real_str)

    mylog.DBG1(10,'comparing clean track %s to %s: dist: %d' % (clean_my_str, clean_real_str, dist))

    # for longer strings, we allow more mistakes, up to MAX_STR_DIST
    if dist < globalz.MAX_STR_DIST and dist <= int(len(clean_my_str)/globalz.DIV_STR_DIST):
        return dist
    else:
        return -1 

def getAlbumType(album_str):
    ''' rough guess on albumType: 'live', 'hits', 'normal' '''

    typ = 'normal'
   
    if re.search(r'\d\d\d\d-\d\d-\d\d', album_str): typ = 'live' 
    if re.search(r'\d\d-\d\d-\d\d\d\d', album_str): typ = 'live'
    if re.search(r'\d\d-\d\d-\d\d', album_str): typ = 'live' 
    if re.search('live', album_str, re.IGNORECASE): typ = 'live' 
    # skip over greatest hits and remixes
    if re.search('hits', album_str, re.IGNORECASE): typ = 'hits' 
    if re.search('greatest', album_str, re.IGNORECASE): typ = 'hits' 
    if re.search('best of', album_str, re.IGNORECASE): typ = 'hits' 
    if re.search('singles', album_str, re.IGNORECASE): typ = 'hits' 
    if re.search('soundtrack', album_str, re.IGNORECASE): typ = 'hits' 

    return typ


def artistCompare(my_str, real_str):
    '''loose artist matching'''
 
    matched = False

    clean_my_str = sanitizeArtistStr(my_str)
    clean_real_str = sanitizeArtistStr(real_str)

    # we get alot of compares like 'bach' | 'johann sebastian bach'
    # so if our string is found at the very end of the real string, use it
    # kind of risky, but lastfm query will catch any screw ups
    matchx = re.search(clean_my_str, clean_real_str)
    if matchx:
        (substr_start, substr_end) = matchx.span(0)
        if substr_end == len(clean_real_str):
            matched = True

    else:
        # see how good the guess is
        dist = strDist(clean_my_str, clean_real_str)

        # for longer strings, we allow more mistakes, up to MAX_STR_DIST
        if dist < globalz.MAX_STR_DIST and dist <= int(len(clean_my_str)/globalz.DIV_STR_DIST):
            matched = True

    return matched


def removeTrackJunk(a):
    '''
       track names often include stuff we just don't care about...
       e.g. kill the parens here:
       Smells Like Teen Spirit (album version)
       Rape Me (explicit)
    '''

    expl = re.compile(r'\(.*explicit.*\)', re.IGNORECASE)
    alt = re.compile(r'\(.*alternate.*\)', re.IGNORECASE)
    live = re.compile(r'\(.*live.*\)', re.IGNORECASE)
    mix = re.compile(r'\(.*mix.*\)', re.IGNORECASE)
    vers = re.compile(r'\(.*version.*\)', re.IGNORECASE)
    remaster = re.compile(r'\(.*remaster.*\)', re.IGNORECASE)
    feat = re.compile(r'\(.*ft*\)', re.IGNORECASE)
    edit = re.compile(r'\(.*edit.*\)', re.IGNORECASE)

    ret = re.sub(expl,'', a)
    ret = re.sub(remaster,'', ret)
    ret = re.sub(edit,'', ret)

    # SPG 5/7/2010 playing with heuristics...
    #if not alt.search(ret) and not live.search(ret):
    #   ret = re.sub(vers,'', ret)
    ret = re.sub(live,'', ret)
    ret = re.sub(alt,'', ret)
    ret = re.sub(vers,'', ret)
    ret = re.sub(feat,'', ret)
    ret = re.sub(mix,'', ret)
    ret = re.sub('\(\)','', ret)
    return ret.strip()

def sanitizeTrackStr(a):
    '''for track comparision, we don't want to consider things like capitalization'''

    ret = a.lower()
    ret = ret.replace(' ','')
    return ret

def sanitizeArtistStr(a):
    ''' for artist comparision, we don't want to consider things like capitalization,
        parentheticals e.g. Everclear (band), and 'the'
    '''

    ret = a.lower()
    ret = ret.replace(' ','')
    ret = re.sub(r'\(.*?\)','', ret)
    ret = re.sub(r'the','', ret)
    return ret

def strDist(a, b):
    '''Calculates the Levenshtein distance between a and b.
    src: http://hetland.org/coding/python/levenshtein.py
    '''

    n, m = len(a), len(b)

    if n > m:
        # Make sure n <= m, to use O(min(n, m)) space
        a, b = b, a
        n, m = m, n

    current = range(n+1)
    for i in range(1, m+1):
        previous, current = current, [i]+[0]*n

        for j in range(1, n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]

            if a[j-1] != b[i-1]:
                change = change + 1

            current[j] = min(add, delete, change)

    return current[n]


# (field1, val1), (field2, val2)...
def printNice(*args):
   for x in args:
      mylog.DBG1(3, u'{0:20} ==> {1:20}'.format(x[0], x[1]))

if __name__ == '__main__':
   try:
      type = sys.argv[1]
      arg1 = sys.argv[2]
   except IndexError:
      exit('usage: %s [TRACKJUNK|TESTARTIST|TESTTRACK|CLEANARTIST|TRACKMATCH|CLEANTRACK|'
           'UNESCAPE] str1 [str2]' % sys.argv[0])


   if type == 'TESTARTIST':
      try:
         arg2 = sys.argv[3]
         print artistCompare(arg1, arg2)
      except IndexError:
         exit('usage: %s TESTARTIST str1 str2' % sys.argv[0])

   elif type == 'UNESCAPE':
      print unescape(arg1)

   elif type == 'TRACKMATCH':
      try:
         arg2 = sys.argv[3]
         print isLooseTrackMatch(arg1, arg2)
      except IndexError:
         exit('usage: %s TRACKMATCH str1 str2' % sys.argv[0])

   elif type == 'TESTTRACK':
      try:
         arg2 = sys.argv[3]
         print trackCompare(arg1, arg2)
      except IndexError:
         exit('usage: %s TESTTRACK str1 str2' % sys.argv[0])

   elif type == 'CLEANTRACK':
      print sanitizeTrackStr(arg1)

   elif type == 'TRACKJUNK':
      print removeTrackJunk(arg1)
