'''Helper classes to simplify XML I/O (last.fm and config files)'''

from xml.dom.minidom import parse, parseString, getDOMImplementation, Element, Node, Document
import xml.parsers.expat
import os.path
from mp3scrub import globalz
from mp3scrub.util import mylog, strtool
from mp3scrub.util.musicTypes import MP3File


def safeChildGet(parent_node, child_name):
    '''handy function to get the txt of a child txt node. returns '' if not found''' 

    child_nodes = parent_node.childNodes

    for child_node in child_nodes:
        if child_node.nodeName != child_name: continue

        tmp = child_node.firstChild
        if tmp:
            return tmp.nodeValue

    return ''


class AbsXMLNode(object):
    '''Abstract Node representation. Makes a tiny 1node-xmldoc that can be
    added to a larger xml doc.
    '''
             
    def __init__(self):
       self.elm = getDOMImplementation().createDocument(None, None, None)

    def __str__(self):
       return self.toString()

    def __del__(self):
       self.elm.unlink()

    def toString(self):
       raise NotImplementedError("abstract base class. toString Not implemented")




class HashXMLNode(AbsXMLNode):
    '''unused for now. orginially stored all mp3s in XML format first, not in memory''' 

    def __init__(self, _mp3_path, _dup_flag, _hash):
        AbsXMLNode.__init__(self)
        self.node_dict = {'path'    : str(_mp3_path),
                          'dupFlag' : str(_dup_flag),
                          'hash'    : str(_hash)}

        # setup a tiny XML doc of one node that will be appended to bigger one later 
        mp3_node = self.elm.createElement('mp3')

        for node_name in sorted(self.node_dict):
            node_obj = self.elm.createElement(node_name)
            node_val_txt = self.elm.createTextNode(self.node_dict[node_name])
            node_obj.appendChild(node_val_txt)
            mp3_node.appendChild(node_obj)

        self.elm.appendChild(mp3_node)

    def toString(self):
        return self.elm.toprettyxml(indent='  ') 



class MP3FileNode(AbsXMLNode):
    '''reprsents one mp3 file (tags + path). used to persist an editing session''' 

    def __init__(self, mp3_file_obj):

        AbsXMLNode.__init__(self)

        # setup a tiny XML doc of one node that will be appended to bigger one later 
        mp3_node = self.elm.createElement('mp3')

        for i,node_name in enumerate(MP3File.getFieldLabels()): 
            node_obj = self.elm.createElement(strtool.sanitizeTrackStr(node_name))
            txt = unicode(mp3_file_obj.getFieldList()[i]).encode('utf-8').strip()

            node_val_txt = self.elm.createTextNode(txt)
            node_obj.appendChild(node_val_txt)
            mp3_node.appendChild(node_obj)

        self.elm.appendChild(mp3_node)
   
    def toString(self):
        return self.elm.toprettyxml(indent='  ')



 
class XMLWriter(object):
    '''class to manage XMLNodes, creates a full xml doc and writes to file'''
 
    def __init__(self, _config_path):
        self.config_file = open(_config_path, 'w')
        self.xml_dom = getDOMImplementation().createDocument(None, None, None)
        self.root_xml_node = self.xml_dom.appendChild(self.xml_dom.createElement('list'))


    def __str__(self):
        s = self.__class__.__name__ 
        return s

    def doesNodeValExist(self, node_name, node_val):

        for node_obj in self.root_xml_node.getElementsByTagName(node_name):

            child_node_obj = node_obj.firstChild

            if not child_node_obj:
                mylog.MSG('child_node_obj is none...possible error')
                continue

            else:
                try:
                    if child_node_obj.nodeValue == node_val:
                        return True

                except (ValueError, TypeError):
                    continue

        return False   

    def addNode(self, node_obj):
        self.root_xml_node.appendChild(node_obj.elm.firstChild)
 
    def flush(self):
        self.xml_dom.writexml(self.config_file, indent='  ', addindent='  ', newl='\n', encoding='utf-8')
 
    def close(self):
        self.flush()
        self.xml_dom.unlink()
        self.config_file.close()




class XMLReader(object):
    '''Helper to sort through XML files.

        use xmlStr if inputting an xmldoc as a string
        use xmlFile if inputting xmldoc as a file
    ''' 

    def __init__(self, **kwargs):
        self.dom = None

        if 'xmlFile' in kwargs:

            with open(kwargs['xmlFile'], 'r') as config_file:
                try:
                    self.dom = parse(config_file)

                except xml.parsers.expat.ExpatError:
                    mylog.ERR('failed to load XML file %s' % kwargs['xmlFile'])
                    raise


        elif 'xmlStr' in kwargs:
            self.dom = parseString(kwargs['xmlStr'])

        else:
            raise Exception, 'invalid XMLReader constructor args'

    def getTheseNodes(self, node_name):
        return self.dom.getElementsByTagName(node_name)

    @staticmethod
    def strToBool(the_str):
        dictX = {'true' : True, 'false' : False}
    
        trimmed =  the_str.strip().lower() 
        if trimmed in dictX.keys():
            return dictX[trimmed]
        else:
            return the_str.strip()

    def __del__(self):
        self.dom.unlink()

    def close(self):
        self.__del__()

 
if __name__ == '__main__':
    fxn = TagXMLNode('nirvana','bleach','schools out', 3, '/home/users/gawnsen/fuck.mp3')
    fxn2 = TagXMLNode('nirvana','bleach','about a girl', 4, '/home/users/gawnsen/fuck2.mp3')
    wrtr = ConfigWriter('fuck.txt')
    wrtr.addNode(fxn)
    wrtr.addNode(fxn2)
    print str(wrtr.doesNodeValExist('artist','nirvana'))
    print str(wrtr.doesNodeValExist('artixst','nirvana'))
    print str(wrtr.doesNodeValExist('artist','nirvana'))
    print str(wrtr.doesNodeValExist('track','3'))
    wrtr.close()
    del fxn
    del fxn2
    quit()
