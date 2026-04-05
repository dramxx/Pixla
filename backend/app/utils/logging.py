import logging
import time
from functools import wraps
from typing import Any, Callable, Optional
from contextlib import contextmanager


# Create logger for app <-> model communications
def get_pipeline_logger(name: str) -> logging.Logger:
    """Get a logger for pipeline operations (diffusion, agent, etc.)"""
    logger = logging.getLogger(f"pixla.pipeline.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# Pre-configured loggers for different services
diffusion_logger = get_pipeline_logger("diffusion")
agent_logger = get_pipeline_logger("agent")
pipeline_logger = get_pipeline_logger("main")


def log_operation(
    logger: logging.Logger,
    operation: str,
    success: bool = True,
    details: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error: Optional[Exception] = None,
):
    """Log an operation with consistent format."""
    status = "✓" if success else "✗"
    msg = f"{status} {operation}"
    if duration_ms is not None:
        msg += f" ({duration_ms:.1f}ms)"
    if details:
        msg += f" | {details}"
    if error:
        msg += f" | Error: {type(error).__name__}: {error}"

    if success:
        logger.info(msg)
    else:
        logger.error(msg)


@contextmanager
def log_duration(logger: logging.Logger, operation: str):
    """Context manager to log operation duration."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        log_operation(logger, operation, success=True, duration_ms=duration_ms)


def timed(logger: logging.Logger, operation: str):
    """Decorator to log function execution time."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                log_operation(logger, operation, success=True, duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                log_operation(logger, operation, success=False, error=e, duration_ms=duration_ms)
                raise

        return wrapper

    return decorator
