"""
    General Utility Functions and Base Classes for HDXEntities and HDX Media Classes.
"""

import sys
import os
import re
from collections import deque

from mavis import Mavis

class HDXPath(object):
    """
        Base Class for all HDX Entities (physical and virtual) and HDX Media Classes.
    """

    mavis = None
    """An instance of the Mavis class, used to communicate with the Mavis server."""

    path = None
    """Absolute path, the primary identity and string representation of the class."""
   
    source = None
    """The path, as given to HDXPath.__init__ before any manipulation"""
    
    type = None
    """Derived from path (or set by subclass) - the containing or "category" directory."""

    name = None
    """Derived from path - the terminating or "name" directory."""

    fileName = None
    """Derived from path - a specific file (or sprintf-notation sequence name) inside the "name" directory."""

    components = {}
    """Component names indexed by type."""

    paths = {}
    """Component paths indexed by type."""

    metadata = {}
    """Mavis metadata for this and all component entities."""

    def __init__(self, source, name = None, mavis = None, **kwargs):
        """
            It is possible to initialize an HDXPath instance using a string specifying the
            source path OR another HDXPath instance. When using a string, an authenticated
            Mavis instance may also be passed.
        """

        self.__name__ = self.__class__.__name__

        if isinstance(source, HDXPath):
            self.mavis = source.mavis

            # copy metadata to reduce bandwidth.
            if source.exists():
                self.metadata = dict(source.metadata)

        elif not isinstance(source, str):
            raise HDXError('HDXPath first arg must be HDXPath or String (source).')

        # save source, begin path construction - child classes may specify a type.
        self.path = self.source = str(source)
        if not isinstance(name, Mavis) and self.type: self.path = os.path.join(self.path, self.type)

        # join name to path, store Mavis instance.
        if name:
            if isinstance(mavis, Mavis):
                if not self.mavis: self.mavis = mavis
            elif mavis is not None:
                raise HDXError('HDXPath third arg must be Mavis.')

            if isinstance(name, Mavis):
                if not self.mavis: self.mavis = name
            elif isinstance(name, str):
                self.path = os.path.join(self.path, name)
            else: raise HDXError('HDXPath second arg must be Mavis or String (name).')

        self._parsePath()

    def getPath(self, component = None, mavis = False):
        if component:
            try:
                path = self.paths[component]
            except KeyError:
                path = None
        else: path = self.path

        # Mavis stores certain metadata (thumbnails, strips, etc.) in a hidden directory.
        if mavis: path = os.path.join(path, Mavis.directory)

        return path

    def exists(self, component = None):
        return os.path.exists(self.getPath(component))

    def _parsePath(self):
        """
            Normalize and extract component information from self.path.
        """

        pattern = r"(?:(?:\/?hdx\/)|(?:\/?mnt\/[xz]\d+\/))?\/?projects\/"
        self.path = re.sub(pattern, os.path.join(os.path.sep,'hdx','projects',''), self.path)

        # first element after split is an empty string, the second is 'hdx'.
        components = self.path.split(os.path.sep)[2:]
        
        # non-even components indicate the presence of a file name.
        if (len(components)) % 2 == 1:
            self.fileName = components[-1:][0]
            components = components[:-1]

        # break the path up into (component, name) pairs.
        for i in xrange(0,len(components),2):
            self.components[components[i]] = components[i+1]
            self.paths[components[i]] = os.path.sep + os.path.join('hdx',*components[:i+2])

            # the last iteration yields the type (if not already defined) and name.
            if i == (len(components)-2):
                self.name = components[i+1]
                if not self.type: self.type = components[i]
                elif self.type != components[i]:
                    raise HDXError('%s defined type [%s] does not match parsed type [%s]' % (self.__name__, self.type, components[i]))

        # self.name may also be the file name.
        if os.path.splitext(self.name)[1] != '': self.fileName = self.name

    def __ls(self, path, directory, linkTable):
        """
            Call the underlying Mavis.ls method, storing results under self[directory].
        """

        try:
            self[directory] = self._callMavis('ls', path, directory, linkTable)
        except MavisError as e:
            if e.errno == 404: self[directory] = None
            else: raise e

        # break out 'all' into separate properties.
        if directory == 'all':
            for dir, list in self['all'].items():
                self[dir] = list
            del self['all']
            return True

        return self[directory]

    def _callMavis(self, method, *args, **params):
        """
            Execute a call to Mavis. Raises HDXError if no Mavis instance exists.
        """

        if not self.mavis: raise HDXError('%s requires an authenticated Mavis instance to call `%s`.' % (self.__name__, method))
        else: 
            return getattr(self.mavis, method)(*args, **params)

    def __str__(self):
        return self.path


class HDXBaseEntity(HDXPath):
    """
        Base Class for all Physical HDX Entities - entities present both in Mavis and on the filesystem.
    """

    def __init__(self, *args, **kwargs):
        super(HDXBaseEntity, self).__init__(*args, **kwargs)

        if not self.mavis:
            raise HDXError('%s must be supplied with an authenticated Mavis instance.' % self.__name__)

        if self.exists():
            self.__loadMetadata()

    def getMetadata(self, field = None, component = None, default = None):
        """
            Return metadata - optionally a specific field from a specific component.
        """

        # metadata from a this entity, a component entity, or no matching component.
        if component:
            try: data = self.metadata[component]
            except KeyError: return default
        else: data = self.metadata[self.type]
      
        # single metadata field, all fields, or no matching field.
        if field:
            try: value = data[field]
            except KeyError: return default
        else: value = data

        return value

    def make(self, metadata = None, **params):
        """
            Create this entity via a call to Mavis.
            
            Raises OSError if entity already exists.
        """

        if self.exists():
            raise OSError(17, '%s already exists.' % self.__name__, self.path)

        # projects make their source directory and symlink it into /hdx/
        if self.__name__ == 'HDXProject': path = self.source
        else: path = self.path

        self.metadata[self.type] = self._callMavis('mk', path, metadata, **params)

    def update(self, metadata, **params):
        """
            Update metadata (i.e. non-filesystem data).
        """
        self.metadata[self.type].update(metadata)
        self._callMavis('update', self.path, metadata, **params)
        
    def move(self, destination):
        """
            Alias for __moveOrCopy
        """
        self.__moveOrCopy('mv', destination)

    def copy(self, destination):
        """
            Alias for __moveOrCopy
        """
        self.__moveOrCopy('cp', destination)

    def remove(self, source = False):
        """
            Remove entity (or entity source). Returns True if successfully removed, False if not.

            Raises no errors and returns True if entity (or source) does not exist.
        """

        if source: path = self.source
        else: path = self.path

        if os.path.exists(path):
            return self._callMavis('rm', path)
        else: return True

    def list(self, directory, linkTable = None):
        """
            List all "virtual" HDX Entities under a virtual directory. 
        """
        return self.__ls(self.path, directory)

    def __moveOrCopy(self, method, destination):
        """
            Move or Copy this entity to destination via a call to Mavis.

            Raises OSError if destination exists, HDXError if it would change the entity's type.
        """

        if not isinstance(destination, HDXPath):
            destination = HDXPath(destination)

        if destination.exists():
            raise OSError(17, '%s.%s - destination exists.' % (self.__name__, method), self.path)

        if destination.type != self.type:
            raise HDXError('%s.%s cannot alter entity type - [%s to %s]' % (self.__name__, method, self.type, destination.type))

        # update metadata, path, and components.
        self.metadata[self.type] = self._callMavis(method, self.path, destination.path)
        self.path = self.metadata[self.type]['path']
        self._parsePath()

    def __loadMetadata(self):
        """
            Load metadata from Mavis - only for components that do not already have metadata.
        """

        # to reduce bandwidth usage and database roundtrips, only get metadata for this entity.
        if self.metadata:
            self.metadata[self.type] = self._callMavis('get', self.path)[self.type]
        else:
            self.metadata = self._callMavis('get', self.path, iterate=True)

class HDXBaseVirtualEntity(HDXBaseEntity):
    """
        Base class for all Virtual HDX Entities - entities present only in Mavis, not on the filesystem.
    """

    def __init__(self, *args, **kwargs):
        """
            A virtual entity's path must NOT contain "virtual" directories.
        """

        super(HDXBaseVirtualEntity, self).__init__(*args, **kwargs)
        
        components = self.path.split(os.path.sep)
        self.path = os.path.join(os.path.sep, *components[:components.index(self.type)])
        self.paths[self.type] = self.path

        # the parent constructor will never call __loadMetadata because self.exists() will
        # always return False - this version of __loadMetadata also checks for existence.
        self.__loadMetadata()

    def exists(self, component = None, forceCheck = False):
        """
            Mavis must be queried to determine existence of virtual entities.
        """

        # all sub-components of a virtual entity are physical.
        if component and component != self.type:
            return super(HDXBaseVirtualEntity, self).exists(component)

        # forcing a check requires a roundtrip to Mavis - only use when necessary.
        if forceCheck is True:
            try:
                self._callMavis('get', self.path, entity=self.type, name=self.name)
            except MavisError as e:
                if e.errno == 404: self.__exists = False
                else: raise e
            self.__exists = True

        return self.__exists

    def list(self, directory, linkTable = None):
        """
            Virtual entities use their id (rather than path) to list related "directories."
        """
        return self.__ls('%s/%s' % (self.type, self.getMetadata('id')), directory, linkTable)

    def __loadMetadata(self):
        """
            Load metadata from Mavis - only for components that do not already have metadata.
        """

        params = {'entity':self.type,'name':self.name}
        
        if self.metadata:
            try:
                self.metadata[self.type] = self._callMavis('get', self.path, **params)[self.type]
            except MavisError as e:
                if e.errno == 404: self.__exists = False
                else: raise e
            self.__exists = True
        else:
            try:
                self.metadata = self._callMavis('get', self.path, iterate=True, **params)
            except MavisError as e:
                if e.errno == 404: self.__exists = False
                else: raise e
            self.__exists = True

    __exists = False


class HDXBaseMedia(HDXPath):
    """
        Base Class for all HDX Media Classes - classes representing working files that could be made deliverable.
    """

    jobDefaults = {}
    """Default options to pass to Mavis.lucy - subclasses will define these defaults."""

    def __init__(self, *args, **kwargs):
        super(HDXBaseMedia, self).__init__(*args, **kwargs)

    def render(self, destination, title = None, **jobOptions):
        """
            Submit a Lucy job to render this media instance using the given options.

            Returns the Lucy response - on success, the newly-created job's ID.
        """

        if not title: title = '[%s] Media Render' % self.__name__

        job = dict(self.jobDefaults.items() + jobOptions.items())
        job['title'] = title

        if 'command' not in job: job['command'] = '%s_render' % self.__name__.lower()
        
        # first positional argument to all render scripts is the
        # source path, second is the destination
        destination = os.path.join(str(destination), self.name)
        if 'args' not in job: job['args'] = [self.path, destination]
        else: job['args'] = [self.path, destination] + job['args']

        return self._callMavis('lucy', title, job)

class HDXLog(object):
    """ Provide access to various logging levels. """

    def info(self, message):
        sys.stdout.write(message + '\n')

    def error(self, message):
        sys.stderr.write(message + '\n')


class HDXError(Exception):
    """ Pass through class to easily identify HDX errors. """

    def __init__(self, message):
        Exception.__init__(self, message)
