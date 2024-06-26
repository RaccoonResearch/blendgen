import json
import logging
import os
import sys
import subprocess
import time
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_job(
    combination_indeces: int,
    combinations: Dict[str, Any],
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
    combination_strings = []
    for combo in combinations:
        combination_string = json.dumps(combo)
        combination_string = '"' + combination_string.replace('"', '\\"') + '"'
        combination_strings.append(combination_string)

    # create output directory, add time to name so each new directory is unique
    output_dir += str(time.time())
    os.makedirs(output_dir, exist_ok=True)

    # render images in batches (batches to handle rate limiting of uploads)
    batch_size = len(combination_indeces)
    for i in range(batch_size):

        args = f" --width {width} --height {height} --combination_index {combination_indeces[i]}"
        args += f" --output_dir {output_dir}"
        args += f" --hdri_path {hdri_path}"
        args += f" --start_frame {start_frame} --end_frame {end_frame}"
        args += f" --combination {combination_strings[i]}"

        command = f"{sys.executable} -m simian.render -- {args}"
        logger.info(f"Worker running simian.render")

        subprocess.run(["bash", "-c", command], check=True)

    distributaur.upload_directory(output_dir)

    return "Task completed"


# only run this is this file was started by celery or run directly
# check if celery is in sys.argv, it could be sys.argv[0] but might not be

if __name__ == "__main__" or any("celery" in arg for arg in sys.argv):
    from distributaur.distributaur import create_from_config

    distributaur = create_from_config()
    distributaur.register_function(run_job)

    celery = distributaur.app
