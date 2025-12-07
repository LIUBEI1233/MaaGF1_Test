import sys
import os
import traceback
import time
import uuid
import threading
import platform

def get_executable_dir():
    """获取执行文件所在目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_project_root():
    """获取项目根目录"""
    current_dir = get_executable_dir()
    
    if getattr(sys, 'frozen', False):

        return os.path.dirname(os.path.dirname(current_dir))
    else:
        return os.path.dirname(current_dir)

def detect_arch():
    """检测当前系统架构并返回对应的目录名"""
    machine = platform.machine().lower()
    # 常见的返回值: 'amd64', 'x86_64', 'arm64'
    if 'arm' in machine or 'aarch64' in machine:
        return 'win-arm64'
    else:
        # 默认为 x64，涵盖 AMD64 和 Intel 64位
        return 'win-x64'

def setup_dll_path():
    """设置 DLL 路径，支持多架构 runtimes 目录"""
    current_dir = get_executable_dir()
    project_root = get_project_root()
    target_arch = detect_arch()
    
    print(f"Current directory: {current_dir}")
    print(f"Project root directory: {project_root}")
    print(f"Detected Architecture: {target_arch} (System: {platform.machine()})")
    print(f"Runtime environment: {'Packaged exe' if getattr(sys, 'frozen', False) else 'Development environment'}")
    
    # 定义可能的 DLL 搜索路径 (优先级从高到低)
    # 1. 新标准路径: runtimes/{arch}/native
    # 2. 旧兼容路径: 直接在根目录
    possible_paths = [
        os.path.join(project_root, "runtimes", target_arch, "native"),
        project_root
    ]
    
    # 关键 DLL 文件列表
    key_dlls = [
        "MaaFramework.dll",
        "MaaAgentServer.dll", 
        "MaaToolkit.dll"
    ]
    
    final_dll_dir = None
    
    # 遍历寻找包含关键 DLL 的目录
    for search_path in possible_paths:
        print(f"Checking for DLLs in: {search_path}")
        if not os.path.exists(search_path):
            continue
            
        # 检查该目录下是否包含 MaaFramework.dll (作为一个标志性文件)
        # 这里只检查主文件是否存在，避免因为缺少某个次要文件就跳过正确目录
        if os.path.exists(os.path.join(search_path, "MaaFramework.dll")):
            final_dll_dir = search_path
            print(f"-> Found valid DLL directory: {final_dll_dir}")
            break
    
    if final_dll_dir is None:
        print("Error: Could not find MaaFramework DLLs in any standard location.")
        print(f"Searched paths: {possible_paths}")
        sys.exit(1)

    # 再次确认所有关键文件是否存在（为了输出详细日志）
    missing_files = []
    for dll_name in key_dlls:
        dll_path = os.path.join(final_dll_dir, dll_name)
        if os.path.exists(dll_path):
            print(f"Verified {dll_name}: Found")
        else:
            print(f"Verified {dll_name}: Not Found!")
            missing_files.append(dll_name)
    
    if missing_files:
        print(f"Warning: Some key DLL files are missing: {missing_files}")
        # 这里可以选择是否强制退出，或者尝试继续运行
        # sys.exit(1)
    
    # 设置 MAAFW_BINARY_PATH 环境变量
    os.environ["MAAFW_BINARY_PATH"] = final_dll_dir
    print(f"Set MAAFW_BINARY_PATH: {final_dll_dir}")
    
    # 将 DLL 目录加入 PATH 环境变量的最前端
    old_path = os.environ.get("PATH", "")
    new_path = final_dll_dir + os.pathsep + old_path
    os.environ["PATH"] = new_path
    print(f"Added DLL directory to PATH")
    
    # 设置其他环境变量
    os.environ["MAA_LIBRARY_PATH"] = final_dll_dir
    
    return final_dll_dir, project_root

def generate_socket_id():
    """生成唯一的 socket_id"""
    return f"maa_agent_{uuid.uuid4().hex[:8]}"

# ======================================================================================
# 主程序逻辑开始
# ======================================================================================

# 在导入 MaaFramework 之前设置 DLL 路径和环境变量
print("Starting DLL environment setup...")
try:
    dll_dir, project_root = setup_dll_path()
    print("DLL environment setup completed")
except Exception as e:
    print(f"Critical Error during DLL setup: {e}")
    traceback.print_exc()
    sys.exit(1)

# 导入 maa 模块
try:
    print("Starting to import MaaFramework modules...")
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(dll_dir)
            print(f"Added DLL directory via os.add_dll_directory: {dll_dir}")
        except Exception as e:
            print(f"Warning: os.add_dll_directory failed: {e}")

    from maa.agent.agent_server import AgentServer
    from maa.toolkit import Toolkit
    print("MaaFramework modules imported successfully")
except Exception as e:
    print(f"MaaFramework module import failed: {e}")
    print("Detailed error information:")
    traceback.print_exc()
    
    print(f"\nDebug information:")
    print(f"MAAFW_BINARY_PATH: {os.environ.get('MAAFW_BINARY_PATH', 'Not set')}")
    print(f"First few PATH directories: {os.environ.get('PATH', '')[:200]}...")
    sys.exit(1)

# 导入自定义模块
try:
    print("Starting to import custom modules...")
    import my_reco
    import action
    from action import get_global_watchdog
    print("Custom modules imported successfully")
    
except Exception as e:
    print(f"Custom module import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# 加载配置文件
try:
    print("Starting to load configuration file...")
    
    # 修正配置文件路径
    if getattr(sys, 'frozen', False):
        # 打包环境: 配置文件在项目根目录的 agent 子目录下
        config_path = os.path.join(project_root, "agent", "agent.conf")
    else:
        # 开发环境: 配置文件在当前目录
        config_path = os.path.join(get_executable_dir(), "agent.conf")
    
    print(f"Configuration file path: {config_path}")
    
    from utils import load_config, get_watchdog_interval, is_watchdog_interval_configured
    load_config(config_path)
    print("Configuration file loading completed")
    
    # 从配置获取 watchdog 间隔
    watchdog_interval = get_watchdog_interval()
    interval_from_config = is_watchdog_interval_configured()
    
    print(f"Watchdog check interval: {watchdog_interval} seconds ({'from config file' if interval_from_config else 'using default'})")
    
except Exception as e:
    print(f"Configuration file loading failed: {e}")
    traceback.print_exc()
    # 如果加载失败，设置默认 watchdog 间隔
    watchdog_interval = 5.0
    print(f"Using fallback watchdog interval: {watchdog_interval} seconds")

class CustomAgentServer:
    """
    带有 Watchdog 监控的自定义 AgentServer 包装类
    """
    
    def __init__(self, watchdog_check_interval=None):
        # 使用提供的间隔或从全局配置获取
        if watchdog_check_interval is not None:
            self._watchdog_check_interval = float(watchdog_check_interval)
        else:
            try:
                from utils import get_watchdog_interval
                self._watchdog_check_interval = get_watchdog_interval()
            except:
                # 如果 config 模块不可用，使用回退值
                self._watchdog_check_interval = 5.0
        
        print(f"CustomAgentServer initialized with watchdog check interval: {self._watchdog_check_interval} seconds")
        
        self._watchdog_thread = None
        self._stop_event = threading.Event()
        self._watchdog = get_global_watchdog()
    
    def _watchdog_monitor_loop(self):
        """
        运行在独立线程中的 Watchdog 监控循环
        """
        print(f"Watchdog monitor thread started (check interval: {self._watchdog_check_interval}s)")
        
        while not self._stop_event.wait(self._watchdog_check_interval):
            try:
                if self._watchdog.poll():
                    print("Watchdog timeout detected, sending notification...")
                    self._watchdog.notify()
                    # 超时后继续监控
                else:
                    # Watchdog 健康，无需操作
                    pass
            except Exception as e:
                print(f"Watchdog monitor exception: {e}")
                traceback.print_exc()
        
        print("Watchdog monitor thread stopped")
    
    def start_up(self, socket_id):
        """启动 AgentServer 并开启 Watchdog 监控"""
        # 启动原始 AgentServer
        print("Starting to launch AgentServer...")
        AgentServer.start_up(socket_id)
        print("AgentServer started successfully")
        
        # 启动 watchdog 监控线程
        self._stop_event.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_monitor_loop,
            daemon=True,
            name="WatchdogMonitor"
        )
        self._watchdog_thread.start()
        print(f"Watchdog monitor thread started with {self._watchdog_check_interval}s interval")
    
    def join(self):
        """等待 AgentServer 完成"""
        # 这将阻塞直到连接结束
        AgentServer.join()
    
    def shut_down(self):
        """关闭 AgentServer 并停止 Watchdog 监控"""
        # 停止 watchdog 监控
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            print("Stopping watchdog monitor thread...")
            self._stop_event.set()
            self._watchdog_thread.join(timeout=10)
            if self._watchdog_thread.is_alive():
                print("Warning: Watchdog monitor thread did not stop gracefully")
            else:
                print("Watchdog monitor thread stopped")
        
        # 关闭原始 AgentServer
        AgentServer.shut_down()
    
    def set_watchdog_check_interval(self, interval):
        """设置 watchdog 检查间隔 (需要重启生效)"""
        try:
            interval = float(interval)
            if interval > 0:
                self._watchdog_check_interval = interval
                print(f"Watchdog check interval updated to: {interval} seconds (restart required)")
                return True
            else:
                print(f"Invalid watchdog interval: {interval}, must be positive")
                return False
        except (ValueError, TypeError):
            print(f"Invalid watchdog interval format: {interval}")
            return False
    
    def get_watchdog_check_interval(self):
        """获取当前 watchdog 检查间隔"""
        return self._watchdog_check_interval
    
    # 如果需要，暴露其他 AgentServer 方法
    @staticmethod
    def custom_action(name):
        """自定义动作装饰器"""
        return AgentServer.custom_action(name)

def main():
    
    try:
        print("Starting to initialize MaaFramework...")
        # 传入计算好的 dll_dir
        Toolkit.init_option(dll_dir)
        print("MaaFramework initialization completed")

        # 处理 socket_id 参数
        print(f"Command line arguments: {sys.argv}")
        
        if len(sys.argv) >= 2:
            # 如果提供了参数，使用第一个参数作为 socket_id
            socket_id = sys.argv[1]
            print(f"Using socket_id provided from command line: {socket_id}")
        else:
            # 如果未提供参数，自动生成 socket_id
            socket_id = generate_socket_id()
            print(f"Auto-generated socket_id: {socket_id}")
        
        print(f"Final socket_id to use: {socket_id}")

        # 创建带有 watchdog 支持的自定义 agent server
        # 传入配置中的 watchdog 间隔
        custom_agent_server = CustomAgentServer(watchdog_interval)
        
        # 启动服务器
        custom_agent_server.start_up(socket_id)
        
        # 等待 AgentServer 完全启动
        print("Waiting for AgentServer to fully start...")
        time.sleep(2)
        print("AgentServer startup wait completed")
        print("Starting to wait for connections...")
        
        # AgentServer.join() 将阻塞直到连接结束
        custom_agent_server.join()
        print("AgentServer connection ended")
        
        # 清理资源
        custom_agent_server.shut_down()
        print("All services shutdown completed")

    except Exception as e:
        print(f"Service startup failed: {e}")
        print("Detailed error information:")
        traceback.print_exc()
        
        # 输出调试信息
        print(f"\nDebug information:")
        print(f"Current working directory: {os.getcwd()}")
        print(f"MAAFW_BINARY_PATH: {os.environ.get('MAAFW_BINARY_PATH', 'Not set')}")
        print(f"Command line arguments: {sys.argv}")
        
        try:
            AgentServer.shut_down()
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()