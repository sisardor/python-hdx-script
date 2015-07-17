import traceback
import os, sys
import functools
import copy
import argparse

sys.path.append("/hdx/cg/pydraulx")
sys.path.append("/hdx/cg/lucy_workstations/python2.6/lib/python2.6/site-packages/requests-2.1.0-py2.6.egg")
sys.path.append('/hdx/sys/lucy_scripts')
import imageHeaderInfo

import mavis
standalone=False

try:
    import nuke
except ImportError,e:
    standalone=True
'''
###example plate entity:
conn.find('/projects/test006/shots/tst001/plates/client')
[{u'publishes': [], u'name': u'client', u'links': [], u'updatedAt': None, u'createdBy': u'superuser', u'activity': [],
            u'input': {u'colorspace': u'Cineon', u'inX': 1920, u'inY': 1080, u'inPixelAspect': 2.3999999999999999, u'inFilter': 0, u'inCDL': 0},
            u'path': {u'name': u'client', u'collection': u'entities', u'file': None, u'directory': u'projects/test006/shots/tst001/plates',
                        u'path': u'/projects/test006/shots/tst001/plates/client', u'model': u'plates', u'root': u'/hdx'},
            u'_id': u'/projects/test006/shots/tst001/plates/client', u'createdAt': u'2014-06-18T01:04:14.999Z'}]

###example nodeDict {
    'read1' : {'nodeType':'Read', args=[], 'kwargs': {'file':'sequence', 'first':sfrm, 'last':efrm, 'colorspace':None, raw=0}  },
    'colourspace1' : {'nodeType':'Colorspace', args=[], 'kwargs': {'name':'Colorspace'}  },
    'writeLin' : {'nodeType':'Write', args=[], 'kwargs': {'raw': 1, 'file':"%s/%s_LIN.%s.exr" 0}  },
    'reformat1' : {'nodeType':'Reformat', args=[], 'kwargs': {'type':"scale", 'scale':scale}  },
    'writeProxy' : {'nodeType':'Write', args=[], 'kwargs': {'file':'sequence', 'first':sfrm, 'last':efrm, 'colorspace':None, raw=0}  },
}

#NB - ALWAYS resize in log colorspace, as it has an effect on the image.
#also certain rezolutions are only available to certain colorspaces - ie if it is size A the file is Cineon. etc etc

testPlatePath = "/mnt/x1/hdx/cg/maya/scripts/hdxBrowser/trevorDev/testPlate/TC_066_3115.%04d.dpx"

 ### example command line call
$ nuke -t /hdx/cg/lucy/scripts/convertImageSequence.py \
--source=/full/path/to/source/sequence.%04d.exr \
--dest=/projects/test006/shots/tst001/plates/client/publishes/0001/sequence.%04d.exr \
--entity=/projects/test006/shots/tst001/plates/client

#nuke -t /hdx/cg/lucy/scripts/convertImageSequence.py --source=/mnt/x1/hdx/cg/maya/scripts/hdxBrowser/trevorDev/testPlate/TC_066_3115.%04d.dpx --dest=/hdx/projects/test006/shots/tst001/plates/autoIngest/publishes/0039/sequence.%04d.exr --entity=/projects/test006/shots/tst001/plates/client
#new script:
/hdx/cg/scripts/nuke8args /hdx/sys/lucy_scripts/convertImageSequence.py --source /mnt/x1/hdx/cg/maya/scripts/hdxBrowser/trevorDev/testPlate --entity /projects/mavisTesting/shot/sh_ot1_012/plates/client1 --start 1001 --end null
'''

conn = mavis.Mavis('superuser', 'password')
#project defaults os a dict of external default values to be stored (somewhere) for plates.
#These are cascading /facility/project/shot values for entity (plate) settings
PROJECT_DEFAULTS = {'colorspace': 'Linear', 'xResolution': 1080, 'yResolution': 1080, 'pixelAspect': 1, 'filter': 0, 'CDL': 0}


def importPlateAction(*args, **kwargs):
    print "Welcome to importPlateAction. Live hot plate importing action. \nLadies and gentlemen here are your **kwargs:"
    if not kwargs:
        print "Problem! the dancing kwargs are missing"
        return False

    latest = kwargs['publishes'][-1]

    inputPath=None; outputPath=None; start=10; end=20
    inputValues=None; sampleFile=None

    #use hard coded defaults as a fallback
    workingValues=PROJECT_DEFAULTS

    #search for project defaults
    project = conn.find("/projects/%s" %str(mavisEntity['project']))
    if project and project.has_key('data'):
        if project['data'].has_key('defaults'):
            print "found defaults"
            print project['data']['defaults']['plates']
            if project['data']['defaults'] and project['data']['defaults'].has_key('plates'):
                workingValues=project['data']['defaults']['plates']
                print "setWorkingValues"

    sampleFile=''
    try:
        outputPath          = kwargs['publishes'][-1]['path']
        start                    = kwargs['publishArgs']['sfrm']
        end                     = kwargs['publishArgs']['efrm']
        srcPath               =kwargs['publishArgs']['source']

        inputValues             = kwargs['data']['originalMetadata']
        fileList =sorted([x for x in os.listdir(srcPath) if os.path.isfile(os.path.join(srcPath, x))])
        sampleFile = os.path.join(srcPath, fileList[ int(len(fileList)/2)-1 ] )
        print "sampleFile %s " %sampleFile

        if not inputValues:
            #we have nothing for information on the incoming plate
            #'input': {u'colorspace': u'Cineon', u'inX': 1920, u'inY': 1080, u'inPixelAspect': 2.3999999999999999, u'inFilter': 0, u'inCDL': 0}
            #is the  data['sfrm'] the same as the plate ?
            if not end or end == "null":
                end=int(start)+len(fileList)

            inputValues = imageHeaderInfo.imageHeader(sampleFile)
            updateDict = kwargs['data']
            #update the mavis plate entity with metadata values
            updateDict['originalMetadata']=inputValues
            #save this metadata out to mavis?
            #conn.put(kwargs['path'], {'data':updateDict})

    except Exception, e:
        print "ERROR: mavis entity has no input and working keys"
        print e
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, file=sys.stdout)

    tokens=sampleFile.rsplit(".",2)
    escape= "%0"+str(len(tokens[1]))+"d"
    sequence = "%s.%s.%s" %(tokens[0], escape, tokens[2])

    print "sequence %s" %sequence
    outputPath = os.path.join(outputPath, os.path.basename(sequence))
    outputPath =os.path.join("/mnt/x3/", outputPath)
    print '\n'
    print workingValues
    print '\n'
    #outformat = str ( "%d %d 1" %( xres, yres) )                               # output res and aspect ratio. "x y apspect"
    outformat = "%s %s %s" %(workingValues['xResolution'],  workingValues['yResolution'],  workingValues['pixelAspect'])
    #aspect_format = str ( "%d %d 1" %( xres, xres / ratio_aspect ) )               # aspect ratio matte
    #prot_format = str ( "%d %d 1" %( xres, xres / ratio_prot ) )


    #for testing purposes - possibly look in to project default if non existent
    #if not mavisEntity.has_key("working"):
    #    pass
        #workingValuef = {'colorspace': 'Linear', 'wX': 1920, 'wY': 1080, 'inPixelAspect': 2.4, 'inFilter': 0, 'inCDL': 0}
        #workingValues = {'colorspace': 'Linear', 'xResolution': 1080, 'yResolution': 1080, 'pixelAspect': 2.4, 'filter': 0, 'CDL': 0}
        #workingValues        = PROJECT_DEFAULTS
    #else:
    #    pass
        #workingValues       = mavisEntity['working']
    #added second reformat node. First one is if we are working at a different resolution than the input plate
    #second is for proxy plates


    if not mavisEntity.has_key("nukeNodes"):
        #NUKE NODES READ1 - changed to raw:0
        nukeNodes = {
            'read1' : {'nodeType':'Read', 'args':[], 'kwargs': {'file':'sequence', 'first':start, 'last':end, 'raw':0}  },
            'reformat1' : {'nodeType':'Reformat', 'args':[], 'kwargs': {'type':"to box", 'scale':'scale'}  },
            'colourspace1' : {'nodeType':'OCIOColorSpace', 'args':[], 'kwargs': {'name':'Colorspace'}  },
            'writeLin' : {'nodeType':'Write', 'args':[], 'kwargs': {'name':'writeLin', 'raw': 1, 'file':"%s/%s_LIN.%s.exr",  'first':start, 'last':end, 'raw':1 }  },
            'reformat2' : {'nodeType':'Reformat', 'args':[], 'kwargs': {'name': 'proxyResize', 'type':"scale", 'scale':'scale'}  },
            'CopyMetaData1': {'args': [], 'nodeType': 'CopyMetaData', 'kwargs': {'imageMetadatafilterMode': 'keys and values', 'metadatafilterMode': 'keys and values', 'mergeMode': 'Image+Meta'} },
            'writeProxy' : {'nodeType':'Write', 'args':[], 'kwargs': {'name':'writeProxy', 'file':'sequence', 'first':start, 'last':end, 'raw':1}  },
            }
    else:
        nukeNodes           = mavisEntity['nukeNodes']

    if not mavisEntity['type'] == 'plates':
        print "ERROR: attempting plate publish on non-plate entity"
        return False

    #update a copy of input with values from working. If they are the same, do nothing
    if copy.copy(inputValues).update(workingValues) != inputValues:
        #create default nodes in nuke (Read, Colorspace, Log2Lin, Resize, Write)
        for aNodeName, aNode in nukeNodes.iteritems():
            nukeNodes[aNodeName]['node'] = nodeFactory(aNode)

        #SET VALUES
        nukeNodes['read1']['node'].knob("file").setValue( sequence )
        print "start %s end %s" %(str(start), str(end))
        nuke.Root().knob('first_frame').setValue(float(start))
        nuke.Root().knob('last_frame').setValue(float(end))
        nuke.Root().knob('frame').setValue(float(start))

        #we will be dealing with nodeFlow[-1] to get the last node in the tree.
        #this means appending to the list whenever we connect anything to update the last item
        nodeFlow=[ nukeNodes['read1']['node'] ]

        #do the resize in CINEON colourspace as conversion then resize can crush color values
        #For this the best colorspace is pLogLin.
        print "line180 input and working"
        print inputValues
        print workingValues
        if inputValues['xResolution'] != workingValues['xResolution'] or inputValues['yResolution'] != workingValues['yResolution']:
            #add -> pLogLin colorspace conversion

            #create the colorspace sandwich Erik asked for
            reformatP_log_In = nodeFactory(nukeNodes['colourspace1'])
            reformatP_log_In.knob("in_colorspace").setValue("Linear")
            reformatP_log_In.knob("out_colorspace").setValue( "pLogLin")


            dst = nukeNodes['reformat1']['node']
            print "setting resize values %s %s %s"%(str(workingValues['xResolution']),  str(workingValues['yResolution']),  str(workingValues['pixelAspect']) )
            dst.knob("resize").setValue( "%s %s %s"%(str(workingValues['xResolution']),  str(workingValues['yResolution']),  str(workingValues['pixelAspect']) ))
            #resize type = box
            dst.knob('type').setValue(1)
            #set resize to none
            dst.knob('resize').setValue(1) #0=None, 1=width, 2=height, 3=fit, 4=fill, 5=distort
            dst.knob('box_width').setValue(float(workingValues['xResolution']))
            dst.knob('box_height').setValue(float(workingValues['yResolution']))
            dst.knob('box_fixed').setValue(1)
            dst.knob('box_pixel_aspect').setValue(float(workingValues['pixelAspect']))

            #do resize then back to original colorspace
            reformatP_log_Out = nodeFactory(nukeNodes['colourspace1'])
            reformatP_log_Out.knob("in_colorspace").setValue("pLogLin")
            reformatP_log_Out.knob("out_colorspace").setValue( "Linear")

            #connect Everything
            connectNodes(nodeFlow[-1], reformatP_log_In, 0)
            nodeFlow.append(reformatP_log_In)
            connectNodes(nodeFlow[-1], dst, 0)
            nodeFlow.append(dst)
            connectNodes(nodeFlow[-1], reformatP_log_Out, 0)
            nodeFlow.append(reformatP_log_Out)

            #if not connectNodes(nodeFlow[-1], dst, 0):
            #    print "NODE CONNECTION ERROR: reformat1 not connected"
            #else:
            #nodeFlow.append(dst)
            #NEED resize values
            #resize to the specified image width height
            #dst.knob('type').setValue(1)
            #dst.knob('box_width').setValue(1024)
            #dst.knob('box_height').setValue(1024)
            #dst.knob('box_fixed').setValue(1)
            #dst.knob("format").setValue( "%s %s %s"%(workingValues['inX'],  workingValues['inY'],  workingValues['inPixelAspect'] ))
            #x & y & pixel aspect - steal from Erik's code ( "x y aspect")

            dst.knob("black_outside").setValue( 1 )

            #if we have a value for filter, use the value specified otherwise use Lanczos
            filterType =  'Lanczos4'
            if inputValues.has_key('filter'):
                filterType = str(inputValues['filter'])
            dst.knob("filter").setValue( filterType ) #Lanczos4, Rifman

        '''
        if inputValues['colorspace'] != workingValues['colorspace']:
            dst = nukeNodes['colourspace1']['node']
            if not connectNodes(nodeFlow[-1], dst, 0):
                print "NODE CONNECTION ERROR: colourspace1 not connected"
            else:
                nodeFlow.append(dst)
                inCS = inputValues['colorspace']
                nukeNodes['colourspace1']['node'].knob("colorspace_in").setValue(str( inputValues['colorspace']) )
                nukeNodes['colourspace1']['node'].knob("colorspace_out").setValue( str(workingValues['colorspace']) )'''

        #work out our output path
        if str(workingValues['inputColorspace']) == "Linear":
            if os.path.splitext(outputPath)[1]==".dpx":
                outputPath = outputPath.replace(".dpx", ".exr")

        outputPath = "/mnt/x3" +outputPath
        print "outputPath: %s" %outputPath

        mdat = nukeNodes['CopyMetaData1']['node']
        readNode = nukeNodes['read1']['node']
        connectNodes(readNode, mdat, 1)
        if not connectNodes(nodeFlow[-1], mdat, 0):
            print "NODE CONNECTION ERROR: CopyMetaData1 not connected"
        else:
            nodeFlow.append(mdat)


        wrt = nukeNodes['writeLin']['node']
        if not connectNodes(nodeFlow[-1], wrt, 0):
            print "NODE CONNECTION ERROR: writeLin not connected"
        else:
            nodeFlow.append(wrt)
            wrt.knob("file").setValue( outputPath )
            wrt.knob("file_type").setValue( 'exr' )
            wrt.knob("compression").setValue( "PIZ Wavelet (32 scanlines)" )

            wrt.knob('first').setValue(float(start))
            wrt.knob('last').setValue(float(end))
            #wrt.knob('use_limit').setValue(True)

        proxyResize = nukeNodes['reformat2']['node']
        if not connectNodes(nodeFlow[-2], proxyResize, 0): #NB - this may need to be -2 not the write node, but the one above
            print "NODE CONNECTION ERROR: reformat1 not connected"
        else:
            nodeFlow.append(proxyResize)
            proxyX=int(float(workingValues['xResolution'])/2)
            proxyY=int(float(workingValues['yResolution'])/2)


            #format = "250 140 1"
            #proxyResize.knob("resize").setValue('resize')
            proxyResize.knob("scale").setValue( 0.5 )
            #proxyResize.knob("resize").setValue( "%s %s %s"%(proxyX,  proxyY,  workingValues['inPixelAspect'] ))
            #x & y & pixel aspect - steal from Erik's code ( "x y aspect")
            #dst.knob("center").setValue( center ) -- for publish plate we dont need to set center
            proxyResize.knob("black_outside").setValue( 1 )
            proxyResize.knob("filter").setValue( 'Rifman' )


        proxyWrt = nukeNodes['writeProxy']['node']
        pathSplit = os.path.split(outputPath)
        proxyPath = os.path.join(pathSplit[0], "proxies")
        if not os.path.exists(proxyPath):
            os.mkdir(proxyPath)
        proxyPath=os.path.join(proxyPath, pathSplit[1])
        if not connectNodes(nodeFlow[-1], proxyWrt, 0):
            print "NODE CONNECTION ERROR: writeProxy not connected"
        else:
            nodeFlow.append(proxyWrt)
            proxyWrt.knob("file").setValue( proxyPath )
            proxyWrt.knob("file_type").setValue( 'exr' )
            proxyWrt.knob("compression").setValue( "PIZ Wavelet (32 scanlines)" )
            print start
            proxyWrt.knob('first').setValue(float(start))
            proxyWrt.knob('last').setValue(float(end))
            #proxyWrt.knob('use_limit').setValue(True)

        #render srfm, efrm
        #outputs =either of the write nodes if they have an input connection
        outputs = [x for x in [nukeNodes['writeLin']['node'], nukeNodes['writeProxy']['node']]  if x.input(0) ]
        if outputs:
            #nuke.executeMultiple ((variable,), ([start,end,incr],))
            #nuke.executeMultiple([w, w2,], ([start - 1,stop,1],))
            print "Rendering: %s start=%s end=%s" %( str(outputs), str(start), str(end) )

            nuke.executeMultiple(outputs, ([int(start),int(end), 1],))
            #nuke.execute(nukeNodes['writeLin']['node'], int(start), int(end))
            #nuke.execute(nukeNodes['writeProxy']['node'], int(start), int(end))
            return True
        else:
            print "ERROR: No putput nodes connected"
            return False
    else:
        print "Input and working are identical. No operation"
        return True


# NUKE NODE CODE -----------------------------------------------------------------------------------------------------------------
def nodeFactory(nodeDict):
    '''
    a node creator. Pass a dict with 'nodeType'<str>, 'args'<list> and 'kwargs'<dict> keys
    All values must exist, but may be empty.
    Return a pointer to the newly created item or None on error
    '''
    try:
        if hasattr(nuke.nodes, nodeDict['nodeType']):
            #get a pointer to the function
            func = getattr(nuke.nodes, nodeDict['nodeType'])
            #pass required args and kwargs to the func as list and dict
            aNode = func( *nodeDict['args'], **nodeDict['kwargs'])
            return aNode
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, file=sys.stdout)
        print e
        print nodeDict
        return None


def connectNodes(srcNode, dstNode, connectionIndex):
    '''
    Connect srcNode to dstNode's input at index connectionIndex
    return True on success or False on error
    '''
    try:
        dstNode.setInput( connectionIndex, srcNode )
        return True
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, file=sys.stdout)
        print e
        return False



'''
Down and dirty arg parser. Uses argparse to compile keyword arguments into
a dict to be passed to a function

['/hdx/sys/lucy_scripts/convertImageSequence.py', '--source', '/mnt/x1/hdx/cg/maya/scripts/hdxBrowser/trevorDev/testPlate',
'--entity', '54513295128acb6238b48f9d', '--start', '1001', '--end', 'null']

'''
if __name__ == '__main__':
    print sys.argv
    parser = argparse.ArgumentParser(description='Process plate entity publish.')
    parser.add_argument('--source',  dest='source', action='store', help='Directory of source images')
    parser.add_argument('--entity', dest='entity', action='store', help='Mavis entity _id')
    parser.add_argument('--start', dest='sfrm', action='store', help='start frame vlaue')
    parser.add_argument('--end', dest='efrm', action='store', help='end frame value')

    args = vars(parser.parse_args())
    mavisEntity={}
    print args
    print '\n'
    print "command line args:"
    nukeArgs=" ".join(sys.argv)
    nukeCommand = "nuke8args %s"%nukeArgs
    print nukeCommand
    print '\n'

    #for k,v in args.iteritems():
    #    nukeCommand  = "%s %s %s" %(nukeCommand, str(k), str(v))
    sys.exit("Step 1)")
    if args and args.has_key('entity'):
        mavisEntity = conn.find(args['entity'])

    if not mavisEntity:
        print "ERROR: Cannot determine mavis entity"
    else:
        mavisEntity['publishArgs']=args
        if not mavisEntity:
            print "ERROR: ImportPlateAction got no action"
            print sys.argv
        importPlateAction(**mavisEntity)

'''
    #if nuke.INTERACTIVE:
    #    kwargDict =   {'source' : '/full/path/to/source/sequence.%04d.exr',  'dest' : '/projects/test006/shots/tst001/plates/client/publishes/0001/sequence.%04d.exr',
    #   'entity' : '/projects/test006/shots/tst001/plates/client' }
    #else:
 '''

