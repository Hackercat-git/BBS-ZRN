"""
NFC UID reader — Project ZRN
ByteBell Software

Reads the UID of a MIFARE Classic card via MFRC522 (SPI on Raspberry Pi).
MFRC522 -> Pi pin layout:
  SDA  -> GPIO 8  (CE0)
  SCK  -> GPIO 11 (SCLK)
  MOSI -> GPIO 10
  MISO -> GPIO 9
  IRQ  -> not connected
  GND  -> GND
  RST  -> GPIO 25
  3.3V -> 3.3V
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Try to load the real hardware library; fall back to a mock otherwise
try:
    from mfrc522 import SimpleMFRC522
    _HARDWARE = True
except (ImportError, RuntimeError):
    _HARDWARE = False
    logger.warning("MFRC522 unavailable — mock mode active")


class NFCReader:
    def __init__(self):
        self.reader = None
        if _HARDWARE:
            try:
                self.reader = SimpleMFRC522()
            except Exception as e:
                logger.warning(
                    f"MFRC522 hardware unreachable ({e}) — mock mode active. "
                    f"Check that SPI is enabled (dtparam=spi=on, requires reboot) "
                    f"and that the reader is connected."
                )
                self.reader = None

    def read_uid(self, timeout: float = 10.0) -> Optional[str]:
        """
        Wait for a card and return its UID as a hex string.
        Returns None on timeout or error.
        """
        if not _HARDWARE or self.reader is None:
            return self._mock_read()

        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                uid, _ = self.reader.read_no_block()
                if uid:
                    uid_hex = format(uid, 'X').zfill(8)
                    # Format as "D2 D6 22 B0"
                    formatted = ' '.join(
                        uid_hex[i:i+2] for i in range(0, len(uid_hex), 2)
                    )
                    logger.info(f"NFC read: {formatted}")
                    return formatted
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"NFC read error: {e}")
        return None

    def _mock_read(self) -> Optional[str]:
        """Mock for development without hardware."""
        logger.debug("Mock NFC read — returning test value")
        time.sleep(1)
        return "D2 D6 22 B0"

    def cleanup(self):
        """Clean up GPIO on shutdown."""
        if _HARDWARE:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass
