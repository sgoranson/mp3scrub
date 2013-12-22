'''logging. maybe replace with \'import logging\''''

from mp3scrub import globalz
import sys
import time

def initLog(file_name=''):
   if file_name: 
       try:
           globalz.LOG_FILE = open(file_name, 'a')    
       except:
           print 'log open failure'
           globalz.LOG_FILE = sys.stdout

   print >> globalz.LOG_FILE, 'initLog: ', time.ctime()

def closeLog():
   if globalz.LOG_FILE:
      try:
         globalz.LOG_FILE.close()
      except:
         print 'log close failure'

def LOC():
   loc = sys._getframe(1).f_lineno
   func = sys._getframe(1).f_code.co_name
   ret = '%s\@%s' % (loc,func)
   return ret

def DBG(*txt):
   try:
      if globalz.LOG_DEBUG >= 8: 
         print >> globalz.LOG_FILE, 'DBG: ',
         for arg in txt: print >> globalz.LOG_FILE, arg.encode('utf-8'),' ', 
         print >> globalz.LOG_FILE

   except UnicodeDecodeError:
      pass


def DBG1(lvl,*txt):
   try:
      if globalz.LOG_DEBUG >= lvl: 
         print >> globalz.LOG_FILE, 'DBG1: ',
         for arg in txt: print >> globalz.LOG_FILE, arg.encode('utf-8'),' ', 
         print >> globalz.LOG_FILE

   except UnicodeDecodeError:
      pass

def MSG(*txt):
   try:
      if globalz.LOG_DEBUG >= 6: 
         print >> globalz.LOG_FILE, 'MSG: ',
         for arg in txt: print >> globalz.LOG_FILE, arg.encode('utf-8'),' ', 
         print >> globalz.LOG_FILE

   except UnicodeDecodeError:
      pass

def INFO(*txt):
   try:
      if globalz.LOG_DEBUG >= 2:
         print >> globalz.LOG_FILE, 'INFO: ',
         for arg in txt: print >> globalz.LOG_FILE, arg.encode('utf-8'),' ', 
         print >> globalz.LOG_FILE

   except UnicodeDecodeError:
      pass


def WARN(*txt):
   try:
      if globalz.LOG_DEBUG >= 0:
         print >> globalz.LOG_FILE, 'WARN: ',
         for arg in txt: print >> globalz.LOG_FILE, arg.encode('utf-8'),' ', 
         print >> globalz.LOG_FILE

   except UnicodeDecodeError:
      pass

def ERR(*txt):
   try:
      if globalz.LOG_DEBUG >= 0:
         print >> globalz.LOG_FILE, 'ERR: ',
         for arg in txt: print >> globalz.LOG_FILE, arg.encode('utf-8'),' ', 
         print >> globalz.LOG_FILE

   except UnicodeDecodeError:
      pass

def STDERR(*txt):
   try:
      for arg in txt: print >> sys.stderr, arg.encode('utf-8'),' ', 
      print >> sys.stderr

   except UnicodeDecodeError:
      pass
