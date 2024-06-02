import json
import os
import sys
import subprocess
from typing import Any, Dict

from distributaur.huggingface import upload_to_huggingface

def run_job(
    combination_index: int,
    combination: Dict[str, Any],
    width: int,
    height: int,
    output_dir: str,
    hdri_path: str,
    start_frame: int = 0,
    end_frame: int = 65,
) -> None:
    """
    Run a rendering job with the specified combination index and settings.

    Args:
        combination_index (int): The index of the combination to render.
        combination (Dict[str, Any]): The combination dictionary.
        width (int): The width of the rendered output.
        height (int): The height of the rendered output.
        output_dir (str): The directory to save the rendered output.
        hdri_path (str): The path to the HDRI file.
        start_frame (int, optional): The starting frame number. Defaults to 0.
        end_frame (int, optional): The ending frame number. Defaults to 65.

    Returns:
        None
    """
    combination = json.dumps(combination)
    combination = '"' + combination.replace('"', '\\"') + '"'

    os.makedirs(output_dir, exist_ok=True)

    args = f"--width {width} --height {height} --combination_index {combination_index}"
    args += f" --output_dir {output_dir}"
    args += f" --hdri_path {hdri_path}"
    args += f" --start_frame {start_frame} --end_frame {end_frame}"
    args += f" --combination {combination}"

    command = f"{sys.executable} simian/render.py -- {args}"
    print("Worker running: ", command)

    subprocess.run(["bash", "-c", command], check=False)

    upload_to_huggingface(output_dir)

    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)


if __name__ == "__main__":

    from distributaur.core import register_function, app

    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))

    celery = app

    register_function(run_job)
