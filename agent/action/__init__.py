"""
Action package initialization
Provides unified access to all action module functionalities
"""

# Import submodules
from . import borderless

# Import log module
from . import log

# Import commonly used functions and classes for convenient access
from .log import (
    MaaLog_Debug, 
    MaaLog_Info,
    Task_Counter,
    Enable_MaaLog_Debug,
    Enable_MaaLog_Info
)

# Import borderless functions
from .borderless import get_global_optimizer

# Define what gets exported when using "from action import *"
__all__ = [
    # Submodules
    'log', 
    'borderless',
    
    # Logging functions
    'MaaLog_Debug',
    'MaaLog_Info',
    
    # Borderless functions
    'get_global_optimizer',
    
    # Global variables
    'Task_Counter',
    'Enable_MaaLog_Debug',
    'Enable_MaaLog_Info'
]

# Package metadata
__version__ = '1.0.1'
__author__ = 'MaaGF1 Team'
__description__ = 'Action module for MaaFramework agent (Refactored)'