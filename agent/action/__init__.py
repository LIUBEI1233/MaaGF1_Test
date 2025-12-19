"""
Action package initialization
Provides unified access to all action module functionalities
"""

# Import submodules
from . import log
from . import matlab

# Import commonly used functions from log
from .log import (
    MaaLog_Debug, 
    MaaLog_Info,
    Task_Counter,
    Enable_MaaLog_Debug,
    Enable_MaaLog_Info
)

# Import Matlab engine accessor if needed externally
from .matlab import get_matlab_engine

# Define what gets exported when using "from action import *"
__all__ = [
    # Submodules
    'log', 
    'matlab',
    
    # Logging functions
    'MaaLog_Debug',
    'MaaLog_Info',
    
    # Global variables
    'Task_Counter',
    'Enable_MaaLog_Debug',
    'Enable_MaaLog_Info',
    
    # Accessors
    'get_matlab_engine'
]

# Package metadata
__version__ = '1.1.0'
__author__ = 'MaaGF1 Team'
__description__ = 'Action module for MaaFramework agent (Log & Matlab)'