from pathlib import Path
import shutil
import sys
import json
import os

from configure import configure_ocr_model

working_dir = Path(__file__).parent
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"


def install_deps():
    """
    Install dependencies from deps/bin to install directory.
    Since MFAAvalonia includes both binaries and MaaAgentBinary in the same root,
    we only need to copy from deps/bin.
    """
    source_dir = working_dir / "deps" / "bin"
    
    if not source_dir.exists():
        print("Please download the MaaFramework/MFAAvalonia to \"deps/bin\" first.")
        print("请先下载 MaaFramework/MFAAvalonia 到 \"deps/bin\"。")
        sys.exit(1)

    print(f"Copying dependencies from {source_dir} to {install_path}...")

    # Copy everything from deps/bin (includes DLLs, EXEs, and MaaAgentBinary folder)
    shutil.copytree(
        source_dir,
        install_path,
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
            # If there are other files in MFA you want to exclude, add them here
            "*.pdb", # Optional: Exclude debug symbols if not needed to reduce size
        ),
        dirs_exist_ok=True,
    )
    
    # The explicit copy for MaaAgentBinary is removed because it is now inside deps/bin


def install_resource():
    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )

    shutil.copytree(
        working_dir / "assets" / "resource_en",
        install_path / "resource_en",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = json.load(f)

    interface["version"] = version

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent():
    """Install agent source code to the install directory"""
    agent_src = working_dir / "agent"
    agent_dst = install_path / "agent"
    
    if not agent_src.exists():
        print("Warning: agent directory not found, skipping agent installation.")
        return
    
    # Create agent directory
    agent_dst.mkdir(parents=True, exist_ok=True)
    
    # Copy agent source files
    for item in agent_src.iterdir():
        if item.name in ["__pycache__"]:
            continue  # Skip cache directory
        
        dst_item = agent_dst / item.name
        if item.is_file():
            shutil.copy2(item, dst_item)
        elif item.is_dir():
            shutil.copytree(item, dst_item, dirs_exist_ok=True)
    
    print(f"Agent source files installed: {agent_src} -> {agent_dst}")


def install_tools():
    """Install tools scripts to the install directory"""
    tools_src = working_dir / "tools"
    tools_dst = install_path / "tools"
    
    if tools_src.exists():
        shutil.copytree(
            tools_src,
            tools_dst,
            dirs_exist_ok=True,
        )
        print(f"Tools installed: {tools_src} -> {tools_dst}")
    else:
        print("Warning: tools directory not found, skipping tools installation.")


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_tools()

    print(f"Install to {install_path} successfully.")