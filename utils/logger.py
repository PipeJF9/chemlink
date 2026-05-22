"""Logging configuration for ChemLink project."""

import logging
import sys


def setup_logger(name: str, level: int = logging.WARNING) -> logging.Logger:
    """Configure and return a logger with consistent formatting.
    
    Args:
        name: Name of the logger (typically __name__)
        level: Logging level (default: WARNING)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler with simple format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get existing or create new logger.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
