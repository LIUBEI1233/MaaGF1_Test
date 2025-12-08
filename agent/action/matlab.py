import time
import math
import sys
import os
import gc
import json
import atexit
from typing import Dict, Any, Optional

# MaaFramework Imports
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

# Load config.py (Keep consistency with log.py)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Log function import (Optional, for internal debugging)
try:
    from .log import MaaLog_Debug, MaaLog_Info
except ImportError:
    # Fallback if log module is not fully initialized yet
    def MaaLog_Debug(msg): print(f"[Matlab-DEBUG] {msg}")
    def MaaLog_Info(msg): print(f"[Matlab-INFO] {msg}")

################################################################################ Part I : The Calculation Engine ################################################################################

class _MatlabEngine:
    """
    Singleton engine providing Turing-complete calculation environment.
    Stores variables and executes syntax.
    """
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self._call_count = 0
        MaaLog_Debug("_MatlabEngine initialized")

    def _get_context(self) -> Dict[str, Any]:
        """
        Construct the execution context.
        Injects built-in functions and current variables.
        """
        # Copy current variables to context
        ctx = self.variables.copy()
        
        # Inject System Constants/Functions
        ctx['_get_time'] = time.time()
        ctx['math'] = math
        ctx['abs'] = abs
        ctx['round'] = round
        ctx['min'] = min
        ctx['max'] = max
        ctx['int'] = int
        ctx['float'] = float
        ctx['str'] = str
        
        return ctx

    def update_variables(self, ctx: Dict[str, Any]):
        """
        Persist variables from context back to storage.
        Filters out built-ins and temporary system vars.
        """
        protected_keys = [
            '_get_time', 'math', '__builtins__', 
            'abs', 'round', 'min', 'max', 'int', 'float', 'str'
        ]
        
        for k, v in ctx.items():
            if k not in protected_keys:
                self.variables[k] = v

    def clear(self, target: str):
        """Memory management"""
        if target == 'all':
            self.variables.clear()
            MaaLog_Debug("MatlabEngine memory cleared (all)")
        elif target in self.variables:
            del self.variables[target]
            MaaLog_Debug(f"MatlabEngine variable cleared: {target}")

    def execute_command(self, syntax: str) -> bool:
        """
        Execute assignment or void function (e.g., "A = 1 + 2")
        """
        try:
            self._call_count += 1
            
            # Handle special 'clear' command
            if syntax.strip().startswith("clear "):
                target = syntax.strip().split(" ", 1)[1].strip()
                self.clear(target)
                return True

            ctx = self._get_context()
            
            # Execute with restricted builtins for basic safety
            exec(syntax, {"__builtins__": {}}, ctx)
            
            # Save state
            self.update_variables(ctx)
            
            # Periodic GC
            if self._call_count % 100 == 0:
                gc.collect()
                
            return True
        except Exception as e:
            MaaLog_Debug(f"Matlab Execution Error: '{syntax}' -> {e}")
            return False

    def evaluate_condition(self, syntax: str) -> bool:
        """
        Evaluate boolean expression (e.g., "A > 10")
        """
        try:
            ctx = self._get_context()
            # Eval returns the result of the expression
            result = eval(syntax, {"__builtins__": {}}, ctx)
            return bool(result)
        except Exception as e:
            MaaLog_Debug(f"Matlab Evaluation Error: '{syntax}' -> {e}")
            return False
            
    def get_variable(self, name: str) -> Any:
        """External access to variables (e.g. for logging)"""
        return self.variables.get(name, None)

# Global Singleton Instance
_matlab_engine = _MatlabEngine()

################################################################################ Part II : The Action Class ################################################################################

class _MatlabAction(CustomAction):
    """
    Action wrapper for MatlabEngine.
    Handles JSON parsing and Context flow control.
    """
    def __init__(self):
        super().__init__()
        self._action_count = 0
        MaaLog_Debug("_MatlabAction singleton created")

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            self._action_count += 1
            param = argv.custom_action_param
            
            # Parse parameter if it's a string (legacy/compatibility)
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except json.JSONDecodeError:
                    MaaLog_Debug("MatlabAction param is invalid JSON string")
                    return CustomAction.RunResult(success=False)
            
            if not isinstance(param, dict):
                 MaaLog_Debug("MatlabAction param must be a dictionary")
                 return CustomAction.RunResult(success=False)

            syntax = param.get('syntax', '')
            if not syntax:
                # No syntax means nothing to do, return success
                return CustomAction.RunResult(success=True)

            # Check logic branching mode
            target_true = param.get('true')
            target_false = param.get('false')

            if target_true or target_false:
                # --- Logic Mode ---
                result = _matlab_engine.evaluate_condition(syntax)
                
                if result:
                    if target_true:
                        MaaLog_Debug(f"[Matlab] '{syntax}' is True -> Jump to {target_true}")
                        context.override_next(argv.node_name, [target_true])
                    else:
                        MaaLog_Debug(f"[Matlab] '{syntax}' is True (No jump target)")
                else:
                    if target_false:
                        MaaLog_Debug(f"[Matlab] '{syntax}' is False -> Jump to {target_false}")
                        context.override_next(argv.node_name, [target_false])
                    else:
                        MaaLog_Debug(f"[Matlab] '{syntax}' is False (No jump target)")
            else:
                # --- Execution Mode ---
                success = _matlab_engine.execute_command(syntax)
                if not success:
                    return CustomAction.RunResult(success=False)

            return CustomAction.RunResult(success=True)

        except Exception as e:
            MaaLog_Debug(f"MatlabAction Critical Error: {e}")
            return CustomAction.RunResult(success=False)

################################################################################ Part III : Registration System ################################################################################

# Reuse the robust registration logic from log.py
_registration_status = {
    'registered': False,
    'instance': None
}

def _get_or_create_instance():
    if _registration_status['instance'] is None:
        _registration_status['instance'] = _MatlabAction()
    return _registration_status['instance']

def _safe_register_matlab(action_name: str):
    if _registration_status['registered']:
        return
    
    instance = _get_or_create_instance()
    success = AgentServer.register_custom_action(action_name, instance)
    
    if success:
        _registration_status['registered'] = True
        MaaLog_Debug(f"Successfully registered {action_name}")
    else:
        MaaLog_Debug(f"Failed to register {action_name}")

def custom_action_decorator(name: str):
    def wrapper(cls):
        _safe_register_matlab(name)
        return cls
    return wrapper

# Register the action
@custom_action_decorator("matlab_calculate")
class MatlabCalculateAction:
    pass

################################################################################ Part IV : Cleanup ################################################################################

def cleanup_matlab_resources():
    try:
        _matlab_engine.clear('all')
        gc.collect()
        MaaLog_Debug("Matlab resources cleaned up")
    except:
        pass

atexit.register(cleanup_matlab_resources)

# Export engine for external access (e.g. by log.py)
def get_matlab_engine():
    return _matlab_engine