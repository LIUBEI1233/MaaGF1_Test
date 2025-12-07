# Std Lib
import time
import ctypes
import sys
import os
import traceback
import json
import re

# Win32
import win32con
import win32gui
import win32process
import win32api
import win32ui
from ctypes import windll, wintypes, byref, sizeof

# CV
from PIL import Image, ImageGrab
import numpy as np

# MaaFramework
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

import pygetwindow as gw

class WindowOptimizer:
    """
    Window optimization class for borderless and resolution adjustment
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self.selected_window = None
        self.original_style = None
        self.original_ex_style = None
        self.original_rect = None
        self.calculated_size = None
        self.action_name = "WindowOptimizer"
    
    def _log_debug(self, message):
        """Internal debug logging"""
        from .log import MaaLog_Debug
        MaaLog_Debug(f"[WindowOptimizer] {message}")
    
    def _log_info(self, message):
        """Internal info logging"""
        from .log import MaaLog_Info
        MaaLog_Info(f"[WindowOptimizer] {message}")
    
    def find_target_window(self, window_title_pattern=None):
        """
        Find target window, prioritize game windows
        """
        try:
            windows = gw.getAllWindows()
            
            # If specific pattern provided, search for it
            if window_title_pattern:
                for window in windows:
                    if window.title and window.visible and window_title_pattern.lower() in window.title.lower():
                        self.selected_window = window
                        self._log_info(f"Found target window by pattern '{window_title_pattern}': {window.title}")
                        return True
            
            # Auto-detect game windows
            game_keywords = ['少女前线', 'girls', 'frontline', 'game']
            for window in windows:
                if window.title and window.visible:
                    title_lower = window.title.lower()
                    if any(keyword in title_lower for keyword in game_keywords):
                        self.selected_window = window
                        self._log_info(f"Auto-detected game window: {window.title}")
                        return True
            
            # If no game window found, try to get active window
            try:
                active_window = gw.getActiveWindow()
                if active_window and active_window.title and active_window.visible:
                    self.selected_window = active_window
                    self._log_info(f"Using active window: {active_window.title}")
                    return True
            except Exception as e:
                self._log_debug(f"Failed to get active window: {e}")
            
            self._log_debug("No suitable window found")
            return False
            
        except Exception as e:
            self._log_debug(f"Error finding target window: {e}")
            return False
    
    def analyze_dpi(self):
        """
        Analyze DPI settings for the selected window
        """
        if not self.selected_window:
            return 96, 1.0
        
        try:
            hwnd = self.selected_window._hWnd
            
            # Set DPI awareness
            ctypes.windll.user32.SetProcessDPIAware()
            
            try:
                dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            except:
                dpi = 96
            
            # Get system DPI
            dc = ctypes.windll.user32.GetDC(0)
            system_dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
            system_dpi_y = ctypes.windll.gdi32.GetDeviceCaps(dc, 90)
            ctypes.windll.user32.ReleaseDC(0, dc)
            
            scale_factor = dpi / 96.0
            
            self._log_debug(f"DPI analysis - Window DPI: {dpi}, System DPI: {system_dpi_x}x{system_dpi_y}, Scale: {scale_factor:.2f}")
            
            return dpi, scale_factor
            
        except Exception as e:
            self._log_debug(f"DPI analysis failed: {e}")
            return 96, 1.0
    
    def save_original_state(self):
        """
        Save original window state for restoration
        """
        if not self.selected_window:
            return False
        
        try:
            hwnd = self.selected_window._hWnd
            self.original_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            self.original_ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            self.original_rect = win32gui.GetWindowRect(hwnd)
            
            self._log_debug(f"Original state saved - Style: 0x{self.original_style:08X}, ExStyle: 0x{self.original_ex_style:08X}")
            self._log_debug(f"Original rect: {self.original_rect}")
            
            return True
        except Exception as e:
            self._log_debug(f"Failed to save original state: {e}")
            return False
    
    def set_dpi_awareness(self):
        """
        Set DPI awareness for proper scaling
        """
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except:
                pass
            return True
        except Exception as e:
            self._log_debug(f"Failed to set DPI awareness: {e}")
            return False
    
    def remove_window_decorations(self):
        """
        Remove window borders and decorations
        """
        if not self.selected_window:
            return False
        
        try:
            hwnd = self.selected_window._hWnd
            
            # Get current styles
            current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            current_ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            # Remove window decorations
            new_style = current_style
            new_style &= ~win32con.WS_CAPTION
            new_style &= ~win32con.WS_THICKFRAME
            new_style &= ~win32con.WS_BORDER
            new_style &= ~win32con.WS_DLGFRAME
            new_style &= ~win32con.WS_SYSMENU
            new_style &= ~win32con.WS_MINIMIZEBOX
            new_style &= ~win32con.WS_MAXIMIZEBOX
            
            new_ex_style = current_ex_style
            new_ex_style &= ~win32con.WS_EX_DLGMODALFRAME
            new_ex_style &= ~win32con.WS_EX_CLIENTEDGE
            new_ex_style &= ~win32con.WS_EX_STATICEDGE
            new_ex_style &= ~win32con.WS_EX_WINDOWEDGE
            
            # Apply new styles
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)
            
            # Disable DWM effects
            self.disable_dwm_effects(hwnd)
            
            # Force window to update
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                win32con.SWP_FRAMECHANGED | win32con.SWP_NOMOVE | 
                                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
            
            self._log_debug(f"Window decorations removed - New style: 0x{new_style:08X}, New ExStyle: 0x{new_ex_style:08X}")
            
            return True
        except Exception as e:
            self._log_debug(f"Failed to remove window decorations: {e}")
            return False
    
    def disable_dwm_effects(self, hwnd):
        """
        Disable Desktop Window Manager effects
        """
        try:
            dwmapi = ctypes.windll.dwmapi
            
            # Disable rounded corners
            try:
                corner_preference = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_preference), 4)
            except:
                pass
            
            # Disable window shadow
            try:
                no_shadow = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(no_shadow), 4)
            except:
                pass
            
        except Exception as e:
            self._log_debug(f"Failed to disable DWM effects: {e}")
    
    def calculate_correct_size(self, target_width, target_height, dpi_aware=True, force_dpi=None):
        """
        Calculate correct window size considering DPI scaling
        """
        if not self.selected_window:
            return False
        
        try:
            # Re-analyze DPI after border removal
            dpi, scale_factor = self.analyze_dpi()
            
            if dpi_aware:
                if force_dpi:
                    dpi_scale = force_dpi / 96.0
                else:
                    dpi_scale = scale_factor
                
                actual_width = int(target_width / dpi_scale)
                actual_height = int(target_height / dpi_scale)
            else:
                actual_width = target_width
                actual_height = target_height
            
            self.calculated_size = (actual_width, actual_height)
            
            self._log_debug(f"Size calculation - Target: {target_width}x{target_height}, Actual: {actual_width}x{actual_height}, DPI scale: {scale_factor:.2f}")
            
            return True
            
        except Exception as e:
            self._log_debug(f"Failed to calculate correct size: {e}")
            return False
    
    def apply_final_size(self, precise_positioning=True, topmost=False):
        """
        Apply calculated size and positioning
        """
        if not hasattr(self, 'calculated_size') or not self.calculated_size:
            return False
        
        if not self.selected_window:
            return False
        
        try:
            hwnd = self.selected_window._hWnd
            width, height = self.calculated_size
            
            # Get current position
            current_rect = win32gui.GetWindowRect(hwnd)
            current_x = current_rect[0]
            current_y = current_rect[1]
            
            # Adjust position if needed
            if precise_positioning:
                screen_width = win32api.GetSystemMetrics(0)
                screen_height = win32api.GetSystemMetrics(1)
                
                if current_x + width > screen_width:
                    current_x = screen_width - width
                if current_y + height > screen_height:
                    current_y = screen_height - height
                if current_x < 0:
                    current_x = 0
                if current_y < 0:
                    current_y = 0
            
            # Apply size and position
            win32gui.SetWindowPos(hwnd, 0, current_x, current_y, width, height, 
                                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
            
            # Set topmost if requested
            if topmost:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            
            self._log_debug(f"Final size applied - Position: ({current_x}, {current_y}), Size: {width}x{height}, Topmost: {topmost}")
            
            return True
        except Exception as e:
            self._log_debug(f"Failed to apply final size: {e}")
            return False
    
    def execute_optimization(self, target_width=1280, target_height=720, 
                           window_pattern=None, dpi_aware=True, force_dpi=None,
                           disable_dwm=True, topmost=False, precise_positioning=True):
        """
        Execute complete window optimization
        """
        with self._lock:
            try:
                self._log_info("Starting window optimization...")
                
                # Step 1: Find target window
                if not self.find_target_window(window_pattern):
                    self._log_debug("Failed to find target window")
                    return False
                
                time.sleep(0.1)
                
                # Step 2: Save original state
                if not self.save_original_state():
                    self._log_debug("Failed to save original state")
                    return False
                
                time.sleep(0.2)
                
                # Step 3: Set DPI awareness
                if not self.set_dpi_awareness():
                    self._log_debug("Failed to set DPI awareness")
                    return False
                
                time.sleep(0.2)
                
                # Step 4: Remove window decorations
                if not self.remove_window_decorations():
                    self._log_debug("Failed to remove window decorations")
                    return False
                
                time.sleep(0.5)  # Wait for border removal to complete
                
                # Step 5: Calculate correct size
                if not self.calculate_correct_size(target_width, target_height, dpi_aware, force_dpi):
                    self._log_debug("Failed to calculate correct size")
                    return False
                
                time.sleep(0.2)
                
                # Step 6: Apply final size and positioning
                if not self.apply_final_size(precise_positioning, topmost):
                    self._log_debug("Failed to apply final size")
                    return False
                
                time.sleep(0.5)  # Wait for size application to complete
                
                self._log_info(f"Window optimization completed - Target: {target_width}x{target_height}, Window: {self.selected_window.title}")
                
                return True
                
            except Exception as e:
                self._log_debug(f"Optimization failed: {e}")
                import traceback
                self._log_debug(f"Stack trace: {traceback.format_exc()}")
                return False
    
    def restore_original_state(self):
        """
        Restore window to original state
        """
        with self._lock:
            if not self.selected_window or not self.original_style:
                self._log_debug("No saved state to restore")
                return False
            
            try:
                hwnd = self.selected_window._hWnd
                
                # Restore original styles
                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, self.original_style)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, self.original_ex_style)
                
                # Restore original size and position
                if self.original_rect:
                    x, y, right, bottom = self.original_rect
                    width = right - x
                    height = bottom - y
                    win32gui.SetWindowPos(hwnd, 0, x, y, width, height, win32con.SWP_NOZORDER)
                
                # Force window update
                win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                    win32con.SWP_FRAMECHANGED | win32con.SWP_NOMOVE | 
                                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                
                self._log_info(f"Window state restored - Window: {self.selected_window.title}")
                
                # Clear saved state
                self.original_style = None
                self.original_ex_style = None
                self.original_rect = None
                self.calculated_size = None
                
                return True
                
            except Exception as e:
                self._log_debug(f"Failed to restore original state: {e}")
                import traceback
                self._log_debug(f"Stack trace: {traceback.format_exc()}")
                return False
    
    def verify_optimization(self, target_width, target_height):
        """
        Verify optimization results
        """
        if not self.selected_window:
            return False, "No window selected"
        
        try:
            hwnd = self.selected_window._hWnd
            
            window_rect = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)
            
            window_width = window_rect[2] - window_rect[0]
            window_height = window_rect[3] - window_rect[1]
            client_width = client_rect[2]
            client_height = client_rect[3]
            
            # Check if borderless (window size equals client size)
            is_borderless = (window_width == client_width and window_height == client_height)
            
            # Check size match (allow 2px tolerance)
            width_match = abs(client_width - target_width) <= 2
            height_match = abs(client_height - target_height) <= 2
            size_match = width_match and height_match
            
            status = "Optimized" if (is_borderless and size_match) else "Needs re-optimization"
            
            result = {
                "status": status,
                "is_borderless": is_borderless,
                "size_match": size_match,
                "window_size": (window_width, window_height),
                "client_size": (client_width, client_height),
                "target_size": (target_width, target_height),
                "size_difference": (abs(client_width - target_width), abs(client_height - target_height))
            }
            
            self._log_debug(f"Verification result: {result}")
            
            return True, result
            
        except Exception as e:
            self._log_debug(f"Verification failed: {e}")
            return False, f"Verification error: {str(e)}"

# Global window optimizer instance
_global_optimizer = WindowOptimizer()

def get_global_optimizer():
    """Get global window optimizer instance"""
    return _global_optimizer

@AgentServer.custom_action("borderless_optimize")
class BorderlessOptimizeAction(CustomAction):
    """
    Borderless window optimization action
    """
    
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            param = argv.custom_action_param
            
            from .log import MaaLog_Debug, MaaLog_Info
            MaaLog_Debug(f"BorderlessOptimizeAction param: {param} (type: {type(param)})")
            
            # Parse parameters
            target_width = 1280
            target_height = 720
            window_pattern = None
            dpi_aware = True
            force_dpi = None
            disable_dwm = True
            topmost = False
            precise_positioning = True
            
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except json.JSONDecodeError:
                    # If not JSON, treat as window pattern
                    window_pattern = param
            
            if isinstance(param, dict):
                target_width = param.get('target_width', 1280)
                target_height = param.get('target_height', 720)
                window_pattern = param.get('window_pattern', None)
                dpi_aware = param.get('dpi_aware', True)
                force_dpi = param.get('force_dpi', None)
                disable_dwm = param.get('disable_dwm', True)
                topmost = param.get('topmost', False)
                precise_positioning = param.get('precise_positioning', True)
            
            optimizer = get_global_optimizer()
            success = optimizer.execute_optimization(
                target_width=target_width,
                target_height=target_height,
                window_pattern=window_pattern,
                dpi_aware=dpi_aware,
                force_dpi=force_dpi,
                disable_dwm=disable_dwm,
                topmost=topmost,
                precise_positioning=precise_positioning
            )
            
            if success:
                MaaLog_Info(f"Window optimization completed successfully - {target_width}x{target_height}")
            else:
                MaaLog_Info("Window optimization failed")
            
            return CustomAction.RunResult(success=success)
            
        except Exception as e:
            from .log import MaaLog_Debug
            MaaLog_Debug(f"BorderlessOptimizeAction exception: {e}")
            import traceback
            MaaLog_Debug(f"Exception stack: {traceback.format_exc()}")
            return CustomAction.RunResult(success=False)

@AgentServer.custom_action("borderless_revert")
class BorderlessRevertAction(CustomAction):
    """
    Revert borderless optimization action
    """
    
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            from .log import MaaLog_Debug, MaaLog_Info
            MaaLog_Debug(f"BorderlessRevertAction called")
            
            optimizer = get_global_optimizer()
            success = optimizer.restore_original_state()
            
            if success:
                MaaLog_Info("Window state restored successfully")
            else:
                MaaLog_Info("Window state restoration failed")
            
            return CustomAction.RunResult(success=success)
            
        except Exception as e:
            from .log import MaaLog_Debug
            MaaLog_Debug(f"BorderlessRevertAction exception: {e}")
            import traceback
            MaaLog_Debug(f"Exception stack: {traceback.format_exc()}")
            return CustomAction.RunResult(success=False)