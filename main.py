#!/usr/bin/env python

'''
The tag ID algorithm to identify the music is a combination of several algorithms 
described in more detail in other modules. I make 3 passes through the entire list of 
MP3s, and make more accurate guesses in each one, e.g. tracks we couldn't ID in PASS1
might get ID'ed by PASS3. At a high level, for each MP3, do:

1. PASS1 though the list:
    a. use google to fix artist name spelling mistakes (better than last.fm for that)
    b. lookup all artist metadata via last.fm (no guessing yet, just get the data)

2. PASS2 though the list:
    b. attempt to use the last.fm metadata to find a match based on the current tags
    c. for the rest that can't be IDed w/ last.fm, use musicbrainz (hashing)

3. PASS3 though the list:
    a. musicbrainz is good at refining artist and track names, but not so much albums.
       Go back through the list and try last.fm again, because some of the tracks ID'ed
       by musicbrainz in PASS2 will now get recognized by last.fm


Although 3 passes sounds costly, the metadata web lookup is always the bottleneck, and
that only needs to be done once in PASS1. 
'''

# local imports
from mp3scrub import scrubCmds
from mp3scrub.gui import guiMain
from mp3scrub.util import mylog

# force a few import now to avoid failures hours into a job...
import shelve
import dbhash
import anydbm
import musicdns.avcodec
import musicdns.ofa

# etc imports
from optparse import OptionParser
import os


parser = OptionParser()

parser.add_option('-d', help=('edit filenames and create subdirectories in addition to ID3 '
                            'tags. (WRITETAG mode only)'), action='store_false',
                            dest='editfilenames', default=False)

parser.add_option('-i', help=('use specified mp3 list file instead of default %s' % 
                            'mp3save.xml'), action='store', type='string', dest='XMLFILE',
                            default='mp3save.xml') 

parser.add_option('-t', help=('use specified tag output file instead of default %s' % 
                            'id3save.xml'), action='store', type='string', dest='ID3FILE',
                            default='id3save.xml') 

parser.add_option('-x', help='use musicbrainz for every single mp3', action='store_true', 
                           dest='ALLPUID', default=False) 

parser.add_option('-a', help=('create a new mp3 xml file in current dir only containing files ' 
                            'matching specified artist string. (GENTAG mode only)'), 
                            action='store', type='string', dest='ARTISTSTR') 

parser.add_option('-F', help=('FIND mode (step 1). finds all music files in specified directory, '
                              ' FINDDIR'), action='store', type='string', dest='FINDDIR')

parser.add_option('-M', help=('MERGE mode (step 2). requires FIND mode results. moves '
                            'unique music listed in XMLFILE into MERGE dir.'), 
                            action='store', type='string', dest='MERGEDIR')

parser.add_option('-G', help=('GENTAG mode. (step 3). Generates best match guesses for ID3 '
                            'tags for all files listed in XMLFILE. Does not edit anything. '
                            'Results saved in ID3FILE'), action='store_true', dest='GENTAG', 
                            default=False) 

parser.add_option('-W', help=('WRITETAG mode. (step 4). requires MERGEDIR mode results. '
                            'Modifies ID3 tags guessed in ID3FILE'), action='store_true', 
                            dest='WRITETAG', default=False) 
                            

(options, args) = parser.parse_args()


flagSet = 0


# int cast hack to make sure just one flag was used
for flag in (options.GENTAG, options.WRITETAG, options.MERGEDIR, options.FINDDIR): 
    flagSet += int(flag is (None or False))

if flagSet != 1:
    guiMain.guiMain()   

# disable cli for now
'''
if options.XMLFILE:
    if not os.path.exists(options.XMLFILE):
        mylog.ERR('XML file %s does not exist' % options.XMLFILE)
        quit(1)

if options.FINDDIR:
    mainCmds.FindMusic(options.FINDDIR, options.XMLFILE)

if options.GENTAG:
    mp3_list = mainCmds.ListFoundMusic(options.XMLFILE, options.ARTISTSTR)


    clean_mp3_list = mainCmds.IdentifyMusic(mp3_list, options.ALLPUID)

    mainCmds.WriteMusic(clean_mp3_list)
'''
