import sys

###### LOGGING 

LOG_FILE = sys.stdout
LOG_NAME = 'mp3scrub.log'
LOG_DEBUG = 2

###### STRINGS

MAX_STR_DIST = 5
DIV_STR_DIST = 5

###### GUI
MAX_EVT = 22 
MAXROWS = 25000

MP3_MUTEX = None
CANCEL_EVENT = None

SUBJECT_LIST = {}
MP3_OBJ_LIST = []

EVT_WORK_DONE = None
EVT_STATUS_UPDATE = None
StatusUpdateEvent = None
WorkDoneEvent = None

###### QUERY

API_KEY = '774d32a61d43cd8bd61523a1c5e7f7f1'
MUSICDNS_KEY = '03a1344bad8caaea06299360c9530c8f'

MAX_POTENTIAL_ALBUM_MATCH = 1
MAX_ALBUM_MATCH = 20 

###### CACHING

CACHE_DEBUG_ON = False
PERSIST_CACHE_ON = False

PICKLE_FILE = 'artists.pkl'
ALBUM_GUESS_LIMIT = 20

