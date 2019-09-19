# -*- coding: utf-8 -*-

"""
Copyright (c) 2019 Galib F. Arrieta

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in 
the Software without restriction, including without limitation the rights to 
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE.
"""
import bpy
import os

#The modules of lumbermixalot
if __package__ is None or __package__ == "":
    # When running as a standalone script from Blender Text View "Run Script"
    import actormixalot
    import motionmixalot
    import commonmixalot
    from commonmixalot import Status
else:
    # When running as an installed AddOn, then it runs in package mode.
    from . import actormixalot
    from . import motionmixalot
    from . import commonmixalot
    from .commonmixalot import Status

if "bpy" in locals():
    from importlib import reload
    if "actormixalot" in locals():
        reload(actormixalot)
    if "motionmixalot" in locals():
        reload(motionmixalot)
    if "commonmixalot" in locals():
        reload(commonmixalot)


#Exports the current scene with the right settings for Lumberayrd.
#@fbxFilePath (string) a fully qualified file path, suitable for file
#   exporting.
def _ExportFbx(fbxFilePath):
    bpy.ops.export_scene.fbx(filepath=fbxFilePath, check_existing=False, axis_forward='Y', axis_up='Z', path_mode='COPY')
    print("{} exported successfully".format(fbxFilePath))


# Looks across first level children and see if at least one of them is of type
# 'MESH'
# @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
def _CheckArmatureContainsMesh(obj):
    children = obj.children
    for childObj in children:
        if childObj.type == 'MESH':
            return True
    return False


#Returns a fully qualified file path, suitable for file exporting.
#@isActor (bool) If True the path is expected to be for an Actor.
#   If False the path is expected to be for a Motion.
#   This parameter is only relevant if @appendActorOrMotionPath is True.
#@fbxFilename (string). File name (no path). '.fbx' extension is optional.
#    If Empty or None, automatic FBX exporting won't be done upon
#    conversion.
#@fbxOutputPath (string). Output directory. Only relevant if @fbxFilename
#    is valid. CAVEAT: 
#@appendActorOrMotionPath (bool). If True, If an Actor is being converted
#    then the 'Actor/' path will be appended to @fbxOutputPath. If a Motion
#    is being converted then the 'Motions/' path will be appended.
#    If False, no path is appended to @fbxOutputPath.
def _GetOutputFilename(isActor,  fbxFilename, fbxOutputPath,
                       appendActorOrMotionPath):
    fbxFilename = "" if (fbxFilename is None) else fbxFilename.strip()
    fbxOutputPath = "" if (fbxOutputPath is None) else fbxOutputPath.strip()

    if fbxFilename == "":
        return None
    #Clean the fbxFilename.
    name, ext = os.path.splitext(fbxFilename)
    fbxFilename = "{}.fbx".format(name)
    if fbxOutputPath == "":
        fbxOutputPath = "."
    if appendActorOrMotionPath:
        if isActor:
            dirToAppend = "Actor"
        else:
            dirToAppend = "Motions"
        lastDir = os.path.basename(os.path.normpath(fbxOutputPath))
        if lastDir != dirToAppend:
            fbxOutputPath = os.path.join(fbxOutputPath, dirToAppend)
    #Make sure the output directory exists. If not, create it.
    if not os.path.exists(fbxOutputPath):
        try:
            os.makedirs(fbxOutputPath)
        except:
            msg = "Failed to create output dir:{}.\n \
                Will convert without exporting.".format(fbxOutputPath)
            print(msg)
            return None
    return os.path.join(fbxOutputPath, fbxFilename)
    

def Convert(sceneObj, armatureObj, hipBoneName="", rootBoneName="",
            animationSampleRate=60.0, fbxFilename="", fbxOutputPath="",
            appendActorOrMotionPath=True, dumpCSVs=False):
    """
    Main function to bake hipmotion to RootMotion in Mixamo Rigs.
    If this function finds at least one 'MESH' type of child object, then
    it will assume it is converting an Actor type if asset. If no 'MESH' type
    of child object is found, then it will assume it is converting a Motion
    type of asset.

    @sceneObj (bpy.types.Scene)
    @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @hipBoneName (string). Name of the "Hips" bone as originated by Mixamo.
        If Empty or None, the value will be assumed to tbe "Hips".
    @rootBoneName (string). Name of the root motion bone that will be added to
        the armature. If Empty or None, the value will be assumed to be "root".
    @animationSampleRate (double) A value in Hz that represents the target
        Frames Per Second at which the animation is supposed to run. It is
        usually 60fps or 30fps.
    @fbxFilename (string). File name (no path). '.fbx' extension is optional.
        If Empty or None, automatic FBX exporting won't be done upon
        conversion.
    @fbxOutputPath (string). Output directory. Only relevant if @fbxFilename
        is valid. CAVEAT: 
    @appendActorOrMotionPath (bool). If True, If an Actor is being converted
        then the 'Actor/' path will be appended to @fbxOutputPath. If a Motion
        is being converted then the 'Motions/' path will be appended.
        If False, no path is appended to @fbxOutputPath.
    @dumpCSVs (bool) DEBUG Only. Dump motion vector data as CSV files
    """
    yield Status("starting Convert")
    
    hipBoneName = "" if (hipBoneName is None) else hipBoneName.strip()
    rootBoneName = "" if (rootBoneName is None) else rootBoneName.strip()
    if hipBoneName == "":
        hipBoneName = "Hips"
    if rootBoneName == "":
        rootBoneName = "root"

    isActor = _CheckArmatureContainsMesh(armatureObj)
    
    yield Status("Checked Asset Type. isActor={}".format(isActor))
    
    outputFilename = _GetOutputFilename(isActor,  fbxFilename, fbxOutputPath,
        appendActorOrMotionPath)

    yield Status("Processed output path strings")

    if isActor:
        conversion_iterator = actormixalot.ProcessActor(armatureObj, rootBoneName)
    else:
        conversion_iterator = motionmixalot.ProcessMotion(sceneObj, armatureObj,
            hipBoneName, rootBoneName, animationSampleRate, dumpCSVs)

    for status in conversion_iterator:
        yield Status(str(status))

    yield Status("Completed Asset Conversion.")

    if outputFilename is not None:
        _ExportFbx(outputFilename)
        yield Status("FBX Assert exported.")

    return 1