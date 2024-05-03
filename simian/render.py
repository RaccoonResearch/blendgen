"""Blender script to render images of 3D models."""
import argparse
import platform
import subprocess
import sys
import json
import os
import ssl
import pandas as pd

ssl._create_default_https_context = ssl._create_unverified_context

def check_imports():
    # what was the CLI command used to run this script?
    application_path = sys.argv[0]
    print("Application path")
    print(application_path)
    # read from requirements.txt
    with open("requirements.txt", "r") as f:
        requirements = f.readlines()
    for requirement in requirements:
        requirement = requirement.split(">=")[0].split("==")[0].split("@")[0].strip()
        try:
            __import__(requirement)
        except ImportError:
            print(f"Installing {requirement}")
            subprocess.run(["bash", "-c", f"{sys.executable} -m pip install {requirement}"])

check_imports()

import pandas as pd
import objaverse
import bpy

# Get the directory of the currently executing script
current_dir = os.path.dirname(os.path.abspath(__file__))

# if the directory is simian, remove that
if current_dir.endswith("simian"):
    current_dir = os.path.dirname(current_dir)  

# Append the simian directory to sys.path
blendgen_path = os.path.join(current_dir)
sys.path.append(blendgen_path)

from simian.camera import reset_cameras, set_camera_settings
from simian.scene import reset_scene
from simian.object import combine_and_centralize_hierarchy, delete_invisible_objects, load_object, merge_close_vertices, normalize_object_scale, remove_small_geometry
from simian.background import set_background

def read_combination(combination_file, index=0):
    """Reads a specified camera combination from a JSON file."""
    with open(combination_file, 'r') as file:
        combinations = json.load(file)
        return combinations[min(index, len(combinations) - 1)]

def render_scene(
    object_file: str,
    output_dir: str,
    context: bpy.types.Context,
    combination_file,
    combination_index=0,
    height=1080,
    width=1920
) -> None:
    """Saves rendered video of the object."""
    os.makedirs(output_dir, exist_ok=True)
    scene = context.scene
    
    combination = read_combination(combination_file, combination_index)

    # Load the object
    if object_file.endswith(".blend"):
        bpy.ops.object.mode_set(mode="OBJECT")
        reset_cameras(scene)
        delete_invisible_objects(context)
    else:
        reset_scene()
        load_object(object_file, context=context)
    
    # Get the object just loaded and ensure all children are selected
    obj = [obj for obj in context.view_layer.objects.selected][0]
    
    # print mesh statistics
    print("Mesh statistics")
    print(obj.data)
    
    combine_and_centralize_hierarchy(context, obj)
    obj = [obj for obj in context.view_layer.objects.selected][0]
    print("Mesh statistics")
    print(obj.data)
    # merge_close_vertices(context, obj, 0.001)
    obj = [obj for obj in context.view_layer.objects.selected][0]
    
    # print mesh statistics
    print("Mesh statistics")
    print(obj.data)
    
    # remove_small_geometry(context, obj, 10)
    obj = normalize_object_scale(context, obj)
        
    # Set up cameras
    
    set_camera_settings(context, combination)
    set_background(context, args, combination)
    
    # set height and width of rendered output
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
        
    # set the render type to H264, visually lossless
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
    scene.render.ffmpeg.ffmpeg_preset = 'BEST'
    
    # Set output path and start rendering
    render_path = os.path.join(output_dir, f"{combination_index}.mp4")
    
    scene.render.filepath = render_path
    bpy.ops.render.render(animation=True)  # Use animation=True for video rendering
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Path to the directory where the rendered video will be saved.",
    )
    parser.add_argument(
        "--combination_file",
        type=str,
        default="combinations.json",
        help="Path to the JSON file containing camera combinations.",
    )
    parser.add_argument(
        "--background_path",
        type=str,
        default="backgrounds",
        help="Path to the directory where the background HDRs will be saved.",
    )
    parser.add_argument(
        "--combination_index",
        type=int,
        default=0,
        help="Index of the camera combination to use from the JSON file.",
    )
    parser.add_argument("--width", type=int, default=1920, help="Render output width.")
    parser.add_argument("--height", type=int, default=1080, help="Render output height.")
    argv = sys.argv[sys.argv.index("--") + 1 :]
    args = parser.parse_args(argv)

    context = bpy.context

    bpy.ops.wm.open_mainfile(filepath="scenes/video_generation_v1.blend")

    scene = context.scene
    render = scene.render

    scene.render.film_transparent = True

    os_system = platform.system()

    # if we are on mac, device type is METAL
    # if we are on windows or linux, device type is CUDA
    if os_system == "Darwin":
        bpy.context.preferences.addons[
            "cycles"
        ].preferences.compute_device_type = "METAL"
    else:
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "CUDA"
        
    objects = pd.read_json("combinations.json", orient="records")
    object = objects.iloc[args.combination_index]
    print(object)
    
    # get the object uid from the 'object' column, which is a dictionary
    objects_column = object["object"]
    uid = objects_column["uid"]
    
    print("Loading uid")
    print(uid)
    
    # Download object with objaverse to download_dir
    downloaded = objaverse.load_objects([uid])
    download_dir = downloaded[uid]
    # Render the images
    render_scene(
        object_file=download_dir,
        output_dir=args.output_dir,
        context=context,
        combination_file=args.combination_file,
        combination_index=args.combination_index,
        height=args.height,
        width=args.width
    )