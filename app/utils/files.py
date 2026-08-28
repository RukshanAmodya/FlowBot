"""File operations and archive packaging utilities."""
import shutil
import zipfile
from pathlib import Path
from typing import List
from app.utils.logger import logger

def create_zip_archive(image_paths: List[Path], output_zip_path: Path) -> Path:
    """Creates a zip archive containing the provided image files."""
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, img_path in enumerate(image_paths, 1):
            if img_path.exists():
                arcname = f"image_{idx}{img_path.suffix}"
                zf.write(img_path, arcname=arcname)
            else:
                logger.warning(f"File {img_path} not found when building zip archive.")
    logger.info(f"Created ZIP archive at {output_zip_path}")
    return output_zip_path

def cleanup_directory(dir_path: Path) -> None:
    """Safely removes a directory and all its contents."""
    try:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            logger.info(f"Cleaned up directory: {dir_path}")
    except Exception as e:
        logger.error(f"Error during cleanup of {dir_path}: {e}")
