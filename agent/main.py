import sys
import os
import traceback
import time
import uuid
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
            
        if os.path.exists(os.path.join(search_path, "MaaFramework.dll")):
            final_dll_dir = search_path
            print(f"-> Found valid DLL directory: {final_dll_dir}")
            break
    
    if final_dll_dir is None:
        print("Error: Could not find MaaFramework DLLs in any standard location.")
        print(f"Searched paths: {possible_paths}")
        sys.exit(1)

    # 再次确认所有关键文件是否存在
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
    traceback.print_exc()
    sys.exit(1)

# 导入自定义模块
try:
    print("Starting to import custom modules...")
    import my_reco
    import action
    # 注意：action 模块现在只包含 log 和 borderless，不再包含 watchdog
    print("Custom modules imported successfully")
    
except Exception as e:
    print(f"Custom module import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# 加载配置文件
try:
    print("Starting to load configuration file...")
    
    if getattr(sys, 'frozen', False):
        config_path = os.path.join(project_root, "agent", "agent.conf")
    else:
        config_path = os.path.join(get_executable_dir(), "agent.conf")
    
    print(f"Configuration file path: {config_path}")
    
    from utils import load_config
    load_config(config_path)
    print("Configuration file loading completed")
    
except Exception as e:
    print(f"Configuration file loading failed: {e}")
    traceback.print_exc()

def main():
    try:
        print("Starting to initialize MaaFramework...")
        Toolkit.init_option(dll_dir)
        print("MaaFramework initialization completed")

        # 处理 socket_id 参数
        print(f"Command line arguments: {sys.argv}")
        
        if len(sys.argv) >= 2:
            socket_id = sys.argv[1]
            print(f"Using socket_id provided from command line: {socket_id}")
        else:
            socket_id = generate_socket_id()
            print(f"Auto-generated socket_id: {socket_id}")
        
        print(f"Final socket_id to use: {socket_id}")

        # 启动服务器
        print("Starting to launch AgentServer...")
        AgentServer.start_up(socket_id)
        print("AgentServer started successfully")
        
        # 等待 AgentServer 完全启动
        print("Waiting for AgentServer to fully start...")
        time.sleep(2)
        print("AgentServer startup wait completed")
        print("Starting to wait for connections...")
        
        # AgentServer.join() 将阻塞直到连接结束
        AgentServer.join()
        print("AgentServer connection ended")
        
        # 清理资源
        AgentServer.shut_down()
        print("All services shutdown completed")

    except Exception as e:
        print(f"Service startup failed: {e}")
        print("Detailed error information:")
        traceback.print_exc()
        
        try:
            AgentServer.shut_down()
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()