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
import os
import json

import bpy
from mathutils import *

class Axis:
    X = Vector([1, 0, 0])
    Y = Vector([0, 1, 0])
    Z = Vector([0, 0, 1])

#For debugging.
def Dump(obj):
    print(type(obj))
    print(dir(obj))

class Status:
    """ Used for yield statements """
    def __init__(self, msg, status_type='default'):
        print(msg)
        self.msg = msg
        self.status_type = status_type
    def __str__(self):
        return str(self.msg)


def ApplyCurrentRotationAs000(obj: bpy.types.Object, verbose: bool = False):
    """
    Whatever is the default rotation of the armature we need to apply as
    its default rotation. This way the rotation becomes (0,0,0) if seen
    as an XYZ Euler.
    """
    #Set 'OBJECT' mode
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if verbose:
        print(f"Applied current rotation as 0,0,0 to object named '{obj.name}'")


def GetRootBone(obj: bpy.types.Armature) -> bpy.types.Bone:
    """
    This method assumes the root bone has no siblings.
    returns the first non parented bone. 
    """
    bones = obj.data.bones
    for bone in bones:
        if bone.parent == None:
            return bone
    return None


def HasOnlyOneRootBone(obj):
    """
    Returns True if @obj only has a single root bone without siblings.
    @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    """
    bones = obj.data.bones
    rootBoneCount = 0
    for bone in bones:
        if bone.parent == None:
            rootBoneCount += 1
    return rootBoneCount == 1


def HasRootMotionBone(obj, rootBoneName):
    """
    Returns True if the root bone is named @rootBoneName
    @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @rootBoneName (string). Name of the root motion bone to compare with
    """
    bones = obj.data.bones
    for bone in bones:
        #print(bone.name, len(bone.children), bone.parent)
        if (bone.parent is None) and (bone.name==rootBoneName):
            return True
    return False


def GetRestPoseMatrixFromPoseBone(poseBoneObj):
    """
    bpy.types.PoseBone
    All animation data is recorded in the PoseBone.
    Technically by setting the current frame number
    with SetCurrentAnimationFrame() you can get the current Matrix4x4
    from the PoseBone.
    BUT, All animation data is technically relative to the
    Rest Pose, and for that We access the matrix from PoseBone.bone
    which is a bpy.types.Bone 
    """
    return poseBoneObj.bone.matrix_local


def GetPoseBoneFromArmature(armatureObj, boneName):
    """
    @armatureObj is a bpy.types.Armature
    @boneName str
    returns a bpy.types.PoseBone
    """
    bpy.ops.object.mode_set(mode='POSE')
    for bone in armatureObj.pose.bones:
        if bone.name == boneName:
            return bone
    return None

def AddSiblingRootBone(obj, boneName):
    hasOnlyOneRootBone = cmn.HasOnlyOneRootBone(obj)
    hasRootMotionBone = cmn.HasRootMotionBone(obj, boneName)
    if hasOnlyOneRootBone and hasRootMotionBone:
        raise Exception("Most likely this asset was already processed because it contains a single 'root' bone")
        return
    if hasRootMotionBone:
        print("Armature already had root motion bone")
        return
    #Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    ebones = obj.data.edit_bones

    #Create the new root bone
    newRootBone = ebones.new(boneName)
    boneSize = 1.0/obj.scale[0]
    newRootBone.tail = (0.0, -boneSize, 0)

    #Exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')

    print("Added bone '{}' as sibling of the current root bone.".format(boneName))


def MakeParentBone(obj, parentBoneName, childBoneName):
    #Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    ebones = obj.data.edit_bones
    rootBoneIndex = ebones.find(parentBoneName)
    childBoneIndex = ebones.find(childBoneName)
    print("root bone index = {}, child bone index = {}".format(rootBoneIndex, childBoneIndex))
    ebones[childBoneIndex].parent = ebones[rootBoneIndex]
    
    #Exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')


def _ExportFbxInternal(fbxFilePath: str):
    """
    Exports the current scene with the right settings for O3DE.
    @fbxFilePath A fully qualified file path, suitable for file exporting.
    """
    bpy.ops.export_scene.fbx(filepath=fbxFilePath, check_existing=False, axis_forward='Y', axis_up='Z')#, path_mode='COPY')
    print(f"FBX file '{fbxFilePath}' was exported successfully")


def _MakeFilePathForFBX(fbxFilename: str, fbxOutputPath: str) -> str:
    """
    Returns a fully qualified file path, suitable for file exporting.
    @fbxFilename File name (no path). '.fbx' extension is optional.
        Can not be empty or None.
    @fbxOutputPath Output directory. The directory will be created if it doesn't exist.
    """
    #Clean the fbxFilename.
    name, _ = os.path.splitext(fbxFilename)
    fbxFilename = f"{name}.fbx"
    #Make sure the output directory exists. If not, create it.
    if not os.path.exists(fbxOutputPath):
        try:
            os.makedirs(fbxOutputPath)
        except:
            print(f"Failed to create output dir: '{fbxOutputPath}'")
            return None
    return os.path.join(fbxOutputPath, fbxFilename)


def _CreateTexturesSubdir(outputDirectoryPath: str, subdirName: str = "textures") -> str:
    """
    Only if there's at least one texture in the scene, it will create the directory
    @outputDirectoryPath/@subdirName, if it doesn't exist.
    In case of failure returns the same @outputDirectoryPath.
    In case of success returns @outputDirectoryPath/@subdirName
    """
    hasImage = False
    for image in bpy.data.images:
        if not image.has_data:
            continue
        hasImage = True
        break
    if not hasImage:
        return outputDirectoryPath
    finalDir = os.path.join(outputDirectoryPath, subdirName)
    if not os.path.exists(finalDir):
        try:
            os.makedirs(finalDir)
        except:
            print(f"Failed to create output textures dir: '{finalDir}'")
            return outputDirectoryPath
    return finalDir


def _UnpackTextures(outputDirectoryPath: str, filenamePrefix: str):
    """
    Unpacks all the textures found in the current scene into @outputDirectoryPath.
    Usually the textures come with a name, but the final filename will be prefixed
    with @filenamePrefix
    """
    outputDirectoryPath = _CreateTexturesSubdir(outputDirectoryPath)
    for image in bpy.data.images:
        if not image.has_data:
            continue
        originalFilepath = image.filepath         # Save for later
        originalFilepathRaw = image.filepath_raw          # Save for later
        originalImageFilename = os.path.basename(image.filepath)
        newFilename = f"{filenamePrefix}_{originalImageFilename}"
        finalOutputPath = os.path.join(outputDirectoryPath, newFilename)
        image.filepath = finalOutputPath
        image.filepath_raw = finalOutputPath
        image.save()
        print(f"Unpacked Texture {image.name} As: {finalOutputPath}")
        # Leave as is.
        image.filepath = originalFilepath
        image.filepath_raw = originalFilepathRaw


def ExportFBX(fbxFilename: str, fbxOutputPath: str, unpackTextures: bool) -> str:
    """
    Convenience function to export the current scene as FBX per the required
    O3DE configuration. 

    @fbxFilename File name (no path). '.fbx' extension is optional.
    @fbxOutputPath Output directory. Only relevant if @fbxFilename
        is valid.
    
    If Successful, returns the fully qualified path of the exported FBX file.
    """
    outputFilename = _MakeFilePathForFBX(fbxFilename,
                                        fbxOutputPath)
    if outputFilename is None:
        raise Exception("Undefined output filename")
    _ExportFbxInternal(outputFilename)
    if unpackTextures:
        prefix, _ = os.path.splitext(fbxFilename)
        _UnpackTextures(fbxOutputPath, prefix)
    return outputFilename


def GetFirstAmature(scene: bpy.types.Scene):
    """
    Returns the first Armature in the scene.
    Returns None if there's not at least one Armature.
    """
    for obj in scene.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def _ClearCachedCollectionData(collection: bpy.types.bpy_prop_collection, collectionTypeName: str = "object"):
    """
    Generic function that can clear the content of any collection in the scene.
    """
    dataNames = []
    for name in collection.keys():
        dataNames.append(name)
    if len(dataNames) > 0:
        print(f"Found {len(dataNames)} leftover {collectionTypeName}s. Will proceed to remove them...")
        for name in dataNames:
            collection.remove(collection[name])
            print(f"Removed leftover {collectionTypeName} '{name}'")
        print(f"Removed all leftover {collectionTypeName}s")


def _ClearOldAnimationData():
    _ClearCachedCollectionData(bpy.data.actions, "action")


def _ClearOldTextureData():
    _ClearCachedCollectionData(bpy.data.images, "texture")


def ImportFBX(fbxFilepath: str):
    """
    Convenience function to  import an FBX file. 

    @fbxFilename File name (no path). '.fbx' extension is optional.
    @fbxOutputPath Output directory. Only relevant if @fbxFilename
        is valid.
    
    If Successful, returns the fully qualified path of the exported FBX file.
    """
    #Before importing, let's clear any left over animation and texture data.
    _ClearOldAnimationData()
    _ClearOldTextureData()
    bpy.ops.import_scene.fbx(filepath=fbxFilepath)


class FbxProperties:
    ConfigJson = "lumbermixalot-config.json"

def GetFbxExportPropertiesObj(optionsFileDir: str):
    filename = os.path.join(optionsFileDir, FbxProperties.ConfigJson)
    if not os.path.exists(filename):
        return None
    with open(filename) as json_file:
        return json.load(json_file)


def GetFbxExportProperty(optionsFileDir: str, property: str) -> str:
    obj = GetFbxExportPropertiesObj(optionsFileDir)
    if obj:
        return obj[property]
    else:
        return ""


def StoreFbxExportProperty(optionsFileDir: str, property: str, value: str):
    data = {}
    data[property] = value
    filename = os.path.join(optionsFileDir, FbxProperties.ConfigJson)
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, indent=4)
