'''main wx code'''

import wx
import wx.grid
import wx.lib.newevent
import traceback
import sys, time
import threading
from collections import defaultdict

from mp3scrub import globalz
from mp3scrub.util import mylog
from mp3scrub.netquery import tagGuessCache
from mp3scrub.util.musicTypes import Artist, Album, Track, MP3File
from mp3scrub.gui.guiThreads import *    


class RefineTrackDialog(wx.Dialog):
    ''' manual track refine dialog  '''
    
    def __init__(self, parent, row_num):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, 'Refine Track')

        self.row_num = row_num

        try:
            '''get the current data outta the grid'''

            self.artist_str = globalz.SUBJECT_LIST[row_num].mp3_obj.orig_track.artist
            self.album_str = globalz.SUBJECT_LIST[row_num].mp3_obj.orig_track.album
            self.track_str = globalz.SUBJECT_LIST[row_num].mp3_obj.orig_track.name
            self.track_num = globalz.SUBJECT_LIST[row_num].mp3_obj.orig_track.track_num
            self.artist_obj = None

        except KeyError:
            err_dialog = wx.MessageDialog(self, 'Bad row: %d' % row_num, 'Error', wx.OK | wx.ICON_ERROR)
            err_dialog.ShowModal()
            parent.Destroy()
            exit(1)

        self.artist_combo = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_SORT) 
        self.album_combo = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_SORT) 
        self.track_combo = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_SORT) 
        self.track_entry = wx.TextCtrl(self, wx.ID_ANY, '1')
        self.search_btn = wx.Button(self, wx.ID_ANY, 'Guess Tracks...', size=(160, 30))
        self.cancel_btn = wx.Button(self, wx.ID_ANY, 'Cancel', size=(160, 30))
        self.save_btn = wx.Button(self, wx.ID_ANY, 'Save', size=(160, 30))

        self.Bind(wx.EVT_BUTTON, self.closeMe, self.cancel_btn) 
        self.Bind(wx.EVT_BUTTON, self.initCombos, self.search_btn) 
        self.Bind(wx.EVT_BUTTON, self.saveChanges, self.save_btn) 
        self.Bind(wx.EVT_COMBOBOX, self.onAlbumSelect, self.album_combo)
        self.Bind(wx.EVT_COMBOBOX, self.onTrackSelect, self.track_combo)

        self.grid_sizer =  wx.GridSizer(rows=5, cols=2, vgap=5, hgap=5)
       
        self.grid_sizer.Add(wx.StaticText(self, label='Artist: %s' % self.artist_str), 2, wx.EXPAND)
        self.grid_sizer.Add(self.artist_combo, 2, wx.EXPAND)
        self.grid_sizer.Add(wx.StaticText(self, label='Album: %s' % self.album_str), 2, wx.EXPAND)
        self.grid_sizer.Add(self.album_combo, 2, wx.EXPAND)
        self.grid_sizer.Add(wx.StaticText(self, label='Track: %s' % self.track_str), 2, wx.EXPAND)
        self.grid_sizer.Add(self.track_combo, 2, wx.EXPAND)
        self.grid_sizer.Add(wx.StaticText(self, label='TrackNum: %s' % unicode(self.track_num)), 2, wx.EXPAND)
        self.grid_sizer.Add(self.track_entry, 2, wx.EXPAND)


        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer.Add(self.search_btn, 2, wx.SHAPED, 5)
        self.button_sizer.Add(self.cancel_btn, 2, wx.SHAPED, 5)
        self.button_sizer.Add(self.save_btn, 2, wx.SHAPED, 5)

        self.box = wx.StaticBox(self, wx.ID_ANY, 'Edit Track')
        self.sizer = wx.StaticBoxSizer(self.box, wx.VERTICAL)
        self.sizer.Add(self.grid_sizer, wx.ID_ANY, wx.ALL, 15)
        self.sizer.AddSpacer(40, 1)
        self.sizer.Add(self.button_sizer, 0, wx.CENTER | wx.ALIGN_BOTTOM, 15)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def saveChanges(self, evt):
        '''put the changes back into the grid'''

        art_str = self.artist_combo.GetValue()
        alb_str = self.album_combo.GetValue()
        trk_str = self.track_combo.GetValue()
        trk_num = self.track_entry.GetValue()

        globalz.SUBJECT_LIST[self.row_num].mp3_obj.clean_track.artist = art_str
        globalz.SUBJECT_LIST[self.row_num].mp3_obj.clean_track.album = alb_str
        globalz.SUBJECT_LIST[self.row_num].mp3_obj.clean_track.name = trk_str
        globalz.SUBJECT_LIST[self.row_num].mp3_obj.clean_track.track_num = trk_num
        globalz.SUBJECT_LIST[self.row_num].mp3_obj.result = MP3File.QRY_RESULT.FIELDS_CHANGED;
        globalz.SUBJECT_LIST[self.row_num].notify()
        self.Destroy()

    def closeMe(self, evt):
        self.Destroy()

    def onAlbumSelect(self, evt):
        '''when album changes, update the track combo'''

        if self.artist_obj:

            alb_str = self.album_combo.GetValue()
            trk_str = self.track_combo.GetValue()

            self.track_combo.Clear()

            do_first_trk = True

            for album_obj in self.artist_obj.albums:
                
                if alb_str != album_obj.name: continue

                for track_obj in album_obj.tracks:

                    self.track_combo.Append(track_obj.name)

                    if do_first_trk: 
                        self.track_combo.SetSelection(0)
                        self.track_entry.Clear()
                        self.track_entry.SetValue(unicode(track_obj.track_num))

                        do_first_trk = False


    def onTrackSelect(self, evt):
        '''when track changes, update the track num box'''

        alb_str = self.album_combo.GetValue()
        trk_str = self.track_combo.GetValue()

        for album_obj in self.artist_obj.albums:
            
            if alb_str != album_obj.name: continue

            for track_obj in album_obj.tracks:

                if trk_str != track_obj.name: continue

                self.track_entry.Clear()
                self.track_entry.SetValue(unicode(track_obj.track_num))


    def initCombos(self, evt):
        ''' make some web queries to init the combo boxes '''

        self.artist_combo.Clear()
        self.album_combo.Clear()
        self.track_combo.Clear()

        wait_dialog = wx.ProgressDialog('Searching...', 'Searching...',  maximum=10, parent=self)
        wait_dialog.SetSize((300, 150))
        wait_dialog.SetMaxSize((300,300))
        wait_dialog.SetPosition((250,250))
        wait_dialog.Update(1, 'querying web...')
        self.Refresh()

        _, web_guess = tagGuessCache.queryGoogCache(self.artist_str) 

        if web_guess:
           self.artist_combo.Append(web_guess)
           self.artist_combo.SetSelection(0)

        if not self.artist_obj and web_guess:
            wait_dialog.Update(2, 'querying web...')
            self.artist_obj = tagGuessCache.getRawArtistInfo(web_guess)

        if self.artist_obj and web_guess:
            do_first_alb = True
            do_first_trk = True


            i = 0

            for album_obj in self.artist_obj.albums:
                i += 1

                wait_dialog.Update(i % 10, album_obj.name)

                self.album_combo.Append(album_obj.name)

                if do_first_alb: 
                    self.album_combo.SetSelection(0)


                    for track_obj in album_obj.tracks:

                        self.track_combo.Append(track_obj.name)

                        if do_first_trk: 
                            self.track_combo.SetSelection(0)
                            do_first_trk = False

                    do_first_alb = False


        wait_dialog.Destroy()



class MP3Grid(wx.grid.Grid):
    ''' main grid to display files and tags '''

    def __init__(self, parent):
        super(MP3Grid, self).__init__(parent)

        # setup grid and all its glory
        labelz = MP3File.getFieldLabels()

        self.CreateGrid(globalz.MAXROWS, len(labelz))
        self.EnableEditing(False)
        self.EnableCellEditControl(False)

        for x, l in enumerate(labelz):
            self.SetColLabelValue(x, l)

        self.SetColSize(0, 150)
        self.SetColSize(1, 150)

        for c in xrange(2,6):
            self.SetColSize(c, 300)


    def populateCells(self, filter=None):
        ''' call everytime a major change is made to the global mp3 list '''

        self.ClearGrid()

        with globalz.MP3_MUTEX:

            globalz.SUBJECT_LIST.clear()

            row_num = 0

            for o in globalz.MP3_OBJ_LIST:

                if filter:
                    if not o.clean_track.artist or o.clean_track.artist[0].lower() != filter: continue

                
                mylog.DBG1(6, 'adding track # %d: %s' % (row_num, o.orig_track.path))
                mp3_sub = MP3Subject(o)

                mp3Obz = MP3Observer(mp3_sub, row_num, self)
                mp3_sub.addObserver(mp3Obz)

                globalz.SUBJECT_LIST[row_num] = mp3_sub

                mp3_sub.notify()
                row_num += 1


    def setCell(self, x, y, val):
        ''' make a change to a single cell. quicker than the shotgun approach of populateCells '''
        self.SetCellValue(x, y, unicode(val))



class MP3WaitDialog(wx.ProgressDialog):
    ''' dialog to show everytime a long running process is busy '''

    def __init__(self, title, bar_len, parentx):

        super(MP3WaitDialog, self).__init__(title, title, maximum=bar_len, parent=parentx, 
                                            style=wx.PD_AUTO_HIDE|wx.PD_APP_MODAL|wx.PD_CAN_ABORT)

        self.SetSize((700,150))
        self.SetMaxSize((800,800))
        self.SetPosition((150,250))

class MP3ToolBar(wx.ToolBar):
    '''pretty toolbar'''

    def __init__(self, parent):
        super(MP3ToolBar, self).__init__(parent, style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)
   
        self.parent = parent 
        tsize = (24,24)
        find_bmp =  wx.ArtProvider.GetBitmap(wx.ART_FIND, wx.ART_TOOLBAR, tsize)
        clean_bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_TOOLBAR, tsize)
        update_bmp= wx.ArtProvider.GetBitmap(wx.ART_HARDDISK, wx.ART_TOOLBAR, tsize)

        self.SetToolBitmapSize(tsize)

        self.find_id = 10
        self.clean_id = 20
        self.write_id = 30

        self.AddLabelTool(self.find_id, 'find', find_bmp, shortHelp='Find MP3s')
        self.Bind(wx.EVT_TOOL, self.dispatchBtn)

        self.AddLabelTool(self.clean_id, 'clean', clean_bmp, shortHelp='Clean Tags')
        self.Bind(wx.EVT_TOOL, self.dispatchBtn)

        self.AddLabelTool(self.write_id, 'update', update_bmp, shortHelp='Write Tags')
        self.Bind(wx.EVT_TOOL, self.dispatchBtn)

        self.AddSeparator()

        self.AddControl(wx.StaticText(self, -1, 'filter: ', (30,15), style=wx.ALIGN_RIGHT))

        filter_choices = ['off'] + list('abcdefghijklmnopqrstuvwxyz')

        self.filter_combo = wx.ComboBox(self, 40, 'off', choices=filter_choices, size=(150,-1), 
                                        style=wx.CB_DROPDOWN | wx.CB_READONLY) 
        self.AddControl(self.filter_combo)
        self.Bind(wx.EVT_COMBOBOX, self.doFilter)
        self.Realize()

    def dispatchBtn(self, evt):
        ''' only display the artists starting with the specified letter '''
        id = evt.GetId()

        if id == self.find_id:
            self.parent.doFindMusic(evt)

        elif id == self.clean_id:
            self.parent.doCleanMusic(evt)

        elif id == self.write_id:
            self.parent.doWriteMusic(evt)

        else:
            mylog.ERR('invalid menubar id')


    def doFilter(self, evt):
        ''' only display the artists starting with the specified letter '''

        filter_letter = self.filter_combo.GetValue()

        if filter_letter == 'off':
            self.parent.grid.populateCells()
        else:
            self.parent.grid.populateCells(filter_letter)



class MainApp(wx.Frame):
    ''' the main window '''

    def __init__(self):
        super(MainApp, self).__init__(None, size=(1210, 460))

        self.max_progress = 100
        self.start_time = 0
        self.end_time = 0

        self.wait_dialog = None

        # setup multithread event handlers
        self.Bind(globalz.EVT_WORK_DONE, self.handleWorkDone)
        self.Bind(globalz.EVT_STATUS_UPDATE, self.handleStatusUpdate)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.onGridClick)

        self.grid = MP3Grid(self)

        # make it pretty
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer2.Add(self.grid, 2, wx.EXPAND)

        self.SetSizer(self.sizer2)

        # menu
        self.createMenu()
        super(MainApp, self).SetTitle('MP3Scrub')

        ####### toolbar ######
        tb = MP3ToolBar(self)
        self.SetToolBar(tb)


    def createMenu(self):
        ''' menu initialization '''

        file_menu = wx.Menu()
        item = file_menu.Append(wx.ID_ANY, '&Export...', 'Save the current grid to xml')
        self.Bind(wx.EVT_MENU, self.onExport, item)
        item = file_menu.Append(wx.ID_ANY, '&Import...', 'Import an old grid from xml')
        self.Bind(wx.EVT_MENU, self.onImport, item)
        file_menu.AppendSeparator()
        item = file_menu.Append(wx.ID_EXIT, '&Exit', 'Terminate the program')
        self.Bind(wx.EVT_MENU, self.onExit, item)

        action_menu = wx.Menu()
        item = action_menu.Append(wx.ID_ANY, 'Search...', 'Search a directory for music')
        self.Bind(wx.EVT_MENU, self.doFindMusic, item)
        item = action_menu.Append(wx.ID_ANY, 'Clean tags...', 'Identify your music')
        self.Bind(wx.EVT_MENU, self.doCleanMusic, item)
        item = action_menu.Append(wx.ID_ANY, 'Update tags...', 'Update your music')
        self.Bind(wx.EVT_MENU, self.doWriteMusic, item)

        tools_menu = wx.Menu()
        item = tools_menu.Append(wx.ID_ANY, 'Make directories...', 'create a pretty directory tree by artist')
        self.Bind(wx.EVT_MENU, self.doDirTree, item)

        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, '&File')
        menu_bar.Append(action_menu, '&Action')
        menu_bar.Append(tools_menu, '&Tools')
        self.SetMenuBar(menu_bar) 


    def handleWorkDone(self, evt):
        ''' receive done events from the worker threads '''

        if evt.error_str:
            err_dialog = wx.MessageDialog(self, evt.error_str, 'Fatal Error', wx.OK | wx.ICON_ERROR)
            err_dialog.ShowModal()
            self.Destroy()
            return
                

        self.end_time = time.time()


        if self.wait_dialog:
            self.wait_dialog.Update(self.max_progress - 1, 'Updating grid...') 
            self.grid.populateCells()
            self.printStats()  
            self.wait_dialog.Update(self.max_progress, 'Done') 
            self.wait_dialog = None

        err_dialog = wx.MessageDialog(self, 'Job ' + evt.src + ' finished', 'Work Done', wx.OK)
        err_dialog.ShowModal()
        err_dialog.Destroy()



    def handleStatusUpdate(self, evt):
        ''' receive update events from the worker threads '''

        if self.wait_dialog:

            if evt.src == 'clean_thread':
                (cancel, skip) = self.wait_dialog.Update(evt.pct, evt.msg) 
                if not cancel:
                    globalz.CANCEL_EVENT.set()
            else:
                (cancel, skip) = self.wait_dialog.Pulse(evt.msg) 
                if not cancel:
                    globalz.CANCEL_EVENT.set()


    def onGridClick(self, evt):
        ''' on grid click kick off the manual update window '''

        if evt.GetRow() + 1 <= len(globalz.SUBJECT_LIST):
            self.grid.SelectRow(evt.GetRow()) 
            dialog = RefineTrackDialog(self, evt.GetRow())
            dialog.SetPosition((150,150))
            dialog.ShowModal()
            dialog.Destroy()


    def doWriteMusic(self, evt):
        ''' spawn up the tag updater thread '''

        mylog.INFO('working on update tags...')

        self.max_progress = len(globalz.MP3_OBJ_LIST)
        self.wait_dialog = MP3WaitDialog('Updating tags...', self.max_progress, self)

        self.wait_dialog.Update(0, 'Updating tags...')


        update_thr = UpdateThread(cbwin=self)
        update_thr.daemon = True
        update_thr.start()


    def doCleanMusic(self, evt):
        ''' spawn up the tag identifier thread '''

        mylog.INFO('working on scrubbing mp3s...')

        # 3 passes of cleaning, hence *3
        self.max_progress = len(globalz.MP3_OBJ_LIST) * 3

        self.wait_dialog = MP3WaitDialog('Scrubbing...', self.max_progress, self)
        
        self.wait_dialog.Update(0, 'Scrubbing...')

        self.start_time = time.time()

        clean_thr = CleanThread(cbwin=self, bar_max=self.max_progress)
        clean_thr.daemon = True
        clean_thr.start()


    def doFindMusic(self, evt):
        ''' spawn up the mp3 finder thread '''

        dialog = wx.DirDialog(self, style=wx.DD_DEFAULT_STYLE)
        dialog.SetPosition((30,150))

        dir_name = ''
        if dialog.ShowModal() == wx.ID_OK:
            dir_name = dialog.GetPath()

        dialog.Destroy()

        if dir_name:

            self.max_progress = globalz.MAXROWS
            self.wait_dialog = MP3WaitDialog('Searching...', self.max_progress, self)

            mylog.INFO('searching for mp3s in dir %s...' % dir_name)

            self.wait_dialog.Pulse('searching for mp3s in dir %s...' % dir_name)


            find_thr = FindThread(dir_name=dir_name, cbwin=self)
            find_thr.daemon = True
            find_thr.start()

    def onExport(self, event):
        ''' export the mp3 list an xml file '''

        dialog = wx.FileDialog(self, style=wx.FD_SAVE, wildcard='*.*')

        save_file = ''
        err_str = ''

        if dialog.ShowModal() == wx.ID_OK:
            save_file = dialog.GetPath()


        dialog.Destroy()

        if save_file:
            self.max_progress = globalz.MAXROWS
            self.wait_dialog = MP3WaitDialog('Exporting...', self.max_progress, self)

            self.wait_dialog.Pulse('exporting tag config to file %s...' % save_file)


            export_thr = ExportThread(xml_name=save_file, cbwin=self)
            export_thr.daemon = True
            export_thr.start()


    def onImport(self, evt):
        ''' open an xml file and load it into the grid '''

        dialog = wx.FileDialog(self, style=wx.FD_OPEN, wildcard='*.*')

        save_file = ''
        err_str = ''

        if dialog.ShowModal() == wx.ID_OK:
            save_file = dialog.GetPath()


        dialog.Destroy()

        if save_file:

            self.max_progress = globalz.MAXROWS
            self.wait_dialog = MP3WaitDialog('Importing...', self.max_progress, self)

            self.wait_dialog.Pulse('importing mp3s from config file %s...' % save_file)


            import_thr = ImportThread(xml_name=save_file, cbwin=self)
            import_thr.daemon = True
            import_thr.start()



    def doDirTree(self, evt):
        ''' move the files to a new location and make a nice tree based on artist dir '''

        dialog = wx.DirDialog(self, style=wx.DD_DEFAULT_STYLE)
        dialog.SetPosition((30,150))

        my_dir_name = ''
        err_str = ''

        if dialog.ShowModal() == wx.ID_OK:
            my_dir_name = dialog.GetPath()

        dialog.Destroy()

        if my_dir_name:

            self.max_progress = globalz.MAXROWS
            self.wait_dialog = MP3WaitDialog('Moving Music...', self.max_progress, self)

            self.wait_dialog.Pulse('creating tree in to \'%s\'....' % my_dir_name)


            dirtree_thr = DirTreeThread(dir_name=my_dir_name, cbwin=self)
            dirtree_thr.daemon = True
            dirtree_thr.start()
 

    def onExit(self, event):
        self.Close()  # Close the main window.


    def printStats(self):
        ''' print some debug info '''

        tmp_alb = defaultdict(int)
        good, bad = 0, 0

        for o in globalz.MP3_OBJ_LIST:

            if o.result == MP3File.QRY_RESULT.FIELDS_CHANGED:

                tmp_alb[o.clean_track.album] += 1
                good += 1

            else:
                bad += 1

        total_time_secs = self.end_time - self.start_time
        if total_time_secs <= 0: total_time_secs = 1
        total_time_min = int(total_time_secs / 60)
        and_time_secs = int(total_time_secs - (total_time_min * 60))

        self.start_time = 0
        self.end_time = 0
        mylog.INFO('STATS: elapsed secs: %d' % (total_time_secs))
        mylog.INFO('STATS: elapsed %d:%d' % (total_time_min, and_time_secs))
        mylog.INFO('STATS: total good albums: %d' % len(tmp_alb))
        mylog.INFO('STATS: total good tracks: %d' % good)
        mylog.INFO('STATS: total bad tracks: %d' % bad)
        

#################################

def guiMain():
    mylog.initLog(globalz.LOG_NAME)

    # initialize some of the multithread necessary evil globalz
    globalz.MP3_MUTEX = threading.Lock()
    globalz.WorkDoneEvent, globalz.EVT_WORK_DONE = wx.lib.newevent.NewEvent()
    globalz.StatusUpdateEvent, globalz.EVT_STATUS_UPDATE = wx.lib.newevent.NewEvent()
    globalz.CANCEL_EVENT = threading.Event()
      
    wxapp = wx.App()

    main_app = MainApp()
    main_app.SetPosition((100,100))
    main_app.Show()

    wxapp.MainLoop()

    mylog.closeLog()
