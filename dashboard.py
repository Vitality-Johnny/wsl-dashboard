#!/usr/bin/env python3
"""🖥️  WSL 终端仪表盘 — 每次开终端自动显示"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
import socket

# 检测代理是否可用
def _check_proxy():
    """检查 127.0.0.1:7890 代理通不通"""
    proxy = os.environ.get('https_proxy', '')
    if '127.0.0.1:7890' in proxy or 'localhost:7890' in proxy:
        try:
            s = socket.create_connection(('127.0.0.1', 7890), timeout=1)
            s.close()
            return True
        except:
            pass
    return False

_USE_PROXY = _check_proxy()
if not _USE_PROXY:
    # 代理不可用时，临时清除环境变量
    os.environ.pop('https_proxy', None)
    os.environ.pop('http_proxy', None)

# ═══════════════════════════════════
#  配置
# ═══════════════════════════════════
TODO_FILE = Path.home() / ".dashboard_todos.json"
WEATHER_CITY = "上海"  # 填写你的城市，留空自动检测
COLOR_ENABLED = True

# ═══════════════════════════════════
#  颜色
# ═══════════════════════════════════
class C:
    if COLOR_ENABLED:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        DIM = '\033[2m'
        RESET = '\033[0m'
    else:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = BOLD = DIM = RESET = ''


# ═══════════════════════════════════
#  系统信息
# ═══════════════════════════════════

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except:
        return "N/A"

def get_system_info():
    info = {}
    info['hostname'] = run("hostname")
    info['user'] = run("whoami")
    
    # OS
    info['os'] = run("grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"'")
    
    # Kernel
    info['kernel'] = run("uname -r")
    
    # Uptime
    uptime_sec = run("cat /proc/uptime 2>/dev/null | cut -d' ' -f1")
    if uptime_sec != "N/A":
        sec = float(uptime_sec)
        days = int(sec // 86400)
        hours = int((sec % 86400) // 3600)
        mins = int((sec % 3600) // 60)
        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        parts.append(f"{mins}m")
        info['uptime'] = ' '.join(parts)
    else:
        info['uptime'] = "N/A"
    
    # CPU 负载
    load = run("cat /proc/loadavg 2>/dev/null | cut -d' ' -f1-3")
    info['load'] = load
    
    # CPU 使用率
    cpu_pct = run(r"top -bn2 2>/dev/null | grep 'Cpu(s)' | tail -1 | awk '{print int($2+$4)}'")
    if cpu_pct == "N/A" or cpu_pct == "0":
        # 备选：从 /proc/stat 算
        import time
        with open('/proc/stat') as f:
            l1 = f.readline().split()
        time.sleep(0.1)
        with open('/proc/stat') as f:
            l2 = f.readline().split()
        idle1, idle2 = int(l1[4]), int(l2[4])
        total1 = sum(int(v) for v in l1[1:])
        total2 = sum(int(v) for v in l2[1:])
        used = (total2 - total1) - (idle2 - idle1)
        total = total2 - total1
        cpu_pct = str(int(used * 100 / total)) if total else "0"
    info['cpu_pct'] = cpu_pct
    
    # 内存
    mem = run("free -h 2>/dev/null | grep Mem | awk '{print $3\"/\"$2}'")
    mem_pct = run("free 2>/dev/null | grep Mem | awk '{printf \"%.0f\", $3/$2*100}'")
    info['mem'] = mem
    info['mem_pct'] = mem_pct
    
    # 磁盘
    disk = run("df -h / 2>/dev/null | tail -1 | awk '{printf \"%s/%s (%s)\\n\", $3, $2, $5}'")
    info['disk'] = disk
    
    # IP
    info['ip'] = run("ip route get 1 2>/dev/null | grep -oP 'src \\K[\\d.]+'")
    if info['ip'] == "N/A" or not info['ip']:
        info['ip'] = run("hostname -I 2>/dev/null | awk '{print $1}'")
    
    # WSL
    info['wsl'] = run(r"grep -i wsl /proc/version 2>/dev/null | head -1 | awk '{print $3}'")
    if info['wsl'] and 'microsoft' in info['wsl'].lower():
        info['wsl'] = "WSL2"
    else:
        info['wsl'] = ""
    
    return info


# ═══════════════════════════════════
#  天气（Open-Meteo，免费无需 API Key）
# ═══════════════════════════════════

def get_weather():
    """通过城市名 + Open-Meteo 获取天气"""
    city = WEATHER_CITY or "上海"
    
    # 常用城市坐标（防止 API 被墙时用）
    CITY_COORDS = {
        "上海": (31.23, 121.47),
        "北京": (39.90, 116.40),
        "广州": (23.13, 113.26),
        "深圳": (22.54, 114.06),
        "杭州": (30.27, 120.15),
        "成都": (30.57, 104.06),
        "武汉": (30.58, 114.27),
        "南京": (32.06, 118.79),
    }
    
    try:
        lat, lon = CITY_COORDS.get(city, (None, None))
        
        if lat is None:
            # 用 Open-Meteo Geocoding API 查坐标
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh"
            req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                geo = json.loads(r.read().decode())
            results = geo.get('results', [])
            if not results:
                return None
            loc = results[0]
            city_name = loc.get('name', city)
            lat = loc['latitude']
            lon = loc['longitude']
        else:
            city_name = city
        
        # Open-Meteo 天气 API（免费）
        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={lat}&longitude={lon}"
               f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
               f"&timezone=auto")
        
        req2 = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=5) as r2:
            data = json.loads(r2.read().decode())
        
        current = data.get('current', {})
        temp = current.get('temperature_2m', '?')
        humidity = current.get('relative_humidity_2m', '?')
        wind = current.get('wind_speed_10m', '?')
        
        # 天气码 → 文字/图标
        code = current.get('weather_code', 0)
        weather_icons = {
            0: '☀️ 晴', 1: '🌤️ 多云', 2: '⛅ 阴', 3: '☁️ 阴',
            45: '🌫️ 雾', 48: '🌫️ 雾',
            51: '🌦️ 小雨', 53: '🌦️ 中雨', 55: '🌧️ 大雨',
            61: '🌧️ 小雨', 63: '🌧️ 中雨', 65: '🌧️ 大雨',
            71: '🌨️ 小雪', 73: '🌨️ 中雪', 75: '❄️ 大雪',
            80: '🌦️ 阵雨', 81: '🌧️ 阵雨', 82: '🌧️ 大阵雨',
            95: '⛈️ 雷雨', 96: '⛈️ 雷雨', 99: '⛈️ 大雷雨',
        }
        weather_str = weather_icons.get(code, f'🌡️ {code}')
        
        return {
            'city': city_name,
            'temp': temp,
            'weather': weather_str,
            'humidity': humidity,
            'wind': wind,
        }
    except Exception as e:
        return None


# ═══════════════════════════════════
#  待办事项
# ═══════════════════════════════════

def load_todos():
    if TODO_FILE.exists():
        try:
            data = json.loads(TODO_FILE.read_text())
            return data.get('todos', [])
        except:
            pass
    return []

def init_todos():
    """首次运行时创建示例待办"""
    if not TODO_FILE.exists():
        todos = [
            "🚀 把这个仪表盘上传 GitHub",
            "🎨 试试 Hermes 皮肤包",
            "📚 今天学点新东西"
        ]
        TODO_FILE.write_text(json.dumps({"todos": todos}, ensure_ascii=False, indent=2))
        return todos
    return load_todos()


# ═══════════════════════════════════
#  渲染
# ═══════════════════════════════════

def bar(pct, width=20):
    """绘制进度条 ████████░░"""
    if pct == "N/A":
        return "?" * width
    try:
        p = float(pct.rstrip('%'))
    except:
        return "?" * width
    filled = int(p / 100 * width)
    empty = width - filled
    return f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * empty}{C.RESET}"

def section(title):
    return f"{C.CYAN}┃{C.RESET}  {C.BOLD}{title}{C.RESET}"

def kv(key, val):
    return f"{C.CYAN}┃{C.RESET}  {C.DIM}{key}:{C.RESET} {val}"

def render(info, weather, todos):
    lines = []
    W = 60  # 宽度
    
    sep_top = f"{C.CYAN}╔{'═' * (W-2)}╗{C.RESET}"
    sep_mid = f"{C.CYAN}┃{'─' * (W-2)}┃{C.RESET}"
    sep_bot = f"{C.CYAN}╚{'═' * (W-2)}╝{C.RESET}"
    empty = f"{C.CYAN}┃{C.RESET}{' ' * (W-2)}{C.CYAN}┃{C.RESET}"
    
    def line(text=""):
        text = text[:W-4]
        return f"{C.CYAN}┃{C.RESET} {text}{' ' * (W - 4 - len(text))} {C.CYAN}┃{C.RESET}"
    
    lines.append("")
    lines.append(sep_top)
    
    # 标题
    title_text = f"🖥️  {info['user']}@{info['hostname']}"
    if info['wsl']:
        title_text += f"  ({info['wsl']})"
    lines.append(line(f"{C.BOLD}{title_text}{C.RESET}"))
    lines.append(sep_mid)
    
    # 系统信息
    lines.append(section("系统信息"))
    
    os_display = info['os']
    if info['kernel'] != "N/A":
        os_display += f"  ({C.DIM}{info['kernel']}{C.RESET})"
    lines.append(kv("系统", os_display))
    lines.append(kv("运行时间", info['uptime']))
    
    # CPU
    if info['cpu_pct'] != "N/A":
        lines.append(kv("CPU", f"{bar(info['cpu_pct'])}  {info['cpu_pct']}%"))
    else:
        lines.append(kv("负载", info['load']))
    
    # 内存
    if info['mem'] != "N/A":
        lines.append(kv("内存", f"{bar(info['mem_pct'])}  {info['mem']}"))
    
    # 磁盘
    lines.append(kv("磁盘", info['disk']))
    
    # IP
    if info['ip'] and info['ip'] != "N/A":
        lines.append(kv("IP", info['ip']))
    
    lines.append(sep_mid)
    
    # 天气
    if weather:
        lines.append(section("🌤️  天气"))
        lines.append(kv(weather['city'], f"{weather['temp']}°C  {weather['weather']}  湿度{weather['humidity']}%  风速{weather['wind']}km/h"))
        lines.append(sep_mid)
    
    # 待办
    lines.append(section(f"📋 待办 ({len(todos)}项)"))
    if todos:
        for i, t in enumerate(todos, 1):
            lines.append(kv(f"  {i}", t))
    else:
        lines.append(kv("", f"{C.DIM}暂无待办，编辑 ~/.dashboard_todos.json{C.RESET}"))
    
    lines.append(sep_bot)
    lines.append("")
    
    return '\n'.join(lines)


# ═══════════════════════════════════
#  入口
# ═══════════════════════════════════

def main():
    import time
    start = time.time()
    
    info = get_system_info()
    weather = get_weather()
    todos = init_todos()
    dashboard = render(info, weather, todos)
    
    elapsed = time.time() - start
    print(dashboard, flush=True)
    # 调试：显示加载耗时
    # print(f"{C.DIM}Loaded in {elapsed:.2f}s{C.RESET}")

if __name__ == '__main__':
    main()
