cmake_minimum_required(VERSION 3.15)
project(fetch_webpage_mcp)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# UTF-8 source encoding for MSVC
if(MSVC)
    add_compile_options(/utf-8)
endif()

# nlohmann/json 头文件（已包含在 src/nlohmann/ 中）
include_directories(${CMAKE_SOURCE_DIR}/src)

# 编译 MCP 服务主程序
add_executable(fetch-webpage-mcp src/fetch_webpage_mcp.cpp)

# ========== 构建后自动复制运行时文件到 exe 旁边 ==========

set(RUNTIME_DIR "$<TARGET_FILE_DIR:fetch-webpage-mcp>")

# 1. Python 脚本 → <exe>/scripts/
add_custom_command(TARGET fetch-webpage-mcp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/scripts" "${RUNTIME_DIR}/scripts"
    COMMENT "Copying Python scripts..."
)

# 2. Skills → <exe>/skills/（每个子目录是一个技能，含 SKILL.md 及相关资源）
add_custom_command(TARGET fetch-webpage-mcp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/skills" "${RUNTIME_DIR}/skills"
    COMMENT "Copying skills..."
)
