import logging
import sys
import os
import structlog

def setup_logging():
    """
    Configures structured logging for the application.
    
    This setup provides two modes controlled by the LOG_MODE environment variable:
    - 'json' (default): For production, outputs structured JSON.
    - 'console': For development, outputs human-readable, colored logs.
    """
    is_dev_mode = os.getenv("LOG_MODE", "json").lower() == "console"

    # These processors are shared between development and production formats.
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,  # Handles exceptions cleanly
    ]

    structlog.configure(
        processors=shared_processors + [
            # This prepares the log record for the standard library's formatter.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure the renderer and formatter based on the mode.
    if is_dev_mode:
        # Human-readable, colored output for development.
        renderer = structlog.dev.ConsoleRenderer()
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer,
        )
    else:
        # Structured JSON output for production.
        renderer = structlog.processors.JSONRenderer()
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )

    # Set up the handler to output to the console.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure the root logger.
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to prevent duplicate logs.
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # --- Silence Noisy Libraries ---
    # Set the log level for overly verbose libraries to WARNING,
    # so their INFO messages don't clutter the output.
    for lib in ["sentence_transformers", "httpx", "numba", "torch.distributed"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    print(f"✅ Structured logging configured in '{'CONSOLE' if is_dev_mode else 'JSON'}' mode.")