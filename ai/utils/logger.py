"""
Shared logger for the application.
Writes to logs/app.log with rotation and also outputs to console.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if handlers haven't been added yet
    if not logger.handlers:
        # Attempt to configure std streams to UTF-8 where supported (Python 3.7+)
        try:
            if hasattr(sys.stdout, "reconfigure"):
                try:
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    # Best-effort only; continue if it fails
                    pass
            if hasattr(sys.stderr, "reconfigure"):
                try:
                    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        except Exception:
            # Defensive: do not let stream reconfiguration break startup
            pass
        # Get log level from environment, default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Ensure logs directory exists
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler with rotation (10MB per file, keep 5 backups)
        # File handler with rotation (10MB per file, keep 5 backups)
        # Explicitly use UTF-8 for log files to retain all characters
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )

        # Console handler: use a safe wrapper that avoids UnicodeEncodeError
        class SafeStreamHandler(logging.StreamHandler):
            """StreamHandler that safely writes Unicode to streams with limited encodings.

            It attempts to write the formatted message directly. If a
            UnicodeEncodeError occurs (common on Windows consoles using cp1252),
            it will either reconfigure the stream to UTF-8 (if supported) or
            sanitize the message by encoding/decoding with 'replace' using the
            stream's encoding so the handler never raises on write.
            """

            def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - logging glue
                try:
                    msg = self.format(record)
                    stream = self.stream
                    terminator = getattr(self, "terminator", "\n")

                    try:
                        stream.write(msg + terminator)
                    except UnicodeEncodeError:
                        # Try to reconfigure the stream to UTF-8 if possible
                        try:
                            if hasattr(stream, "reconfigure"):
                                stream.reconfigure(encoding="utf-8", errors="replace")
                                stream.write(msg + terminator)
                                self.flush()
                                return
                        except Exception:
                            pass

                        # Fallback: sanitize message for the stream encoding
                        encoding = getattr(stream, "encoding", None) or "utf-8"
                        safe_msg = msg.encode(encoding, errors="replace").decode(encoding)
                        stream.write(safe_msg + terminator)

                    self.flush()
                except Exception:
                    self.handleError(record)

        console_handler = SafeStreamHandler()

        # Format: timestamp | level | logger name | message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
