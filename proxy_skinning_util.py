"""
Proxy Skinning Utilities
    Example Artist Usage:
        + extract_faces:
            select the faces you want to extract from model

        + copy_proxy_to_skin:
            select your proxy model (skinned) followed by the hires model


    Example Code Usage:
        # Select faces on a mesh
        from proxy_skinning_util import extract_faces
        newMesh = extract_faces()

        # Select Source Mesh and Destination Mesh
        from proxy_skinning_util import copy_proxy_to_skin
        newSkinCluster = copy_proxy_to_skin()
"""
from maya import cmds
from functools import wraps

__author__ = 'Stephan Osterburg'
__doc__ = 'Utility functions for copying proxy skinning'
__version__ = '0.1.0'
__maintainer__ = 'Stephan Osterburg'
__email__ = 'sosterburg@imvu.com'
__status__ = 'Development'  # "Prototype", "Development", or "Production"


def _undo(func):
    """ Undo Decorator

    :param func: incoming function
    :return:
    """

    @wraps(func)
    def _undo_func(*args, **kwargs):
        try:
            cmds.undoInfo(ock=True)
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(cck=False)
            cmds.undo()

    return _undo_func


@_undo
def extract_faces(face_list=None, new_name=None, keep_original=False, copy_skinning=False):
    """Extract faces from mesh and create a copy

    :param face_list: List of faces to extract
    :param new_name: New mesh name
    :param keep_original: Make a copy of mesh before extraction
    :param copy_skinning: Copy skin weights over to extracted mesh
    :return: Extracted mesh
    """

    if not face_list:
        selected_faces = cmds.ls(sl=True)
    else:
        selected_faces = face_list

    if not bool(cmds.filterExpand(selected_faces, ex=True, sm=34)) or []:
        raise RuntimeError("Must select one or more faces")

    shape = cmds.listRelatives(p=1)
    cur_mesh = cmds.listRelatives(shape, p=1)[0]

    cmds.select(cur_mesh + '.f[:]', tgl=1)
    faces_to_extract = cmds.ls(sl=1)

    # Save current pose
    influence_list = cmds.skinCluster(cur_mesh, q=True, wi=True)
    cur_pose = cmds.dagPose(influence_list, save=True, name='extractInPose')

    # Go to bind pose before copying weights
    bind_pose = cmds.dagPose(influence_list, q=True, bindPose=True)
    cmds.dagPose(bind_pose, restore=True)

    new_mesh = cmds.duplicate(cur_mesh)[0]

    # Rename mesh
    if new_name:
        new_mesh = cmds.rename(new_mesh, new_name)

    # Copy skin weights over to new mesh
    if copy_skinning:
        copy_proxy_to_skin(cur_mesh, new_mesh)

    if not keep_original:
        cmds.delete(selected_faces)

    # Swap current mesh to new mesh
    for i in range(len(faces_to_extract)):
        faces_to_extract[i] = faces_to_extract[i].replace(cur_mesh, new_mesh)

    cmds.delete(faces_to_extract)

    # Clean new mesh
    if copy_skinning:
        cmds.bakePartialHistory(cur_mesh, prePostDeformers=True)
        cmds.bakePartialHistory(new_mesh, prePostDeformers=True)
    else:
        cmds.delete(new_mesh, ch=1)

    cmds.dagPose(cur_pose, restore=True)
    cmds.delete(cur_pose)
    cmds.select(new_mesh, r=1)
    
    return new_mesh


def copy_proxy_to_skin(src_mesh=None, dst_mesh=None):
    """Copy skinning information from source (proxy) to destination mesh

    :param src_mesh: Source mesh
    :param dst_mesh: Destination Mesh
    :return: New skinCluster
    """

    # Test for selection
    if not src_mesh or not dst_mesh:
        meshes = cmds.ls(sl=1)
        if len(meshes) == 2:
            src_mesh = meshes[0]
            dst_mesh = meshes[1]
        else:
            raise RuntimeError("You need to have TWO meshes selected!")

    # Get source skinCluster
    src_skin = cmds.ls(cmds.listHistory(src_mesh), type='skinCluster')
    if not src_skin:
        raise RuntimeError("{} does not have a skinCluster".format(src_skin))

    # Check destination skinCluster
    dst_skin = cmds.ls(cmds.listHistory(dst_mesh), type='skinCluster')

    # Save current pose
    influence_list = cmds.skinCluster(src_skin, q=True, wi=True)
    cur_pose = cmds.dagPose(influence_list, save=True, name='skinToPose')

    # Go to bind pose before copying weights
    bind_pose = cmds.dagPose(influence_list, q=True, bindPose=True)
    if bind_pose:
        cmds.dagPose(bind_pose[0], restore=True)

    # Build destination skinCluster
    if not dst_skin:
        dst_prefix = dst_mesh.split(':')[-1]
        src_influence_list = cmds.skinCluster(src_skin[0], q=True, inf=True)
        dst_skin = cmds.skinCluster(src_influence_list, dst_mesh, toSelectedBones=True, rui=False,
                                    n=dst_prefix + '_skinCluster')

    # Copy skin weights
    cmds.copySkinWeights(sourceSkin=str(src_skin[0]), destinationSkin=str(dst_skin[0]),
                         surfaceAssociation='closestPoint', influenceAssociation='name', noMirror=True)

    cmds.dagPose(cur_pose, restore=True)
    cmds.delete(cur_pose)
    cmds.select(cl=1)

    # Return result
    return dst_skin
