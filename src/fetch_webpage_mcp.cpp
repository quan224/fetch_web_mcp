#include <iostream>
#include <string>
#include <cstdio>
#include "nlohmann/json.hpp"
#include <windows.h>

using json = nlohmann::json;

#define FETCH_SCRIPT "\\scripts\\fetch_web.py"
#define LOG_FILE "\\__mcp_debug.log"

std::string GetExeDir() {
    char path[MAX_PATH];
    GetModuleFileNameA(NULL, path, MAX_PATH);
    std::string exePath(path);
    return exePath.substr(0, exePath.find_last_of("\\/"));
}

void DebugLog(const std::string& msg) {
    std::string logPath = GetExeDir() + LOG_FILE;
    HANDLE hLog = CreateFileA(logPath.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hLog != INVALID_HANDLE_VALUE) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        char prefix[64];
        int prefixLen = snprintf(prefix, sizeof(prefix), "[%02d:%02d:%02d.%03d] ", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
        DWORD written;
        WriteFile(hLog, prefix, prefixLen, &written, NULL);
        WriteFile(hLog, msg.c_str(), (DWORD)msg.size(), &written, NULL);
        WriteFile(hLog, "\n", 1, &written, NULL);
        CloseHandle(hLog);
    }
}

// 用 Win32 API 读文件，避免 CRT 文件描述符和 stdout 冲突
std::string ReadFileToString(const std::string& filePath) {
    HANDLE hFile = CreateFileA(filePath.c_str(), GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return "";

    LARGE_INTEGER fileSize;
    GetFileSizeEx(hFile, &fileSize);
    std::string content;
    content.resize((size_t)fileSize.QuadPart);

    DWORD bytesRead = 0;
    ReadFile(hFile, &content[0], (DWORD)content.size(), &bytesRead, NULL);
    content.resize(bytesRead);
    CloseHandle(hFile);
    return content;
}

// 调用计数器，确保每次用唯一的输出文件名，避免文件锁冲突
static int g_callId = 0;

// 将参数写入临时 JSON 文件，通过文件传参避免 CreateProcessA 的中文编码问题
std::string execPython(const std::string& script, const json& argsJson) {
    std::string exeDir = GetExeDir();
    std::string id = std::to_string(++g_callId);
    std::string outFile = exeDir + "\\__mcp_out_" + id + ".txt";
    std::string argsFile = exeDir + "\\__mcp_args_" + id + ".json";

    DebugLog("execPython start, args count=" + std::to_string(argsJson.size()));

    // 写参数到临时 JSON 文件（UTF-8）
    {
        std::string argsContent = argsJson.dump(-1, ' ', true);
        HANDLE hArgs = CreateFileA(argsFile.c_str(), GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hArgs == INVALID_HANDLE_VALUE) {
            DebugLog("FAIL: cannot create args file");
            return "error: cannot create args file";
        }
        DWORD written;
        WriteFile(hArgs, argsContent.c_str(), (DWORD)argsContent.size(), &written, NULL);
        CloseHandle(hArgs);
    }

    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.lpSecurityDescriptor = NULL;
    sa.bInheritHandle = TRUE;

    // 子进程 stdin → NUL
    HANDLE hNul = CreateFileA("NUL", GENERIC_READ, FILE_SHARE_READ, &sa, OPEN_EXISTING, 0, NULL);
    if (hNul == INVALID_HANDLE_VALUE) {
        DebugLog("FAIL: cannot open NUL");
        return "error: cannot open NUL";
    }

    // 子进程 stdout/stderr → 临时文件
    HANDLE hOut = CreateFileA(outFile.c_str(), GENERIC_WRITE, FILE_SHARE_READ, &sa, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hOut == INVALID_HANDLE_VALUE) {
        DebugLog("FAIL: cannot create output file, err=" + std::to_string(GetLastError()));
        CloseHandle(hNul);
        return "error: cannot create output file";
    }

    // 通过 python 调用脚本，传参数文件路径
    std::string cmdLine = "python \"" + script + "\" \"" + argsFile + "\"";
    char cmdBuf[4096];
    memcpy(cmdBuf, cmdLine.c_str(), cmdLine.size() + 1);

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    ZeroMemory(&pi, sizeof(pi));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdInput = hNul;
    si.hStdOutput = hOut;
    si.hStdError = hOut;

    SetHandleInformation(GetStdHandle(STD_INPUT_HANDLE), HANDLE_FLAG_INHERIT, 0);
    SetHandleInformation(GetStdHandle(STD_OUTPUT_HANDLE), HANDLE_FLAG_INHERIT, 0);
    SetHandleInformation(GetStdHandle(STD_ERROR_HANDLE), HANDLE_FLAG_INHERIT, 0);

    // 强制子进程使用 UTF-8 编码
    SetEnvironmentVariableA("PYTHONUTF8", "1");
    SetEnvironmentVariableA("PYTHONIOENCODING", "utf-8");

    DebugLog("CreateProcess: " + cmdLine);
    BOOL success = CreateProcessA(
        NULL, cmdBuf,
        NULL, NULL,
        TRUE,
        CREATE_NO_WINDOW,
        NULL, NULL,
        &si, &pi
    );

    CloseHandle(hNul);
    CloseHandle(hOut);

    if (!success) {
        DebugLog("FAIL: CreateProcess error " + std::to_string(GetLastError()));
        DeleteFileA(argsFile.c_str());
        return "error: CreateProcess failed (" + std::to_string(GetLastError()) + ")";
    }

    DebugLog("waiting for python...");
    WaitForSingleObject(pi.hProcess, 60000);

    DWORD exitCode = 0;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    if (exitCode == STILL_ACTIVE) {
        DebugLog("python timeout, terminating...");
        TerminateProcess(pi.hProcess, 1);
        exitCode = 1;
    }
    DebugLog("python exited code=" + std::to_string(exitCode));

    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    std::string output = ReadFileToString(outFile);
    DeleteFileA(outFile.c_str());
    DeleteFileA(argsFile.c_str());
    DebugLog("output read OK, length=" + std::to_string(output.size()));

    SetHandleInformation(GetStdHandle(STD_INPUT_HANDLE), HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT);
    SetHandleInformation(GetStdHandle(STD_OUTPUT_HANDLE), HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT);
    SetHandleInformation(GetStdHandle(STD_ERROR_HANDLE), HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT);

    return output;
}

void SendMessage(const json& msg) {
    std::string out;
    try {
        out = msg.dump();
    } catch (const json::exception& e) {
        DebugLog(std::string("dump() FAILED: ") + e.what());
        // dump 失败时用 ensure_ascii 安全模式重试
        try {
            out = msg.dump(-1, ' ', false, json::error_handler_t::replace);
        } catch (...) {
            DebugLog("dump() retry also failed");
            return;
        }
    }
    DebugLog("SEND start, length=" + std::to_string(out.size()));
    DWORD written;
    HANDLE hStdout = GetStdHandle(STD_OUTPUT_HANDLE);
    WriteFile(hStdout, out.c_str(), (DWORD)out.size(), &written, NULL);
    WriteFile(hStdout, "\n", 1, &written, NULL);
    FlushFileBuffers(hStdout);
    DebugLog("SEND done");
}

json HandleInitialize(const json& request) {
    return {
        {"jsonrpc", "2.0"},
        {"id", request["id"]},
        {"result", {
            {"protocolVersion", "2024-11-05"},
            {"capabilities", {{"tools", json::object()}, {"prompts", json::object()}}},
            {"serverInfo", {{"name", "fetch-webpage-mcp"}, {"version", "1.0.0"}}}
        }}
    };
}

// isHeadless 属性模板（所有工具共用）
#define IS_HEADLESS_PROP {"isHeadless", {{"type", "boolean"}, {"description", "run browser in headless mode (optional)"}}}

json HandleToolsList(const json& request) {
    return {
        {"jsonrpc", "2.0"},
        {"id", request["id"]},
        {"result", {
            {"tools", json::array({
                {
                    {"name", "navigate"},
                    {"description", "navigate to a URL and return page title and status code"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL to navigate to"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "content"},
                    {"description", "Get the visible text content and the list of interactive elements on the page"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL to get content"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "list_pages"},
                    {"description", "List all open tabs in the current browser"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }}
                    }}
                },
                {
                    {"name", "click"},
                    {"description", "Click an element on the page by selector (CSS, text, XPath, etc.)"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page to click on"}
                            }},
                            {"clicked_item", {
                                {"type", "string"},
                                {"description", "element selector to click (CSS: 'button.submit', text: 'text=Login', XPath: '//button[@type=\"submit\"]', etc.)"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url", "clicked_item"})}
                    }}
                },
                {
                    {"name", "extract"},
                    {"description", "Extract data from page elements matching a CSS selector"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page to extract data from"}
                            }},
                            {"selector", {
                                {"type", "string"},
                                {"description", "CSS selector to match elements (e.g. 'a[href]', '.price', 'table tr')"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url", "selector"})}
                    }}
                },
                {
                    {"name", "screenshot"},
                    {"description", "Take a screenshot of the page or a specific element"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page to screenshot"}
                            }},
                            {"selector", {
                                {"type", "string"},
                                {"description", "CSS selector to screenshot a specific element (optional, full page if omitted)"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "close_page"},
                    {"description", "Close a browser tab by URL domain"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL to match the tab to close (matched by domain)"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "fill"},
                    {"description", "Fill text into an input field"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page"}
                            }},
                            {"selector", {
                                {"type", "string"},
                                {"description", "CSS selector for the input field"}
                            }},
                            {"value", {
                                {"type", "string"},
                                {"description", "text content to fill in"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url", "selector", "value"})}
                    }}
                },
                {
                    {"name", "scroll"},
                    {"description", "Scroll the page up or down"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page"}
                            }},
                            {"direction", {
                                {"type", "string"},
                                {"description", "scroll direction: 'up' or 'down' (default: 'down')"}
                            }},
                            {"distance", {
                                {"type", "string"},
                                {"description", "scroll distance in pixels (default: 500)"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "shutdown"},
                    {"description", "Shutdown the browser and release the CDP debug port"},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }}
                    }}
                },
                {
                    {"name", "detect_popups"},
                    {"description", "Detect all popups (dialogs, modals, overlays) on the page. Returns list with type, content preview, and close button selector for each popup."},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page to detect popups on"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "close_popup"},
                    {"description", "Close a specific popup by selector. Supports 3 methods: click close button, press Escape key, or hide element directly."},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page"}
                            }},
                            {"selector", {
                                {"type", "string"},
                                {"description", "popup selector from detect_popups result"}
                            }},
                            {"close_button_selector", {
                                {"type", "string"},
                                {"description", "close button selector from detect_popups result (optional)"}
                            }},
                            {"method", {
                                {"type", "string"},
                                {"description", "close method: 'button' (click close btn), 'escape' (press Escape), 'hide' (set display:none). Default: 'button'"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url", "selector"})}
                    }}
                },
                {
                    {"name", "detect_ads"},
                    {"description", "Detect all ad elements on the page. Returns list with selector, size, position, and content info for each ad."},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page to detect ads on"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                },
                {
                    {"name", "close_ads"},
                    {"description", "Hide specific or all ad elements on the page by setting display:none. If no selector provided, hides all detected ads."},
                    {"inputSchema", {
                        {"type", "object"},
                        {"properties", {
                            {"url", {
                                {"type", "string"},
                                {"description", "the URL of the page"}
                            }},
                            {"selector", {
                                {"type", "string"},
                                {"description", "ad selector from detect_ads result (optional, hides all if omitted)"}
                            }},
                            {"browser_path", {
                                {"type", "string"},
                                {"description", "browser executable path (optional)"}
                            }},
                            IS_HEADLESS_PROP
                        }},
                        {"required", json::array({"url"})}
                    }}
                }
            })}
        }}
    };
}

json HandlePromptsList(const json& request) {
    return {
        {"jsonrpc", "2.0"},
        {"id", request["id"]},
        {"result", {
            {"prompts", json::array()}
        }}
    };
}

json HandlePromptsGet(const json& request) {
    std::string name = request.value("params", json::object()).value("name", "");
    return {
        {"jsonrpc", "2.0"},
        {"id", request["id"]},
        {"error", {{"code", -32602}, {"message", "Unknown prompt: " + name}}}
    };
}

json HandleToolsCall(const json& request) {
    auto params = request["params"];
    std::string tool_name = params.value("name", "");
    DebugLog("tools/call: " + tool_name);
    std::string result;

    // 构建 JSON 参数数组，通过临时文件传参，避免命令行中文编码问题
    auto buildArgs = [&](const std::vector<std::string>& required, const std::vector<std::string>& optional_keys) -> json {
        auto args = params.value("arguments", json::object());
        json arr = json::array({tool_name});
        for (auto& key : required) {
            arr.push_back(args.value(key, ""));
        }
        for (auto& key : optional_keys) {
            // 兼容 boolean/number/string 类型，统一转为 string
            if (args.contains(key) && args[key].is_boolean()) {
                arr.push_back(args[key].get<bool>() ? "true" : "false");
            } else {
                arr.push_back(args.value(key, ""));
            }
        }
        return arr;
    };

    if (tool_name == "navigate")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "content")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "list_pages")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({}, {"browser_path", "isHeadless"}));
    else if (tool_name == "click")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url", "clicked_item"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "extract")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url", "selector"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "screenshot")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url", "selector"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "close_page")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "fill")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url", "selector", "value"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "scroll")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url", "direction", "distance"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "shutdown")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({}, {"browser_path", "isHeadless"}));
    else if (tool_name == "detect_popups")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "close_popup")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url", "selector"}, {"close_button_selector", "method", "browser_path", "isHeadless"}));
    else if (tool_name == "detect_ads")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url"}, {"browser_path", "isHeadless"}));
    else if (tool_name == "close_ads")
        result = execPython(GetExeDir() + FETCH_SCRIPT, buildArgs({"url"}, {"selector", "browser_path", "isHeadless"}));
    else
        result = "unknown tool: " + tool_name;

    DebugLog("building JSON response...");
    json response = {
        {"jsonrpc", "2.0"},
        {"id", request["id"]},
        {"result", {{
            "content", json::array({
                {{"type", "text"}, {"text", result}}
            })
        }}}
    };
    DebugLog("JSON response built OK");
    return response;
}

int main() {
    // 清空旧日志
    std::string logPath = GetExeDir() + LOG_FILE;
    DeleteFileA(logPath.c_str());
    DebugLog("=== fetch-webpage-mcp starting ===");
    DebugLog("exeDir: " + GetExeDir());

    while (true) {
        std::string line;
        if (!std::getline(std::cin, line)) {
            DebugLog("stdin EOF, exiting");
            break;
        }
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;

        DebugLog("RECV: " + line.substr(0, 300));

        json request;
        try {
            request = json::parse(line);
        } catch (const json::exception& e) {
            DebugLog(std::string("JSON parse error: ") + e.what());
            continue;
        }

        std::string method = request.value("method", "");
        if (method == "notifications/initialized") continue;

        json response;
        if (method == "initialize") response = HandleInitialize(request);
        else if (method == "tools/list") response = HandleToolsList(request);
        else if (method == "tools/call") response = HandleToolsCall(request);
        else if (method == "prompts/list") response = HandlePromptsList(request);
        else if (method == "prompts/get") response = HandlePromptsGet(request);

        if (!response.is_null()) {
            DebugLog("calling SendMessage...");
            SendMessage(response);
        }
    }

    DebugLog("=== fetch-webpage-mcp exiting ===");
    return 0;
}
