from PIL import Image
from typing import Tuple, BinaryIO


def resize_with_aspect_ratio(image_source: str | BinaryIO, output_path: str, size: Tuple[int, int]):
    """
    resizes the image form input_path to the specified size and saves in output_path
    :param image_source: input image path
    :param output_path: output image path
    :param size:  A 2-tuple, containing (width, height) in pixels.
    """
    with Image.open(image_source) as img:
        # Preserve aspect ratio
        img.thumbnail(size)
        img.save(output_path)