"""
    HDXMedia classes wrap around files (or image sequences) to provide rich functionality
    and Lucy communication (via Mavis, acting as a proxy).
"""
import re
import os
from glob import glob

from hdxutils import HDXBaseMedia, HDXError

##-------------
##  Sequences
##-------------

sequencePattern = re.compile('(\d+|%\d{2}d)\.(\w{1,4})$')

class HDXSequence(HDXBaseMedia):
    """
        A single image sequence.
    """

    start = None
    end = None
    """ Defines the frame range of the sequence. """

    renderStart = None
    renderEnd = None
    """ Optionally limit the frame range to render. """

    totalFrames = 0

    shotName = None
    """ Possible shot name parsed from sequence name. """

    __shotNamePattern = re.compile('^([^_\W]+)_?(?:plt\d+?|plate\d+?|bg\d+?|fg\d+?)?([^_\W]+)?')

    def __init__(self, *args, **kwargs):
        super(HDXSequence, self).__init__(*args, **kwargs)

        # replace individual file name with sprintf notation.
        if os.path.isfile(self.path):
            frame = sequencePattern.search(self.path).group(1)
            self.path = self.path.replace(frame, '%%0%dd' % len(frame))
            self._parsePath()

        # determine start and end frame from sequence.
        if 'start' not in kwargs or 'end' not in kwargs or kwargs['start'] is None or kwargs['end'] is None:
            files = [os.path.basename(f) for f in glob(sequencePattern.sub(r'*.\2', self.path))]

            for file in files:
                frame = int(sequencePattern.search(file).group(1))

                if 'start' in kwargs and kwargs['start'] is not None: self.start = kwargs['start']
                elif self.start is None: self.start = frame
                else: self.start = min(self.start, frame)

                if 'end' in kwargs and kwargs['end'] is not None: self.end = kwargs['end']
                elif self.end is None: self.end = frame
                else: self.end = max(self.end, frame)
        else:
            self.start = kwargs['start']
            self.end = kwargs['end']

        self.totalFrames = self.end - self.start + 1

        # default is to render everything.
        self.renderStart = self.start
        self.renderEnd = self.end


    def parseName(self, prefix=None):
        """ Parse the name property to remove sprintf notation and shot name.
            
            Also optionally add a prefix IF the name does not already contain
            a prefix from a list of common prefixes.
        """

        if not self.shotName: self.parseShotName()

        # remove sprintf notation and extension.
        name = sequencePattern.sub('', self.name).lower()

        # remove shot name
        normalizedShotName = self.shotName.lower()
        for s in ['_','-',' ']:
            normalizedShotName = normalizedShotName.replace(s,'')
            name = name.replace(s,'')
        name = name.replace(normalizedShotName, '').strip(' ._')

        # add prefix
        if prefix and not any(s in name for s in ['plt','plate','fg','bg']):
            name = '%s_%s' % (prefix, name)

        return name

    def parseShotName(self):
        """ Parse the name property to extract a possible shot name. """

        # shot names are generally composed of an alpha prefix and number identifier.
        prefix, number = self.__shotNamePattern.match(self.name).group(1, 2)
        if not number: number = ''

        shotName = ''.join([prefix, '_', number]).strip('_').lower()
        if '_' not in shotName:
            shotName = re.compile('(\d+)').sub(r'_\1', shotName)

        self.shotName = shotName
        return shotName

    def view(self, detach = True):
        """ Launch Tweak's RV to view the sequence.
        
            Use `detach = False` to cause this function to wait
            until the user has terminated RV manually.
        """

        if self.exists():
            import subprocess
            
            if detach: subprocess.Popen(['rv', self.path])
            else: subprocess.call(['rv', self.path])
            
            return True
        
        else: return False

    def render(self, destination, **options):
        """ Use Nuke to render the sequence into the HDX Internal format.
        
            Note: to use this and other render methods, the script MUST run
            via Nuke's embedded python interpreter.

            $ nuke -t /path/to/script
        """

        nuke = self._importNuke().read(self, **options)
        renderPath = nuke.writeHDXFormat(destination)
        nuke.render()

        return renderPath

    def renderMavisThumbnails(self, components = None):
        """ Use Nuke to convert the sequence into Mavis Thumbnail.

            Use the thumbnail for given components - this requires that
            those components be contained in the sequence's path.
        """
        
        from shutil import copyfile

        if not components: components = [self.type]

        # render to the first component...
        HDXNuke = self._importNuke()
        nuke = HDXNuke.read(self)
        thumbnail, strip = nuke.writeMavisThumbnails(self.getPath(components[0]))
        nuke.render()

        # copy to the rest.
        for component in components[1:]:
            componentMavisDirectory = os.path.join(self.getPath(component), HDXNuke.MAVIS_DIR)

            if not os.path.isdir(componentMavisDirectory):
                os.mkdir(componentMavisDirectory)
            
            copyfile(
                thumbnail,
                os.path.join(componentMavisDirectory, os.path.basename(thumbnail)))

            copyfile(
                strip,
                os.path.join(componentMavisDirectory, os.path.basename(strip)))

    def exists(self, component = None):
        """ Overwrite `exists` to account for sprintf notation. """

        if not component:
            return os.path.exists(self.path % self.start)
        else:
            return os.path.exists(self.getPath(component))

    def _importNuke(self):
        try:
            HDXNuke = __import__('hdxnuke')
        except ImportError:
            raise HDXError('Method cannot run outside of Nuke runtime. Launch script with `nuke -t`.')

        return HDXNuke


class HDXSequenceList(HDXBaseMedia):
    """
        A list of image sequences - usually representing
        a directory containing multiple sequences.
    """

    list = []
    """ Contains the list of HDXSequences found in the given path """

    def __init__(self, *args, **kwargs):
        super(HDXSequenceList, self).__init__(*args, **kwargs)

        if os.path.isfile(self.path):
            self.list = [HDXSequence(self)]
            return
        elif os.path.isdir(self.path): files = os.listdir(self.path)
        else: 
            files = [os.path.basename(f) for f in glob(sequencePattern.sub(r'*.\2', self.path))]
            self.path = os.path.dirname(self.path)

        # group files into sequences with start and end frame numbers.
        sequences = {}
        for file in files:
            matches = sequencePattern.search(file)
            frame = matches.group(1)
            intFrame = int(frame)
            sequence = file.replace(frame, '%%0%dd' % len(frame))

            if sequence not in sequences: sequences[sequence] = [intFrame, intFrame]
            else:
                sequences[sequence][0] = min(sequences[sequence][0], intFrame)
                sequences[sequence][1] = max(sequences[sequence][1], intFrame)

        for basename, frames in sequences.iteritems():
            self.list.append(HDXSequence(os.path.join(self.path, basename), self.mavis, start=frames[0], end=frames[1]))

    def __iter__(self):
        for sequence in self.list:
            yield sequence

    def __getitem__(self, index):
        return self.list[index]

    def __len__(self):
        return len(self.list)

class HDXImage(HDXBaseMedia):
    """
        A single still image.
    """

    def __init__(self, *args, **kwargs):
        super(HDXImage, self).__init__(*args, **kwargs)

class HDXMovie(HDXBaseMedia):
    """
        A single movie file (usually quicktime).
    """

    def __init__(self, *args, **kwargs):
        super(HDXMovie, self).__init__(*args, **kwargs)
