''' functions for searching fs for music, reading/writing tags from files '''

import fnmatch, os, sys 
import hashlib, zlib 
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC  
from mutagen.oggvorbis import OggVorbis  
from mp3scrub import globalz
from mp3scrub.util import strtool, mylog, findxml
from mp3scrub.util.musicTypes import MP3File, Track


def MP3Finder(dir_str, mp3_list, callback):
    ''' search for mp3 files in directory dir_str. populates list mp3_list '''

    hash_list = []

    if not os.path.exists(dir_str):
        mylog.ERR('directory %s doesn\'t exist' % (dir_str))
        return -1
  
     
    i = 0
    for root, dirs, files in os.walk(str(dir_str)):

        for file in files:
            
            if fnmatch.fnmatch(file, '*.mp3') or \
               fnmatch.fnmatch(file, '*.mp4') or \
               fnmatch.fnmatch(file, '*.ogg') or \
               fnmatch.fnmatch(file, '*.flac'):
                i += 1
                full_path = os.path.join(root, file)

                try:
                    with open(unicode(full_path), 'rb') as mp3fn:

                        mp3fn.seek(100000)
                        taste = mp3fn.read(10000)
                        is_dup = False

                        if taste in hash_list:
                            is_dup = True
                        else:
                            hash_list.append(taste)

                        mp3_list.append(MP3File(is_dup_flag=is_dup, my_path=full_path))

                        callback('adding: %s' % (full_path))

                        mylog.DBG1(3, 'adding to list len: %d file: %s' % (i, unicode(full_path)))

                except UnicodeDecodeError:
                    mylog.ERR('mp3scrub does not support unicode filenames: %s' % \
                               unicode(full_path, errors='replace'));
                    pass

class Id3tool:
    ''' class to read/write mp3 tags '''

    def __init__(self, fn):
        ''' allow throw if file not supported '''

        if fnmatch.fnmatch(fn, '*.ogg'):
            self.tag_obj = OggVorbis(fn)

        elif fnmatch.fnmatch(fn, '*.flac'):
            self.tag_obj = FLAC(fn)

        else:
            self.tag_obj = EasyID3(fn)

    def save(self):
        self.tag_obj.save()

    def readTag(self, tag):
        if self.tag_obj:
            tmp = self.tag_obj.get(unicode(tag))
            return tmp[0] if tmp else  ''
        else:
            return ''

    def writeTag(self, tag, val):
        self.tag_obj[unicode(tag)] = unicode(val)


def importMP3s(mp3_list, file_name): 
    ''' load an xml file into an MP3File list '''

    tag_reader = findxml.XMLReader(xmlFile=file_name)

    mp3_nodes = tag_reader.getTheseNodes('mp3')

    tmp_sort = []
    
    for node in mp3_nodes:
        orig_artist = findxml.safeChildGet(node, 'originalartist').strip()
        clean_artist = findxml.safeChildGet(node, 'cleanartist').strip()
        orig_track = findxml.safeChildGet(node, 'originaltrack').strip()
        clean_track = findxml.safeChildGet(node, 'cleantrack').strip()
        orig_album = findxml.safeChildGet(node, 'originalalbum').strip()
        clean_album = findxml.safeChildGet(node, 'cleanalbum').strip()
        orig_tracknum = findxml.safeChildGet(node, 'originaltracknum').strip()
        clean_tracknum = findxml.safeChildGet(node, 'cleantracknum').strip()
        path = findxml.safeChildGet(node, 'path').strip()

        artist = clean_artist if clean_artist else orig_artist
        track = clean_track if clean_track else orig_track
        album = clean_album if clean_album else orig_album
        tracknum = clean_tracknum if clean_tracknum else orig_tracknum

        mylog.INFO('orig_artist: \'%s\' clean_artist: \'%s\' track: %s album: %s tracknum: %s' %
                   (orig_artist, clean_artist, track, album, tracknum))

        orig_mp3 = Track(_artist=artist, _name=track, _album=album, 
                         _track_num=tracknum, _path=path)

        mp3_list.append(MP3File(orig_track=orig_mp3.copy(), my_path=path))


    tag_reader.close()


def exportMP3s(mp3_list, file_name): 
    ''' given an mp3_list, export their tags and paths to an xml file '''

    tag_writer = findxml.XMLWriter(file_name)

    for mp3_file in mp3_list:

        tmp_node = findxml.MP3FileNode(mp3_file) 

        if tmp_node:
            tag_writer.addNode(tmp_node)

    tag_writer.close()


def doXtoMP3s(x,*args):
   listfn = open(mp3listfn,'rU')
   try:
      for line in listfn:
         line = line.rstrip('\n')
         x(line,*args)

   finally:
      listfn.close()


