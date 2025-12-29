// hook_response.js - 抓取解密后的响应内容

// --- 地址配置 (保持你之前的 JSON 地址) ---
var addr_DecodeWithGzip = 21054368; // AC.AuthCode$$DecodeWithGzip

// --- 辅助函数：读取 C# 字节数组 (System.Byte[]) ---
function readCSharpByteArray(ptr) {
    if (ptr.isNull()) return "null";
    try {
        // Unity/Il2Cpp 数组结构:
        // +0x00: Class Pointer
        // +0x08: Monitor
        // +0x10: Bounds
        // +0x18: Length (Int32) - 这里的偏移量取决于 Unity 版本，通常是 0x18
        // +0x20: Data Start     - 数据通常从 0x20 开始
        
        // 这是一个启发式读取，针对 64位 Il2Cpp
        var len = ptr.add(0x18).readU32();
        
        // 保护性检查：如果长度大得离谱，可能偏移量不对
        if (len > 1000000) {
             return "Array too large or invalid ptr";
        }

        // 读取数据区
        var dataPtr = ptr.add(0x20);
        var bytes = dataPtr.readByteArray(len);
        
        // 尝试转为字符串 (UTF-8)
        // 多数游戏通信是 UTF-8 字符串
        var str = "";
        var u8 = new Uint8Array(bytes);
        // 简单的转换，防止包含非打印字符导致控制台乱码
        // 如果确认是纯文本 JSON，可以直接 TextDecoder，这里用简单过滤
        for (var i = 0; i < len; i++) {
            if (u8[i] >= 32 && u8[i] <= 126) {
                str += String.fromCharCode(u8[i]);
            } else {
                // 如果包含大量非文本，可能还是二进制
                // str += "."; 
            }
        }
        
        // 如果看起来像 JSON，直接返回字符串，否则返回 Hex
        if (str.length > 0 && (str.startsWith("{") || str.startsWith("["))) {
            return "[JSON] " + str;
        } else {
            return "[Hex] Length: " + len + " (可能是二进制数据)";
        }

    } catch (e) {
        return "Array Read Error: " + e.message;
    }
}

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hook() {
    console.log("==================================================");
    console.log("[Step 1] 针对 DecodeWithGzip 挂载返回值 Hook...");

    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) return;

    var targetAddr = gameAssembly.add(addr_DecodeWithGzip);

    Interceptor.attach(targetAddr, {
        onEnter: function(args) {
            // 标记进入，不需要打印太多，防止刷屏
            this.is_target = true; 
        },
        onLeave: function(retval) {
            if (this.is_target) {
                console.log("\n[!] >>> DecodeWithGzip 执行完毕，捕获返回值 <<<");
                
                // retval 是指向 System.Byte[] 的指针
                var result = readCSharpByteArray(retval);
                
                // 打印结果（限制长度防止卡死）
                if (result.length > 500) {
                    console.log(result.substring(0, 500) + " ... (剩余内容已截断)");
                } else {
                    console.log(result);
                }
                console.log("--------------------------------------------------");
            }
        }
    });

    console.log("[+] Hook 就绪，请触发网络请求（如点击任务、编队等）");
}

setTimeout(hook, 1000);