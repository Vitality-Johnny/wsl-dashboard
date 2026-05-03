# 🖥️ WSL Dashboard

每次打开终端自动显示的仪表盘——系统信息、天气、待办。

## 功能

- 系统信息：OS、运行时间、CPU、内存、磁盘、IP
- 🌤️ 天气：自动获取上海（可配置）实时天气
- 📋 待办：编辑 `~/.dashboard_todos.json` 即可

## 安装

```bash
# 1. 放到 PATH 里
cp dashboard.py ~/.local/bin/dashboard
chmod +x ~/.local/bin/dashboard

# 2. 加到 .bashrc 自动启
echo '[[ "$TERM" != "dumb" ]] && command -v dashboard && dashboard' >> ~/.bashrc

# 3. 编辑你的待办
echo '{"todos": ["写代码", "运动", "早睡"]}' > ~/.dashboard_todos.json
```

## 配置

编辑 `~/.dashboard_todos.json`：
```json
{"todos": ["任务1", "任务2", "任务3"]}
```

天气城市改脚本里的 `WEATHER_CITY = "上海"` 为你所在城市。

## 依赖

- Python 3（WSL 自带）
- 无需安装任何包
- 天气来源：Open-Meteo（免费无 key）
