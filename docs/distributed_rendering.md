# Distributed Rendering

Distributed rendering is handled by the `distributed` and `worker` modules. The `distributed` module is responsible for distributing the rendering of videos across multiple machines. It uses Redis to manage the queue of combinations to render and the workers that render the videos. The worker module is responsible for taking a combination from the queue, rendering the video, and uploading the video to a specified location.

### Management Module

::: simian.distributed
    :docstring:
    :members:
    :undoc-members:
    :show-inheritance:

### Worker Module

::: simian.worker
    :docstring:
    :members:
    :undoc-members:
    :show-inheritance: