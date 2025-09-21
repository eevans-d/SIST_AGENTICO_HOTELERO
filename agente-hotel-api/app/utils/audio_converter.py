# [PROMPT 2.6] app/utils/audio_converter.py

import asyncio
from pathlib import Path
from typing import Optional

from ..core.logging import logger


async def ogg_to_wav(input_file: Path) -> Optional[Path]:
    """Convierte un archivo OGG a WAV usando FFmpeg."""
    output_file = input_file.with_suffix(".wav")
    cmd = ["ffmpeg", "-i", str(input_file), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(output_file)]

    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logger.error(f"FFmpeg error: {stderr.decode()}")
        return None

    return output_file
