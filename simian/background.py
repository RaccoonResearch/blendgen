import os
from typing import Dict
import requests
import bpy

def get_background_path(background_path: str, combination: Dict) -> str:
    """
    Get the local file path for the background HDR image.

    Args:
        background_path (str): The base directory for storing background images.
        combination (Dict): The combination dictionary containing background
    Returns:
        str: The local file path for the background HDR image.
    """
    background = combination['background']
    background_id = background['id']
    background_from = background['from']
    background_path = f"{background_path}/{background_from}/{background_id}.hdr"
    return background_path

def get_background(background_path: str, combination: Dict) -> None:
    """
    Download the background HDR image if it doesn't exist locally.

    This function checks if the background HDR image specified in the combination dictionary
    exists locally. If it doesn't exist, it downloads the image from the provided URL and
    saves it to the local file path.

    Args:
        background_path (str): The base directory for storing background images.
        combination (Dict): The combination dictionary containing background information.

    Returns:
        None
    """
    background_path = get_background_path(background_path, combination)
    
    background = combination['background']
    background_url = background['url']

    # make sure each folder in the path exists
    os.makedirs(os.path.dirname(background_path), exist_ok=True)
    
    if not os.path.exists(background_path):
        print(f"Downloading {background_url} to {background_path}")
        response = requests.get(background_url)
        with open(background_path, 'wb') as file:
            file.write(response.content)
    else:
        print(f"Background {background_path} already exists")
        
def set_background(background_path: str, combination: Dict) -> None:
    """
    Set the background HDR image of the scene.

    This function sets the background HDR image of the scene using the provided combination
    dictionary. It ensures that the world nodes are used and creates the necessary nodes
    (Environment Texture, Background, and World Output) if they don't exist. It then loads
    the HDR image, connects the nodes, and enables the world background in the render settings.

    Args:
        background_path (str): The base directory for storing background images.
        combination (Dict): The combination dictionary containing background information.

    Returns:
        None
    """
    get_background(background_path, combination)
    background_path = get_background_path(background_path, combination)
    
    # Ensure world nodes are used
    bpy.context.scene.world.use_nodes = True
    tree = bpy.context.scene.world.node_tree
    
    # Find the existing Environment Texture node
    env_tex_node = None
    for node in tree.nodes:
        if node.type == 'TEX_ENVIRONMENT':
            env_tex_node = node
            break
    
    if env_tex_node is None:
        raise ValueError("Environment Texture node not found in the world node graph")
    
    # Load the HDR image
    env_tex_node.image = bpy.data.images.load(background_path)
    
    # Connect the Environment Texture node to the Background node
    background_node = tree.nodes.get("Background")
    if background_node is None:
        # If the Background node doesn't exist, create it
        background_node = tree.nodes.new(type="ShaderNodeBackground")
    
    # Connect the Environment Texture node to the Background node
    tree.links.new(env_tex_node.outputs["Color"], background_node.inputs["Color"])
    
    # Connect the Background node to the World Output
    output_node = tree.nodes.get("World Output")
    if output_node is None:
        # If the World Output node doesn't exist, create it
        output_node = tree.nodes.new(type="ShaderNodeOutputWorld")
    
    # Connect the Background node to the World Output
    tree.links.new(background_node.outputs["Background"], output_node.inputs["Surface"])
    
    # Enable the world background in the render settings
    bpy.context.scene.render.film_transparent = False
    
    print(f"Set background to {background_path}")

def create_photosphere(background_path: str, combination: Dict) -> bpy.types.Object:
    """
    Create a photosphere object in the scene.

    This function creates a UV sphere object in the scene and positions it at (0, 0, 3).
    It smooths the sphere, inverts its normals, and renames it to "Photosphere". It then
    calls the `create_photosphere_material` function to create a material for the photosphere
    using the environment texture as emission.

    Args:
        background_path (str): The base directory for storing background images.
        combination (Dict): The combination dictionary containing background information.

    Returns:
        bpy.types.Object: The created photosphere object.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64,
        ring_count=32,
        radius=1.0,
        location=(0, 0, 3)
    )
    bpy.ops.object.shade_smooth()
    
    # invert the UV sphere normals
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    
    sphere = bpy.context.object
    sphere.name = "Photosphere"
    sphere.data.name = "PhotosphereMesh"
    create_photosphere_material(background_path, combination, sphere)
    return sphere

def create_photosphere_material(background_path: str, combination: Dict, sphere: bpy.types.Object) -> None:
    """
    Create a material for the photosphere object using the environment texture as emission.

    This function creates a new material for the provided photosphere object. It sets up
    the material nodes to use the environment texture as emission and assigns the material
    to the photosphere object.

    Args:
        background_path (str): The base directory for storing background images.
        combination (Dict): The combination dictionary containing background information.
        sphere (bpy.types.Object): The photosphere object to assign the material to.

    Returns:
        None
    """
    # Create a new material
    mat = bpy.data.materials.new(name="PhotosphereMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Create and connect the nodes
    emission = nodes.new(type="ShaderNodeEmission")
    env_tex = nodes.new(type="ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(get_background_path(background_path, combination))
    mat.node_tree.links.new(env_tex.outputs["Color"], emission.inputs["Color"])
    output = nodes.new(type="ShaderNodeOutputMaterial")
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    
    # Assign material to the sphere
    if sphere.data.materials:
        sphere.data.materials[0] = mat
    else:
        sphere.data.materials.append(mat)
    
    print("Material created and applied to Photosphere")