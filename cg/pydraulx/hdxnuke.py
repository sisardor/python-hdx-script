"""
    Wrapper for Nuke's python module for working with HDX Entities and performing common HDX image processing tasks.

    BIG TODO: handle the options argument... 
              includes things like appending a slate, doing a resize, changing colorspace, pixel aspect ratio, etc etc.
"""

import os
import nuke

##-----------
## Settings 
##-----------

## HDX - Internal EXR ##
HDX_TYPE = 'exr'
HDX_COLORSPACE = 'linear'
HDX_BITDEPTH = 16

## Mavis - General ##
MAVIS_DIR = '.mavis'
MAVIS_TYPE = 'jpg'

## Mavis - Thumbnail ##
MAVIS_THUMB_X = 480
MAVIS_THUMB_Y = 270

## Mavis - Strip ##
MAVIS_STRIP_FRAMES = 50
MAVIS_STRIP_X = MAVIS_THUMB_X * MAVIS_STRIP_FRAMES
MAVIS_STRIP_Y = MAVIS_THUMB_Y

##-----------------------------------
##  Read - HDXNuke Factory Function
##-----------------------------------

def read(meda, **options):
    return HDXNuke(meda, **options)

##-----------------
##  HDXNuke Class
##-----------------

class HDXNuke:
    """ Represents a single Nuke script (node tree) operating on a single piece of media. """

    read = None
    writes = []

    def __init__(self, media, **options):
        """Initialize HDXNuke with a media entity (e.g. HDXSequence, HDXMovie, HDXImage, etc.) and options."""

        self.media = media
        self.options = options
        self.writes = []

        self.__read()

    def writeHDXFormat(self, destination):
        """ Create the standard HDX internal format - currently a 16-bit linear EXR sequence. """

        if self.media.__class__.__name__ != 'HDXSequence':
            raise NotImplementedError('Currently HDXNuke.writeHDXFormat only supports an HDXSequence input.')

        # coerce HDXEntities into strings.
        destination = str(destination)
        
        # destination is directory - sequence name from media source.
        if os.path.isdir(destination):
            name = os.path.splitext(self.media.name)[0]

        # destination contains a filename.
        elif os.path.isdir(os.path.dirname(destination)):
            name = os.path.splitext(os.path.basename(destination))[0]
            destination = os.path.dirname(destination)
        
        # alter the destination sequence's extension.
        destination = '%s.%s' % (os.path.join(destination, name), HDX_TYPE)
        
        self.__write(destination, first = self.media.renderStart, last = self.media.renderEnd)
        return destination

    def writeMavisThumbnails(self, destination):
        """ Create Mavis thumbnails for the web interface - a still frame and a contact strip. """

        mavisPath, mavisNode = self.__prepForMavis(str(destination))
        thumbnailPath = os.path.join(mavisPath, 'thumb.%s' % MAVIS_TYPE)
        stripPath = os.path.join(mavisPath, 'strip.%s' % MAVIS_TYPE)

        # thumbnail - uses middle frame.
        thumbnail = nuke.nodes.Reformat(
            type = 'to box',
            box_width = MAVIS_THUMB_X,
            box_height = MAVIS_THUMB_Y,
            resize = 'width',
            center = 'true',
            filter = 'Cubic')
        thumbnail.setInput(0, mavisNode)

        interestingFrame = MAVIS_STRIP_FRAMES / 2

        self.__write(
            thumbnailPath,
            input = thumbnail,
            file_type = MAVIS_TYPE,
            first = interestingFrame,
            last = interestingFrame)

        # contact strip.
        strip = nuke.nodes.ContactSheet(
            splitinputs = 'true',
            width = MAVIS_STRIP_X,
            height = MAVIS_STRIP_Y,
            rows = 1,
            columns = MAVIS_STRIP_FRAMES,
            startframe = self.media.renderStart,
            endframe = self.media.renderStart + MAVIS_STRIP_FRAMES)
        strip.setInput(0, mavisNode)
        
        self.__write(
            stripPath,
            input = strip,
            file_type = MAVIS_TYPE)

        return (thumbnailPath, stripPath)

    def __prepForMavis(self, path):
        """
            Retime input (and potentially do other stuff) to prepare input for use in creating Mavis elements.
        
            Creates the MAVIS_DIR directory where Mavis looks to find media elements.
        """

        retime = nuke.nodes.Retime(filter = 'nearest')
        retime['input.first'].setValue(self.media.renderStart)
        retime['input.last'].setValue(self.media.renderEnd)
        
        retime['output.first'].setValue(self.media.renderStart)
        retime['output.first_lock'].setValue(True)
        retime['output.last'].setValue(self.media.renderStart + MAVIS_STRIP_FRAMES)
        retime['output.last_lock'].setValue(True)

        retime.setInput(0, self.read)

        # potentially add more nodes...
        mavisNode = retime

        # create Mavis directory if needed.
        mavisPath = os.path.join(path, MAVIS_DIR)    
        if not os.path.isdir(mavisPath):
            os.mkdir(mavisPath)

        return (mavisPath, mavisNode)
    
    def __read(self):
        """Create read node."""

        if self.read:
            raise Exception('Each HDXNuke instance may read in only one main media element.')

        self.read = nuke.nodes.Read(file = self.media.path, first = self.media.start, last = self.media.end)

    def __write(self, destination, input = None, file_type = None, colorspace = None, first = 1, last = 1, interval = 1):
        """Append write node to self.writes for later rendering."""

        if not input:
            input = self.read
        if not file_type:
            file_type = HDX_TYPE
        if not colorspace:
            colorspace = HDX_COLORSPACE

        node = nuke.nodes.Write(
            file = destination,
            file_type = file_type,
            colorspace = colorspace,
            first = first,
            last = last,
            use_limit = 'true')

        node.setInput(0, input)
        self.writes.append((node, first, last, interval))

    def render(self):
        """Render all Write nodes - does not implement nuke.executeMultiple (yet) for stability."""

        for args in self.writes:
            nuke.render(*args)
