import argparse
import json
import logging
import os
import ssl
import sys
import bpy
import random
from pathlib import Path  # Add this import


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ssl._create_default_https_context = ssl._create_unverified_context

from .camera import (
    create_camera_rig,
    position_camera,
    set_camera_animation,
    set_camera_settings,
)
from .transform import find_largest_length, place_objects_on_grid
from .object import (
    apply_all_modifiers,
    apply_and_remove_armatures,
    get_meshes_in_hierarchy,
    join_objects_in_hierarchy,
    load_object,
    lock_all_objects,
    normalize_object_scale,
    optimize_meshes_in_hierarchy,
    set_pivot_to_bottom,
    unlock_objects,
    unparent_keep_transform,
)

from simian.background import create_photosphere, set_background
from simian.scene import apply_stage_material, create_stage, initialize_scene
import simian.vendor.objaverse

    
def generate_random_scene() -> str:
    try:
        command = [
            "python3", "-m", "infinigen.datagen.manage_jobs",
            "--output_folder", "outputs/random",
            "--num_scenes", "1",
            "--configs", "desert.gin", "simple.gin",
            "--pipeline_configs", "local_16GB.gin", "monocular.gin", "blender_gt.gin",
            "--pipeline_overrides", "LocalScheduleHandler.use_gpu=False"
        ]
        infinigen_path = os.path.join(os.getcwd(), "infinigen")
        print(f"Running command: {' '.join(command)} in {infinigen_path}")
        result = subprocess.run(command, cwd=infinigen_path, capture_output=True, text=True, timeout=600)
        print(f"Subprocess return code: {result.returncode}")
        print(f"Subprocess stdout: {result.stdout}")
        print(f"Subprocess stderr: {result.stderr}")

        if result.returncode != 0:
            print(f"Error running command: {result.stderr}")
            return ""
        else:
            print(f"Command output: {result.stdout}")
            # Find the generated folder in outputs/random
            random_folder = os.path.join(infinigen_path, "outputs/random")
            generated_folders = [f for f in os.listdir(random_folder) if os.path.isdir(os.path.join(random_folder, f))]
            if not generated_folders:
                print("Error: No folder generated in outputs/random")
                return ""
            generated_folder = os.path.join(random_folder, generated_folders[0])
            return os.path.join(generated_folder, "fine", "scene.blend")
    except subprocess.TimeoutExpired:
        print("Error: Subprocess timed out")
        return ""
    except Exception as e:
        print(f"Error running command: {e}")
        return ""
        
        
def read_combination(combination_file: str, index: int = 0) -> dict:
    """
    Reads a specified camera combination from a JSON file.

    Args:
        None

    Returns:
        None
    """
    with open(combination_file, "r") as file:
        data = json.load(file)
        combinations_data = data["combinations"]
        return combinations_data[index]


def load_user_blend_file(user_blend_file):
    if not os.path.exists(user_blend_file):
        logger.error(f"Blender file {user_blend_file} does not exist.")
        return False
    
    try:
        bpy.ops.wm.open_mainfile(filepath=user_blend_file)
        logger.info(f"Opened user-specified Blender file {user_blend_file} as the base scene.")
        return True
    except Exception as e:
        logger.error(f"Failed to load Blender file {user_blend_file}: {e}")
        return False
    

def delete_folder():
    try:
        # Get the current working directory and navigate to the infinigen folder
        infinigen_path = os.path.join(os.getcwd(), "infinigen")
        random_folder = os.path.join(infinigen_path, "outputs/random")
        
        # Check if the random folder exists
        if os.path.exists(random_folder):
            # Delete the random folder
            for root, dirs, files in os.walk(random_folder, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(random_folder)
            print(f"Deleted folder: {random_folder}")
        else:
            print("Random folder does not exist.")
    except Exception as e:
        print(f"Error deleting folder: {e}")
    

def render_scene(
    output_dir: str,
    context: bpy.types.Context,
    combination_file,
    start_frame: int = 1,
    end_frame: int = 65,
    animation_length: int = 300,
    combination_index=0,
    combination=None,
    render_images=False,
    user_blend_file=None
) -> None:
    """
    Renders a scene with specified parameters.

    Args:
        output_dir (str): Path to the directory where the rendered video will be saved.
        context (bpy.types.Context): Blender context.
        combination_file (str): Path to the JSON file containing camera combinations.
        start_frame (int): Start frame of the animation. Defaults to 1.
        end_frame (int): End frame of the animation. Defaults to 65.
        animation_length (int): Length of the animation. Defaults to 300.
        combination_index (int): Index of the camera combination to use from the JSON file. Defaults to 0.
        render_images (bool): Flag to indicate if images should be rendered instead of videos.
        user_blend_file (str): Path to the user-specified Blender file to use as the base scene.
    Returns:
        None
    """

    logger.info(f"Rendering scene with combination {combination_index}")

    os.makedirs(output_dir, exist_ok=True)

    initialize_scene()

    if user_blend_file == "infinigen":
        user_blend_file = generate_random_scene()
        if not load_user_blend_file(user_blend_file):
            logger.error(f"Unable to load generated Blender file: {user_blend_file}")
            return  # Exit the function if the file could not be loaded
    elif user_blend_file:
        if not load_user_blend_file(user_blend_file):
            logger.error(f"Unable to load user-specified Blender file: {user_blend_file}")
            return  # Exit the function if the file could not be loaded

    delete__folder()

    create_camera_rig()

    scene = context.scene

    scene.frame_start = animation_length - (end_frame - start_frame)
    scene.frame_end = animation_length

    # Lock and hide all scene objects before doing any object operations
    initial_objects = lock_all_objects()

    if combination is not None:
        combination = json.loads(combination)
    else:
        combination = read_combination(combination_file, combination_index)
    all_objects = []

    focus_object = None

    for object_data in combination["objects"]:
        object_file = objaverse.load_objects([object_data["uid"]])[
            object_data["uid"]
        ]

        load_object(object_file)
        obj = [obj for obj in context.view_layer.objects.selected][0]

        apply_and_remove_armatures()
        apply_all_modifiers(obj)
        join_objects_in_hierarchy(obj)
        optimize_meshes_in_hierarchy(obj)

        meshes = get_meshes_in_hierarchy(obj)
        obj = meshes[0]

        if focus_object is None:
            focus_object = obj

        unparent_keep_transform(obj)
        set_pivot_to_bottom(obj)

        obj.scale = [object_data["scale"]["factor"] for _ in range(3)]
        normalize_object_scale(obj)

        obj.name = object_data["uid"]  # Set the Blender object's name to the UID

        all_objects.append({obj: object_data})

    largest_length = find_largest_length(all_objects)
    place_objects_on_grid(all_objects, largest_length)

    # Unlock and unhide the initial objects
    unlock_objects(initial_objects)

    set_camera_settings(combination)

    set_camera_animation(combination, animation_length)

    # set_background(args.hdri_path, combination)

    # create_photosphere(args.hdri_path, combination).scale = (10, 10, 10)

    if not user_blend_file:
        set_background(args.hdri_path, combination)
        create_photosphere(args.hdri_path, combination).scale = (10, 10, 10)
        stage = create_stage(combination)
        apply_stage_material(stage, combination)

    # Randomize image sizes
    sizes = [
        (1920, 1080),
        (1024, 1024),
        (512, 512),
    ]

    if render_images:
        # Render a specific frame as an image with a random size
        middle_frame = (scene.frame_start + scene.frame_end) // 2
        size = random.choice(sizes)
        scene.frame_set(middle_frame)
        scene.render.resolution_x = size[0]
        scene.render.resolution_y = size[1]
        scene.render.resolution_percentage = 100
        position_camera(combination, focus_object)
        render_path = os.path.join(
            output_dir,
            f"{combination_index}_frame_{middle_frame}_{size[0]}x{size[1]}.png",
        )
        scene.render.filepath = render_path
        bpy.ops.render.render(write_still=True)
        logger.info(f"Rendered image saved to {render_path}")
    else:
        # Render the entire animation as a video
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "PERC_LOSSLESS"
        scene.render.ffmpeg.ffmpeg_preset = "BEST"
        position_camera(combination, focus_object)
        render_path = os.path.join(output_dir, f"{combination_index}.mp4")
        scene.render.filepath = render_path
        bpy.ops.render.render(animation=True)
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.join(output_dir, f"{combination_index}.blend")
        )
        logger.info(f"Rendered video saved to {render_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_dir",
        type=str,
        default="renders",
        required=False,
        help="Path to the directory where the rendered video or images will be saved.",
    )
    parser.add_argument(
        "--combination_file",
        type=str,
        default="combinations.json",
        help="Path to the JSON file containing camera combinations.",
    )
    parser.add_argument(
        "--hdri_path",
        type=str,
        default="backgrounds",
        help="Path to the directory where the background HDRs will be saved.",
    )
    parser.add_argument(
        "--combination_index",
        type=int,
        default=0,
        help="Index of the camera combination to use from the JSON file.",
        required=False,
    )
    parser.add_argument(
        "--start_frame",
        type=int,
        default=1,
        help="Start frame of the animation.",
        required=False,
    )
    parser.add_argument(
        "--end_frame",
        type=int,
        default=65,
        help="End frame of the animation.",
        required=False,
    )
    parser.add_argument(
        "--animation_length",
        type=int,
        default=120,
        help="End frame of the animation.",
        required=False,
    )
    parser.add_argument(
        "--width", type=int, default=1920, help="Render output width.", required=False
    )
    parser.add_argument(
        "--height", type=int, default=1080, help="Render output height.", required=False
    )
    parser.add_argument(
        "--combination", type=str, default=None, help="Combination dictionary."
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Generate images instead of videos.",
    )
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Path to the user-specified Blender file to use as the base scene.",
        required=False,
        nargs='?',  # This makes the argument optional and allows it to be empty
        const='infinigen',  # This makes it default to 'infinigen' if no value is provided
    )

    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]
    else:
        argv = []

    args = parser.parse_args(argv)

    context = bpy.context
    scene = context.scene
    render = scene.render

    if args.combination is not None:
        combination = json.loads(args.combination)
    else:
        combination = read_combination(args.combination_file, args.combination_index)

    # get the object uid from the 'object' column, which is a dictionary
    objects_column = combination["objects"]

    for object in objects_column:
        uid = object["uid"]

        downloaded = objaverse.load_objects([uid])

    # Render the images
    render_scene(
        animation_length=args.animation_length,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        output_dir=args.output_dir,
        context=context,
        combination_file=args.combination_file,
        combination_index=args.combination_index,
        combination=args.combination,
        render_images=args.images,
        user_blend_file=args.scene,
    )





