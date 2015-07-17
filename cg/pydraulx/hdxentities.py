"""
    HDX Entities expose the Mavis API, providing useful methods for
    interacting with both the Mavis database and the HDX filesystem.
"""

import os
from datetime import date

from hdxutils import HDXPath, HDXBaseEntity, HDXBaseVirtualEntity, HDXError
from hdxmedia import HDXSequence, HDXImage, HDXMovie

##-------------------------------
##  PHYSICAL DIRECTORY ENTITIES
##-------------------------------

class HDXProject(HDXBaseEntity):
    """
        The Project is the top-level of organization in Mavis and in the filesystem.

        Projects are located within shared NFS mounts and symlinked to /hdx/projects.
        To this end, it is necessary to create a project by providing a path starting
        with a valid mount point (/mnt/x3 for example).
    """

    type = 'projects'

    def __init__(self, *args, **kwargs):
        super(HDXProject, self).__init__(*args, **kwargs)

    def make(self, metadata = None):
        """
            Add mount point validation to HDXBaseEntity.make
        """

        matches = re.compile('\/mnt\/[xz]\d+').match(self.source)
        if not matches or not os.path.ismount(matches.group(0)):
            raise HDXError('HDXProject.make invalid source [%s]' % self.source)
        else:
            super(HDXProject, self).make(metadata)

class HDXShot(HDXBaseEntity):
    """
        Shots are the primary containing entity for work done by 2D artist.
    """

    type = 'shots'

    def __init__(self, *args, **kwargs):
        super(HDXShot, self).__init__(*args, **kwargs)

class HDXAsset(HDXBaseEntity):
    """
        Assets are the primary containing entity for work done by 3D artist.
    """

    type = 'assets'

    def __init__(self, *args, **kwargs):
        super(HDXAsset, self).__init__(*args, **kwargs)

class HDXOffline(HDXBaseEntity):
    """
        Offlines contain an edit of all shots in a sequence - a child of HDXProject.
    """

    type = 'offlines'

    def __init__(self, *args, **kwargs):
        super(HDXOffline, self).__init__(*args, **kwargs)

class HDXReference(HDXBaseEntity):
    """
        References may contain client or internal references - a child of HDXProject.
    """

    type = 'references'

    def __init__(self, *args, **kwargs):
        super(HDXReference, self).__init__(*args, **kwargs)


class HDXAttribute(HDXBaseEntity):
    """
        Attributes are the building blocks of shots and assets - e.g. a 3D model, matte painting, background plate, etc.
    """

    type = 'attributes'

    versions = {}

    def __init__(self, *args, **kwargs):
        super(HDXAttribute, self).__init__(*args, **kwargs)

        if self.exists():
            self.__loadVersions()

    def publish(self, source, metadata = {}, fileName = None, copySource = False, publishType = 'MASTER'):
        """
            Create a new HDXAttributeVersion of given publishType, optionally copying the source file into the new directory.
        """

        # the metadata field 'versions' is the current max version number - increment it.
        v = (self.getMetadata('versions') or 0) + 1
        self.versions[v] = HDXAttributeVersion(self, str(v))
        self.versions[v].fileName = fileName

        # add source and publishType to metadata and create.
        metadata.update({'source':source,'publishType':publishType})
        self.versions[v].make(metadata, copySource = copySource)

        # manually update in-memory metadata. somewhat fragile.
        self.metadata['attributes']['versions'] = v
        if publishType == 'MASTER':
            self.metadata['attributes']['masterVersion'] = v
            self.versions['MASTER'] = self.versions[v]

        return self.versions[v]

    def __loadVersions(self):
        """
            Retrieve all HDXAttributeVersion children of this (existing) HDXAttribute
        """

        versions = [v+1 for v in range(self.getMetadata('versions'))]
        for v in versions:
            self.versions[v] = HDXAttributeVersion(self, str(v))

            if not self.versions[v].exists():
                raise HDXError('%s version %d exists in Mavis, but not on the filesystem. Seek help.' % (self.__name__, v))

        self.versions['MASTER'] = self.versions[self.getMetadata('masterVersion')]

##--------------------------
##  PHYSICAL FILE ENTITIES
##--------------------------

class HDXAttributeVersion(HDXBaseEntity):
    """
        A published working file, containg the "raw material" of an attribute (e.g. a Maya file, image sequence, etc.)

        Do not create this class directly! Instead, use HDXAttribute.publish().
    """

    type = 'versions'

    def __init__(self, *args, **kwargs):
        super(HDXAttributeVersion, self).__init__(*args, **kwargs)
    
    def make(self, metadata = None, **params):
        """ Extend basic make behavior to add the fileName when copying the source. """

        if (metadata and
            metadata.source and
            params.copySource == True and
            self.fileName is None):
            self.fileName = os.path.basename(metadata.source)

        super(HDXAttributeVersion, self).make(metadata, **params)

    def __int__(self):
        return int(self.name)

class HDXDaily(HDXBaseEntity):
    """
        Dailes are generated by artists and reviewed by supervisors. They are children of either shots or assets.
    """

    type = 'dialies'

    def __init__(self, *args, **kwargs):
        super(HDXDaily, self).__init__(*args, **kwargs)

        self.source = HDXMovie(self.source, self.mavis)

    def make(self, metadata, options = {}):
        """
            Extend basic make behavior to include rending of the source (an HDXMovie).
        """

        self.path = os.path.join(self.paths['shots'] or self.paths['assets'], 'dailies', str(date.today()), self.source.fileName)
        self._parsePath()

        super(HDXDaily, self).make(metadata, options)
        self.source.render(title='HDX Daily')

##--------------------
##  VIRTUAL ENTITIES
##--------------------

class HDXTask(HDXBaseVirtualEntity):
    """
        A task is a unit of work assigned to an artist by a supervisor.
    """

    type = 'tasks'

    def __init__(self, *args, **kwargs):
        super(HDXTask, self).__init__(*args, **kwargs)

class HDXNote(HDXBaseVirtualEntity):
    """
        A note my apply to any (or many) HDX Entity, providing feedback from clients or supervisors.
    """

    type = 'notes'

    def __init__(self, *args, **kwargs):
        super(HDXNote, self).__init__(*args, **kwargs)
