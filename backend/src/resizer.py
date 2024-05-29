from typing import Tuple

from PIL import Image


def resize_with_aspect_ratio(image_path: str, output_path: str, size: Tuple[int, int]):
    """
    resizes the image form input_path to the specified size and saves in output_path
    :param image_path: input image path
    :param output_path: output image path
    :param size:  A 2-tuple, containing (width, height) in pixels.
    """
    with Image.open(image_path) as img:
        # Preserve aspect ratio
        img.thumbnail(size)
        img.save(output_path)


resize_with_aspect_ratio('input_image.jpg', 'output_image.jpg', (150, 120))
