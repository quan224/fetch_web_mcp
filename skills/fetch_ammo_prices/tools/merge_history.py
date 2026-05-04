# -*- coding: utf-8 -*-
"""
合并 data/ 目录下所有 ammo_prices_*.json 文件为时序数据
输出 JSON 格式的 HISTORY 数据，供嵌入 HTML
"""

import json
import glob
import os
import re
from datetime import datetime, timedelta
from collections import OrderedDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(SKILL_DIR, "data")


def parse_time_from_filename(fname):
    """从文件名提取时间: ammo_prices_20260504_1417.json -> (20260504, 1417)"""
    m = re.search(r'(\d{8})_(\d{4})', fname)
    if m:
        return m.group(1), m.group(2)
    return None, None


def format_time_label(date_str, time_str):
    """格式化时间标签: 20260504, 1417 -> 05-04 14:17"""
    month = date_str[4:6]
    day = date_str[6:8]
    hour = time_str[:2]
    minute = time_str[2:]
    return f"{month}-{day} {hour}:{minute}"


def merge_history():
    # 查找所有数据文件并按时间排序
    pattern = os.path.join(DATA_DIR, "ammo_prices_*.json")
    files = sorted(glob.glob(pattern))

    # 只保留最近7天的文件
    cutoff = datetime.now() - timedelta(days=7)
    filtered_files = []
    for f in files:
        date_str, _ = parse_time_from_filename(os.path.basename(f))
        if date_str:
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date >= cutoff:
                filtered_files.append(f)
    files = filtered_files

    if not files:
        print(json.dumps({"timePoints": [], "series": []}, ensure_ascii=False))
        return

    # 解析所有快照
    snapshots = []
    for f in files:
        date_str, time_str = parse_time_from_filename(os.path.basename(f))
        if date_str is None:
            continue
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        snapshots.append({
            "timeLabel": format_time_label(date_str, time_str),
            "ammo": {a["name"]: a for a in data["ammo"]}
        })

    if not snapshots:
        print(json.dumps({"timePoints": [], "series": []}, ensure_ascii=False))
        return

    # 收集所有 grade>=3 且至少一次 price>0 的子弹名称
    bullet_names = set()
    for snap in snapshots:
        for name, a in snap["ammo"].items():
            if a["grade"] >= 3 and a["currentPrice"] > 0:
                bullet_names.add(name)

    # 按等级降序、名称排序
    def sort_key(name):
        # 获取最高等级
        grade = 0
        for snap in snapshots:
            if name in snap["ammo"]:
                grade = max(grade, snap["ammo"][name]["grade"])
        return (-grade, name)

    sorted_names = sorted(bullet_names, key=sort_key)

    # 构建时序数据
    time_points = [snap["timeLabel"] for snap in snapshots]
    series = []
    for name in sorted_names:
        # 获取等级（取最后一次出现的等级）
        grade = 3
        for snap in snapshots:
            if name in snap["ammo"]:
                grade = snap["ammo"][name]["grade"]

        prices = []
        for snap in snapshots:
            if name in snap["ammo"]:
                prices.append(snap["ammo"][name]["currentPrice"])
            else:
                prices.append(None)  # 该时间点无数据

        series.append({
            "name": name,
            "grade": grade,
            "prices": prices
        })

    result = {
        "timePoints": time_points,
        "series": series
    }
    # 输出到文件避免终端编码问题
    out_path = os.path.join(DATA_DIR, "__history_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print("OK: " + out_path)


if __name__ == "__main__":
    merge_history()
