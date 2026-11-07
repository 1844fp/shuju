"""Run Windows OCR locally with bounded input and a hard child-process timeout."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
SLOTS = threading.BoundedSemaphore(2)
SIGNATURES = {'.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}


class OCRUnavailable(ValueError):
    pass


def recognize(data, suffix, *, pdf_page=0):
    signature = b'%PDF-' if suffix == '.pdf' and 1 <= pdf_page <= 100 else SIGNATURES.get(suffix)
    if not signature or not data.startswith(signature) or len(data) > 5 * 1024 * 1024:
        raise ValueError('invalid OCR input')
    if os.name != 'nt':
        raise OCRUnavailable('Windows OCR unavailable')
    if not SLOTS.acquire(blocking=False):
        raise OCRUnavailable('OCR busy')
    try:
        work = ROOT / 'work'
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work, prefix='ocr-') as directory:
            image = Path(directory) / ('scan' + suffix)
            image.write_bytes(data)
            powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            try:
                result = subprocess.run(
                    [str(powershell), '-NoProfile', '-NonInteractive', '-File',
                     str(Path(__file__).with_name('windows_ocr.ps1')), str(image), str(pdf_page)],
                    capture_output=True, timeout=15, check=True, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                output = json.loads(result.stdout.decode('utf-8'))
            except (OSError, subprocess.SubprocessError, ValueError):
                raise OCRUnavailable('OCR worker failed') from None
        if not isinstance(output, dict):
            raise ValueError('invalid OCR output')
        text = output.get('text')
        language = output.get('language')
        if not isinstance(text, str) or not isinstance(language, str) or len(text) > 100000:
            raise ValueError('invalid OCR output')
        return text, language
    finally:
        SLOTS.release()
