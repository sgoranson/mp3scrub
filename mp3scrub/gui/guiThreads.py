'''classes and thread wrappers to help the GUI stay speedy during long running
processes. Sometimes tag identification can take 3+ hours, and you don't want to
wait that long for the window to repaint. 

The GUI will spawn a new thread for finding/IDing/updating mp3s, and a wxEvent 
will be sent when the work is done.

The GUI also needs to be told when to refresh the main grid of mp3 metadata. The
metadata (MP3File list) will obviously be changing as we update tags, and the grid
needs to reflect that. There is a basic subject/observer pattern that wraps the 
MP3File's and makes updates clean. 

Also note that the main list of MP3s is global (as it is shared by threads), so
mutexs are a must. 
'''

import sys, time
import wx
import threading
import traceback
from mp3scrub import scrubCmds, globalz
from mp3scrub.util import mylog
from mp3scrub.netquery import tagGuessCache
from mp3scrub.util.musicTypes import Artist, Album, Track, MP3File


class MP3Subject(object):
    ''' a subject (see GoF observer pattern) that has an MP3File.
        When it's MP3File has been modified, the user must call notify()
        to cause the GUI to update.
    '''
    def __init__(self, mp3_obj):
        self.mp3_obj = mp3_obj
        self.observers = []

    def addObserver(self, observer):
        self.observers.append(observer)

    def delObserver(self, observer):
        try:
            self.observers.remove(observer)
        except ValueError:
            mylog.ERR('cannot remove observer')

    def notify(self):
        for i, obs in enumerate(self.observers):
            mylog.DBG1(6, 'notifying observer %d' % i)
            obs.update()



class MP3Observer(object):
    ''' an observer (see GoF observer pattern) that has an MP3File.
        Needs a ref to the MP3Grid to know how to update the GUI.
    '''
    def __init__(self, mp3_subj, row_n, grid_ref):
        self.mp3_subj = mp3_subj
        self.row_n = row_n
        self.grid_ref = grid_ref


    def update(self):
        set_red = False

        if self.mp3_subj.mp3_obj.result == MP3File.QRY_RESULT.NO_GUESS: 
            set_red = True

        for col, data in enumerate(self.mp3_subj.mp3_obj.fieldList):
            if set_red: 
                self.grid_ref.SetCellBackgroundColour(self.row_n, col, wx.RED)

            self.grid_ref.setCell(self.row_n, col, data)




class ThreadQuit(Exception):
    '''A safe way to exit a thread early if cancel has been clicked.'''
    pass


class DirTreeThread(threading.Thread):
    ''' move the files to a new location and make a nice tree based on artist dir '''

    def __init__(self, **mkwargs):
        threading.Thread.__init__(self, target=self.dirtree, kwargs=mkwargs)
        self.error_str = ''


    def dirtree(self, dir_name='', cbwin=None):
        '''
        dir_name -> where to move the mp3 collection
        cbwin -> ref to the parent window (need to know where to send done event)
        '''
        
        try:
            mylog.INFO('exporting tag work to file \'%s\'' % dir_name)

            with globalz.MP3_MUTEX:
                scrubCmds.MakeDirTree(globalz.MP3_OBJ_LIST, dir_name)

                del globalz.MP3_OBJ_LIST[:]
       
 
        except BaseException, e:
            mylog.ERR('error in DirTree' + str(e))
            mylog.ERR(traceback.format_exc())
            self.error_str = str(e)

        finally:
            mylog.INFO('ending DirTree')
            wx.PostEvent(cbwin, globalz.WorkDoneEvent(src='DirTree', error_str=self.error_str))


class ExportThread(threading.Thread):
    ''' export the mp3 list an xml file '''

    def __init__(self, **mkwargs):
        threading.Thread.__init__(self, target=self.doExport, kwargs=mkwargs)
        self.error_str = ''


    def doExport(self, xml_name='', cbwin=None):
        '''
        xml_name -> xml tag file
        cbwin -> ref to the parent window (need to know where to send done event)
        '''
        
        try:
            mylog.INFO('exporting tag work to file \'%s\'' % xml_name)

            with globalz.MP3_MUTEX:
                scrubCmds.ExportWork(globalz.MP3_OBJ_LIST, xml_name)
       
 
        except BaseException, e:
            mylog.ERR('error in Export' + str(e))
            mylog.ERR(traceback.format_exc())
            self.error_str = str(e)

        finally:
            mylog.INFO('ending Export')
            wx.PostEvent(cbwin, globalz.WorkDoneEvent(src='Export-XML', error_str=self.error_str))



class ImportThread(threading.Thread):
    '''Import a previously saved XML file of mp3 tag edits'''

    def __init__(self, **mkwargs):
        threading.Thread.__init__(self, target=self.doImport, kwargs=mkwargs)
        self.error_str = ''


    def doImport(self, xml_name='', cbwin=None):
        '''
        xml_name -> xml tag file
        cbwin -> ref to the parent window (need to know where to send done event)
        '''
        
        try:
            mylog.INFO('importing tag work from file \'%s\'' % xml_name)

            with globalz.MP3_MUTEX:
                scrubCmds.ImportWork(globalz.MP3_OBJ_LIST, xml_name)

                # sort list (will order by artist name in the GUI)
                tmp_sort = [ (i.orig_track.artist, i.orig_track.album, i) for i in globalz.MP3_OBJ_LIST ]  
                tmp_sort.sort()

                del globalz.MP3_OBJ_LIST[:]
                globalz.MP3_OBJ_LIST = [ i for (_, _, i) in tmp_sort ]
        
  
        except BaseException, e:
            mylog.ERR('error in Import' + str(e))
            mylog.ERR(traceback.format_exc())
            self.error_str = str(e)

        finally:
            mylog.INFO('ending import')
            wx.PostEvent(cbwin, globalz.WorkDoneEvent(src='Import-XML', error_str=self.error_str))



class FindThread(threading.Thread):
    '''Thread to wrap the finding of the *.mp3 files. Each Thread calls
    an associated function in scrubCmds.py.
    '''

    def __init__(self, **mkwargs):
        threading.Thread.__init__(self, target=self.listMusic, kwargs=mkwargs)
        self.error_str = ''


    def listMusic(self, dir_name='', cbwin=None):
        '''
        dir_name -> directory to search
        cbwin -> ref to the parent window (need to know where to send done event)
        '''
        
        i = (x for x in xrange(50000))

        # callback (updates the progressDialog)
        def setStatus(*args):
            y = i.next()

            if globalz.CANCEL_EVENT.isSet():
                mylog.INFO('find_thread got cancel')

                del globalz.MP3_OBJ_LIST[:]

                globalz.CANCEL_EVENT.clear()

                raise ThreadQuit

            if args and (y % globalz.MAX_EVT == 0):
                pctx = y % globalz.MAXROWS
                txt = unicode(args[0])
                wx.PostEvent(cbwin, globalz.StatusUpdateEvent(src='find_thread', pct=pctx, msg=txt))


        try:
            # find all *.mp3 and read their current tags
            with globalz.MP3_MUTEX:
                raw_mp3_list = scrubCmds.FindMusic(dir_name, setStatus)

                # sort list (will order by artist name in the GUI)
                tmp_sort = [ (i.orig_track.artist, i.orig_track.album, i) for i in raw_mp3_list ]  
                tmp_sort.sort()

                del globalz.MP3_OBJ_LIST

                globalz.MP3_OBJ_LIST = [ i for (_, _, i) in tmp_sort ]

  
        except ThreadQuit: 
            mylog.INFO('quitting find_thread early...')

        except BaseException, e:
            mylog.ERR('error in FindMusic' + str(e))
            mylog.ERR(traceback.format_exc())
            self.error_str = str(e)

        finally:
            mylog.INFO('ending find_thread')
            wx.PostEvent(cbwin, globalz.WorkDoneEvent(src='Find-Music', error_str=self.error_str))

     


class UpdateThread(threading.Thread):
    '''Thread to wrap the new tag updating of the *.mp3 files. Each Thread calls
    an associated function in scrubCmds.py.
    '''

    def __init__(self, **mkwargs):
        threading.Thread.__init__(self, target=self.updateMusic, kwargs=mkwargs)
        self.error_str = ''

    def updateMusic(self, cbwin=None):
        '''
        cbwin -> ref to the parent window (need to know where to send done event)
        '''

        i = (x for x in xrange(50000))

        # callback (updates the progressDialog)
        def setStatus(*args):
            y = i.next()

            if globalz.CANCEL_EVENT.isSet():
                mylog.INFO('clean_thread got cancel')

                globalz.CANCEL_EVENT.clear()

                raise ThreadQuit

            if args:
                pctx = y % globalz.MAXROWS
                txt = unicode(args[0])
                wx.PostEvent(cbwin, globalz.StatusUpdateEvent(src='update_thread', pct=pctx, msg=txt))


        try:
            mylog.INFO('starting UpdateThread....')

            with globalz.MP3_MUTEX:
                scrubCmds.WriteMusic(globalz.MP3_OBJ_LIST, setStatus)

        except ThreadQuit: 
            mylog.INFO('quitting update_thread early...')

        except BaseException, e:
            mylog.ERR('error in updateMusic: ' + str(e))
            mylog.ERR(traceback.format_exc())
            self.error_str = str(e)

        finally:
            mylog.INFO('ending update_thread')
            wx.PostEvent(cbwin, globalz.WorkDoneEvent(src='Write-Tags', error_str=self.error_str))



class CleanThread(threading.Thread):
    '''Thread to wrap the music identification of the *.mp3 files. Each Thread calls
    an associated function in scrubCmds.py.
    '''

    def __init__(self, **mkwargs):
        threading.Thread.__init__(self, target=self.cleanMusic, kwargs=mkwargs)
        self.error_str = ''


    def cleanMusic(self, cbwin=None, bar_max=globalz.MAXROWS):
        '''
        cbwin -> ref to the parent window (need to know where to send done event)
        bar_max -> length of the mp3 list. needed for progressDialog updating
        '''

        mylog.INFO('cleaning up mp3 tags...')

        i = (x for x in xrange(50000))

        def setStatus(*args):
            y = i.next()

            if globalz.CANCEL_EVENT.isSet():
                mylog.INFO('clean_thread got cancel')

                globalz.CANCEL_EVENT.clear()

                raise ThreadQuit

            if args and (y % globalz.MAX_EVT == 0):
                pctx = y % bar_max
                txt = unicode(args[0])
                wx.PostEvent(cbwin, globalz.StatusUpdateEvent(src='clean_thread', pct=pctx, msg=txt))

        try:
            with globalz.MP3_MUTEX:

                scrubCmds.IdentifyMusic(globalz.MP3_OBJ_LIST, setStatus)

                # sort
                tmp_sort = [ (i.clean_track.artist, i.clean_track.album, i) for i in globalz.MP3_OBJ_LIST ]  
                tmp_sort.sort()

                del globalz.MP3_OBJ_LIST

                globalz.MP3_OBJ_LIST = [ i for (_, _, i) in tmp_sort ]

        except ThreadQuit: 
            mylog.INFO('quitting clean_thread early...')

        except BaseException, e:
            mylog.ERR('error in doCleanMusic: ' + str(e))
            mylog.ERR(traceback.format_exc())
            self.error_str = str(e)

        finally:
            mylog.INFO('ending clean_thread')
            wx.PostEvent(cbwin, globalz.WorkDoneEvent(src='Clean-Tags', error_str=self.error_str))
