'''A facade to all the modules for mp3scrub functionality. Can also be used
as a CLI.
'''

import re, os
from shutil import move
from mp3scrub import globalz
from mp3scrub.util import strtool, mylog, fileio
from mp3scrub.util.musicTypes import Artist, Album, Track, MP3File
from mp3scrub.netquery import puidquery, tagGuessCache


def ExportWork(mp3_list, file_name):
    '''Wrapper for persisting the mp3 tags to an XML file.

    mp3_list -> list of MP3File objects (supposedly populated via main.FindMusic) 
    file_name -> name of the xml file to output

    returns -> None
    '''

    fileio.exportMP3s(mp3_list, file_name)


def ImportWork(mp3_list, file_name):
    '''load up a previously exported list 
    
    file_name -> name of the xml file of exported list
    mp3_list -> empty list to populate with MP3File's

    returns -> None
    '''

    fileio.importMP3s(mp3_list, file_name)


def MakeDirTree(mp3_list, dir_path):
    '''Given a list of MP3File, will move the *.mp3 files they represnt to a new
    directory in dir_path. Will make a pretty tree with a new folder per artist.

    mp3_list -> list of MP3File objects (supposedly populated via main.FindMusic)
    dir_path -> directory to create the tree

    returns -> None
    '''

    if not os.path.exists(dir_path):
        mylog.ERR('no existe \'%s\'' % dir_path)


    for i,mp3 in enumerate(mp3_list):
        if mp3.is_dup:
            mylog.INFO('skipping dup track \'%s\'...' % (mp3.orig_track.path))
            continue

        sub_dir = strtool.safeUni(mp3.clean_track.artist)

        if not sub_dir or re.search(r'^\s+$', sub_dir):
            sub_dir = strtool.safeUni(mp3.orig_track.artist)

            if not sub_dir or re.search(r'^\s+$', sub_dir):
                sub_dir = 'UNKNOWN'

        new_dir = os.path.join(dir_path, sub_dir)
        orig_path = mp3.orig_track.path

        if not os.path.exists(new_dir):
            try:
                os.mkdir(new_dir)
            except:
                mylog.ERR('error creating \'%s\'...' % (orig_path))
                continue
                

        mylog.DBG('moving \'%s\' to \'%s\'...' % (orig_path, new_dir))

        try:
            move(orig_path, new_dir)
        except:
            mylog.ERR('error moving \'%s\' to \'%s\'...' % (orig_path, new_dir))
            continue
        

def FindMusic(my_dir, callback, only_artist_str=''):
    '''Given a directory, will populate a list with all the *.mp3 files found in
    that directory (recursively) and read their current tag info. Usually the 
    first step in any use case. 

    my_dir -> directory to search for *.mp3
    callback -> a function pointer funct(str) used to return status info 
    only_artist_str -> optional tag to only find artists matching this string

    returns -> mp3_list, a list of MP3File objects
    '''

    mp3_list = []

    fileio.MP3Finder(my_dir, mp3_list, callback)

    new_mp3_list = []

    for mp3_file in mp3_list:

        fn = mp3_file.orig_track.path
        is_dup = mp3_file.is_dup

        callback('processing: %s' % fn)

        
        # load up the id3 tags from the mp3s in our xml list 
        try:
            id3_reader = fileio.Id3tool(fn)


            orig_mp3 = Track(_artist=id3_reader.readTag('artist'),
                             _name=id3_reader.readTag('title'),
                             _album=id3_reader.readTag('album'),
                             _track_num=id3_reader.readTag('tracknumber'),
                             _path=fn)


            if only_artist_str:
                srch = strtool.sanitizeTrackStr(only_artist_str)
                artist = strtool.sanitizeTrackStr(mp3_obj.orig_track.artist)

                if not re.search(srch, artist, re.IGNORECASE):
                    mylog.DBG1(6,'skipping artist %s for match %s' % (srch, artist))
                    continue

            new_mp3_list.append(MP3File(orig_track=orig_mp3.copy(), 
                                my_path=fn, is_dup_flag=is_dup))


        except:
            mylog.ERR('ID3 read failed on \'%s\'\n' % fn)

            new_mp3_list.append(MP3File(my_path=fn, is_dup_flag=is_dup))

    del mp3_list

    return new_mp3_list


def WriteMusic(mp3_list, callback):
    '''Given a list of MP3File, will write to the *.mp3 files the new tag info stored
    in the MP3File.


    mp3_list -> list of MP3File objects (supposedly populated via main.FindMusic)
    callback -> a function pointer funct(str) used to return status info 

    returns -> None
    '''

    for i,mp3 in enumerate(mp3_list):

        callback('updating tags for %s...' % mp3.orig_track.path)

        if not os.path.exists(mp3.orig_track.path):
            mylog.ERR('no existe \'%s\'' % mp3.orig_track.path)
            continue

        if mp3.result != MP3File.QRY_RESULT.FIELDS_CHANGED:
            mylog.ERR('failed cleanup for \'%s\', skipping' % mp3.orig_track.path)
            continue

        try:
            mylog.INFO('writing tags to fn: %s' % mp3.orig_track.path)
            id3_writer = fileio.Id3tool(mp3.orig_track.path)

            id3_writer.writeTag('artist', mp3.clean_track.artist) 
            id3_writer.writeTag('title', mp3.clean_track.name) 
            id3_writer.writeTag('album', mp3.clean_track.album) 
            id3_writer.writeTag('tracknumber', mp3.clean_track.track_num) 
            id3_writer.save()

        except:
            mylog.ERR('ID3 write failed on \'%s\'\n' % mp3.orig_track.path)
            continue



def IdentifyMusic(mp3_list, callback=None):
    '''The meat of the entire program. Loops through a list of MP3File objs, and will
    attempt to find better tag matches for the artist, album, track, and tracknum.


    mp3_list -> list of MP3File objects (supposedly populated via main.FindMusic)

                (note that these objects specify both old and refined tags. entering
                 this function, the refined tags will be empty. exiting this function,
                 they will be populated)

    callback -> a function pointer funct(str) used to return status info 

    returns -> None
    '''

    if globalz.PERSIST_CACHE_ON:
        tagGuessCache.undump()

    try:

        # PASS 1: use google to refine the artist name
        for mp3_count, mp3_obj in enumerate(mp3_list):

            if callback:
                callback('pass1: %s - %s' % (mp3_obj.orig_track.artist, mp3_obj.orig_track.name))

            # use google instead of last.fm to correct the artist name
            (net_error, web_guess) = tagGuessCache.queryGoogCache(mp3_obj.orig_track.artist) 

            if not net_error:

                if web_guess:

                    # run some heuristics to make sure the artist makes sense
                    if strtool.artistCompare(mp3_obj.orig_track.artist, web_guess):
                        mp3_obj.clean_track.artist = web_guess

                        # now look up the last.fm track list for the top 10 albums of artist
                        is_track_found = tagGuessCache.updateGuessCache(mp3_obj.orig_track.path, 
                                                                        mp3_obj.orig_track.name, 
                                                                        mp3_obj.clean_track.artist)

                        if not is_track_found: 
                            mp3_obj.result = MP3File.QRY_RESULT.TRACK_NOT_FOUND 
                            mp3_obj.clean_track.artist = mp3_obj.orig_track.artist 
                        else:
                            mp3_obj.result = MP3File.QRY_RESULT.OK

                    else:
                        mp3_obj.result = MP3File.QRY_RESULT.ARTIST_BAD_MATCH
                        mp3_obj.clean_track.artist = mp3_obj.orig_track.artist 
                else:
                    mp3_obj.result = MP3File.QRY_RESULT.ARTIST_NOT_FOUND
                    mp3_obj.clean_track.artist = mp3_obj.orig_track.artist 
            else:
                mp3_obj.result = MP3File.QRY_RESULT.NET_ERROR
                mp3_obj.clean_track.artist = mp3_obj.orig_track.artist 

            if (mp3_count % 100) == 0:
                mylog.INFO('processed %d files' % (mp3_count))


        if globalz.CACHE_DEBUG_ON:
            with open('pprint.txt','w') as f:
                f.write('BEFORE:\n')
                tagGuessCache.dbgPrint(f)
               
        mylog.INFO("refining track info...")



        # PASS 2: use lastfm and musicbrainz for better track/album info
        tagGuessCache.refineGuessCache()

        # see if we found a guess in last.fm
        for mp3_obj in mp3_list:

            if mp3_obj.result == MP3File.QRY_RESULT.OK: 

                if callback:
                    callback('pass2: lastfm: %s - %s' % (mp3_obj.orig_track.artist,
                                                         mp3_obj.orig_track.name))


                guess_track_obj = tagGuessCache.searchGuessCache(mp3_obj.clean_track.artist, 
                                                                 mp3_obj.orig_track.path)

                if not guess_track_obj:
                    mp3_obj.result = MP3File.QRY_RESULT.TRACK_NOT_FOUND 
                else:
                    mp3_obj.clean_track.name = guess_track_obj.name
                    mp3_obj.clean_track.album = guess_track_obj.album
                    mp3_obj.clean_track.track_num = guess_track_obj.track_num
                    mp3_obj.method1 = MP3File.METHOD.ID3ID

        # now use musicbrainz for what lastfm couldn't find 
        # (skip NET_ERROR tracks too...want to be clear in the gui that 
        #  these tracks failed due to network problems, not algorithm failure
        for mp3_obj in mp3_list:

            if mp3_obj.result != MP3File.QRY_RESULT.OK and \
               mp3_obj.result != MP3File.QRY_RESULT.NET_ERROR:

                if callback:
                    callback('pass2: hashing: %s - %s' % (mp3_obj.orig_track.artist, 
                              mp3_obj.orig_track.name))

                mylog.INFO('using hashing for unknown file %s' % (mp3_obj.orig_track.path))
                puid_qry_obj = puidquery.PUIDQuery()

                (mp3_obj.clean_track.artist, 
                 mp3_obj.clean_track.album, 
                 mp3_obj.clean_track.name,
                 mp3_obj.clean_track.track_num) = puid_qry_obj.lookupTrack(mp3_obj.orig_track.path)

                if mp3_obj.clean_track.artist:
                    mp3_obj.method1 = MP3File.METHOD.HASHED
                else:
                    mp3_obj.method1 = MP3File.METHOD.FAILEDHASH


        # PASS 3: retry album name guessing. now that the data has been partially cleaned, we'll have 
        #         better luck guessing the correct album name
        tagGuessCache.clearCache()

        for mp3_obj in mp3_list:
            if mp3_obj.result == MP3File.QRY_RESULT.NET_ERROR: continue

            mylog.INFO('pass3: on file \'%s\' track \'%s\'' % 
                       (mp3_obj.orig_track.path, mp3_obj.clean_track.name))

            if callback:
                callback('pass3: on file \'%s\' track \'%s\'' % 
                         (mp3_obj.orig_track.path, mp3_obj.clean_track.name))

            if mp3_obj.clean_track.artist:
                if mp3_obj.clean_track.name:
                    tagGuessCache.updateGuessCache(mp3_obj.orig_track.path, 
                                                   mp3_obj.clean_track.name, 
                                                   mp3_obj.clean_track.artist)
                else: 
                    tagGuessCache.updateGuessCache(mp3_obj.orig_track.path, 
                                                   mp3_obj.orig_track.name, 
                                                   mp3_obj.clean_track.artist)

        tagGuessCache.refineGuessCache()

        for mp3_obj in mp3_list:
            if mp3_obj.result == MP3File.QRY_RESULT.NET_ERROR: continue

            guess_track_obj = tagGuessCache.searchGuessCache(mp3_obj.clean_track.artist, 
                                                             mp3_obj.orig_track.path)

            if guess_track_obj:
                mylog.INFO('pass3_result: found guess on file \'%s\' track \'%s\'' % 
                           (mp3_obj.orig_track.path, mp3_obj.clean_track.name))
                mp3_obj.clean_track.name = guess_track_obj.name
                mp3_obj.clean_track.album = guess_track_obj.album
                mp3_obj.clean_track.track_num = guess_track_obj.track_num
                mp3_obj.updateResults()
                mp3_obj.method2 = MP3File.METHOD.ID3ID
                mp3_obj.result = MP3File.QRY_RESULT.FIELDS_CHANGED
            else:
                mylog.INFO('pass3_result: no guess found on file \'%s\' track \'%s\'' % 
                           (mp3_obj.orig_track.path, mp3_obj.clean_track.name))
                mp3_obj.method2 = MP3File.METHOD.SECONDPASSFAIL

                # make a final call on whether we got good results or not
                if mp3_obj.method1 == MP3File.METHOD.FAILEDHASH or \
                    mp3_obj.method1 == MP3File.METHOD.UNKNOWN:

                    mp3_obj.result = MP3File.QRY_RESULT.NO_GUESS

                else:
                    mp3_obj.result = MP3File.QRY_RESULT.FIELDS_CHANGED


        if globalz.CACHE_DEBUG_ON:
            for x in mp3_list: print unicode(x).encode('utf-8')

            with open('pprint.txt','w') as f:
                f.write('AFTER:\n')
                tagGuessCache.dbgPrint(f)


    finally:
        if globalz.PERSIST_CACHE_ON:
            mylog.INFO('persisting track guesses')
            tagGuessCache.dump()

    return mp3_list



