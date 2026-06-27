"""macOS 监控命令模块

磁盘用量、电池健康、传感器温度。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
  ⚠️ 警告信息
"""

import re
import subprocess


# ── 工具函数 ─────────────────────────────────────────────

def _run_cmd(cmd: list[str], timeout: int = 15) -> str:
    """执行外部命令并返回 stdout 去除尾随空格。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return ""
        return r.stdout.strip()
    except Exception:
        return ""


def _run_cmd_stderr(cmd: list[str], timeout: int = 15) -> tuple[str, str, int]:
    """执行外部命令，返回 (stdout, stderr, returncode)。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except FileNotFoundError:
        return "", "命令未找到", -1
    except subprocess.TimeoutExpired:
        return "", "执行超时", -1
    except Exception as e:
        return "", str(e), -1


# ── 磁盘监控 ─────────────────────────────────────────────

def cmd_disk_monitor(params: dict) -> str:
    """检查磁盘用量。params: {"path": "/", "warn_percent": 90}"""
    path = params.get("path", "/")
    warn_percent = int(params.get("warn_percent", 90))
    stdout, stderr, rc = _run_cmd_stderr(["df", "-H", path])
    if rc != 0 or not stdout:
        return f"❌ 无法读取磁盘信息: {stderr or '无输出'}"

    lines = stdout.splitlines()
    if len(lines) < 2:
        return "❌ 磁盘信息格式异常"

    # Filesystem      Size  Used  Avail  Use%  Mounted on
    parts = lines[1].split()
    if len(parts) < 5:
        return "❌ 无法解析磁盘信息"

    size = parts[1]
    used = parts[2]
    avail = parts[3]
    use_percent_str = parts[4].rstrip("%")

    try:
        use_percent = int(use_percent_str)
    except ValueError:
        use_percent = 0

    lines_out = [
        f"📀 磁盘监控 — {path}",
        f"   总大小: {size}",
        f"   已用:   {used}",
        f"   可用:   {avail}",
        f"   使用率: {use_percent}%",
    ]

    if use_percent > warn_percent:
        lines_out.append(f"   ⚠️  警告：磁盘使用率 {use_percent}% 超过阈值 {warn_percent}%")

    return "\n".join(lines_out)


# ── 电池健康 ─────────────────────────────────────────────

def cmd_battery_health(params: dict) -> str:
    """查看电池健康信息：循环次数、状态、最大容量"""

    # 方案一: system_profiler SPPowerDataType
    stdout = _run_cmd(["system_profiler", "SPPowerDataType", "-detailLevel", "mini"])
    if stdout:
        result = _parse_system_profiler_battery(stdout)
        if result:
            return result

    # 方案二: pmset -g batt + ioreg (回退)
    return _battery_fallback()


def _parse_system_profiler_battery(text: str) -> str | None:
    """从 system_profiler 输出中解析电池信息。"""
    cycle = "N/A"
    condition = "N/A"
    max_cap = "N/A"
    state_of_charge = "N/A"

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("Cycle Count"):
            cycle = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Condition"):
            condition = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Maximum Capacity"):
            max_cap = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("State of Charge"):
            # e.g. "State of Charge (%): 100"
            _, _, val = stripped.partition(":")
            state_of_charge = val.strip() + "%"

    if cycle == "N/A" and condition == "N/A":
        return None

    lines_out = [
        "🔋 电池健康",
        f"   循环计数: {cycle}",
        f"   状态:     {condition}",
    ]
    if max_cap != "N/A":
        lines_out.append(f"   最大容量: {max_cap}")
    if state_of_charge != "N/A":
        lines_out.append(f"   当前电量: {state_of_charge}")

    return "\n".join(lines_out)


def _battery_fallback() -> str:
    """使用 pmset + ioreg 作为回退方案获取电池信息。"""
    lines_out = ["🔋 电池健康"]

    # pmset -g batt 获取充放电状态和百分比
    stdout_batt = _run_cmd(["pmset", "-g", "batt"])
    if stdout_batt:
        # 例: "Now drawing from 'Battery Power' -InternalBattery-0 (id=...)... 78%; discharging;"
        for line in stdout_batt.splitlines():
            if "-InternalBattery" in line or "InternalBattery" in line:
                # 提取百分比
                m = re.search(r"(\d+)%", line)
                if m:
                    lines_out.append(f"   电量: {m.group(1)}%")
                # 提取状态
                m = re.search(r";\s*([\w\s]+);", line)
                if m:
                    lines_out.append(f"   状态: {m.group(1).strip()}")

    # ioreg 获取更详细的电池信息
    stdout_ioreg = _run_cmd(
        ["ioreg", "-br", "-c", "AppleSmartBattery"],
        timeout=10,
    )
    if stdout_ioreg:
        cycle = _ioreg_value(stdout_ioreg, "CycleCount")
        if cycle:
            lines_out.append(f"   循环计数: {cycle}")

        max_cap = _ioreg_value(stdout_ioreg, "AppleRawMaxCapacity")
        design_cap = _ioreg_value(stdout_ioreg, "DesignCapacity")
        if max_cap and design_cap:
            health_pct = round(int(max_cap) / int(design_cap) * 100)
            lines_out.append(f"   最大容量: {max_cap} / {design_cap} mAh ({health_pct}%)")

        condition = _ioreg_value(stdout_ioreg, "HealthCondition")
        if condition:
            lines_out.append(f"   电池状态: {condition}")
        else:
            # 检查是否建议维修
            is_charging = _ioreg_value(stdout_ioreg, "IsCharging")
            if is_charging:
                lines_out.append(f"   电池状态: 正常")

    if len(lines_out) == 1:
        return "❌ 无法获取电池信息"

    return "\n".join(lines_out)


def _ioreg_value(text: str, key: str) -> str | None:
    """从 ioreg 输出中提取指定 key 的值。"""
    m = re.search(rf'"{key}"\s*=\s*([^\s]+)', text)
    if m:
        return m.group(1).strip()
    return None


# ── 传感器温度 ─────────────────────────────────────────────

def cmd_sensor_temp(params: dict) -> str:
    """查看传感器温度。params: {"sensor": "cpu"}"""
    sensor = params.get("sensor", "cpu")
    if sensor.lower() not in ("cpu",):
        return f"❌ 不支持的传感器: {sensor}"

    # 方案一: osx-cpu-temp
    stdout, stderr, rc = _run_cmd_stderr(["osx-cpu-temp"], timeout=10)
    if rc == 0 and stdout:
        # 输出示例: "63.5°C"
        return f"🌡️  CPU 温度: {stdout.strip()}"

    # 方案二: sysctl (M1/M2 无法使用)
    stdout = _run_cmd(["/usr/sbin/sysctl", "-n", "machdep.xcpm.cpu_thermal_level"])
    if stdout:
        raw = stdout.strip()
        try:
            level = int(raw)
            # machdep.xcpm.cpu_thermal_level 返回 0~127 左右的整数（非直接摄氏度）
            temp_c = round(level / 128 * 100, 1)
            return f"🌡️  CPU 温度（估算）: {temp_c}°C (raw: {level})"
        except ValueError:
            return f"🌡️  CPU 热级别: {raw}"
    stdout = _run_cmd(["/usr/sbin/sysctl", "-n", "machdep.xcpm.cpu_temp"])
    if stdout:
        raw = stdout.strip()
        try:
            # 单位可能是摄氏度的 100 倍
            temp_c = round(int(raw) / 100, 1)
            return f"🌡️  CPU 温度: {temp_c}°C"
        except ValueError:
            return f"🌡️  CPU 温度 (raw): {raw}°C"

    # 方案三: istats (需要安装)
    stdout, stderr, rc = _run_cmd_stderr(["istats"], timeout=10)
    if rc == 0 and stdout:
        for line in stdout.splitlines():
            if "CPU" in line or "cpu" in line:
                # 提取温度数值
                m = re.search(r"(\d+[.,]\d+)", line)
                if m:
                    return f"🌡️  CPU 温度: {m.group(1).replace(',', '.')}°C"
        # 如果没找到 CPU 行，返回全部输出
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        return "🌡️  istats 输出:\n" + "\n".join(lines[:10])

    # 方案四: powermetrics (需要 sudo)
    stdout, stderr, rc = _run_cmd_stderr(
        ["/usr/bin/powermetrics", "-n", "1", "-s", "cpu_power", "--show-process-power", "--samplers", "tasks"],
        timeout=15,
    )
    if rc == 0 and stdout:
        for line in stdout.splitlines():
            if "die temperature" in line.lower() or "cpu die" in line.lower():
                m = re.search(r"(\d+[.,]\d+)", line)
                if m:
                    return f"🌡️  CPU 温度: {m.group(1).replace(',', '.')}°C"

    # 方案五: pmset thermal 状态（Apple Silicon 可用，无 sudo）
    try:
        stdout = _run_cmd(["/usr/bin/pmset", "-g", "therm"])
        if stdout:
            for line in stdout.splitlines():
                if "thermal" in line.lower() or "pressure" in line.lower() or "cpu" in line.lower():
                    return f"🌡️  散热状态: {line.strip()}"
            # 显示全部
            lines = [l.strip() for l in stdout.splitlines() if l.strip()]
            if lines:
                return f"🌡️  散热信息:\n" + "\n".join(lines[:5])
    except Exception:
        pass

    # 方案六: os_log 散热警报
    try:
        # 用 ioreg 读取 Apple Silicon 的散热传感器
        stdout = _run_cmd(["/usr/sbin/ioreg", "-r", "-c", "AppleARMIODevice", "-l"])
        if stdout:
            for line in stdout.splitlines():
                if "temperature" in line.lower() or "temp" in line.lower():
                    m = re.search(r'["\"]?(\d+[.,]\d+)["\"]?', line)
                    if m:
                        return f"🌡️  传感器: {line.strip()[:80]}"
    except Exception:
        pass

    return "❌ 无法获取 CPU 温度（尝试: brew install osx-cpu-temp）"


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "disk_monitor": cmd_disk_monitor,
    "battery_health": cmd_battery_health,
    "sensor_temp": cmd_sensor_temp,
}

TOOL_SCHEMAS: dict = {
    "disk_monitor": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "挂载点路径，默认为 /",
                "default": "/",
            },
            "warn_percent": {
                "type": "integer",
                "description": "告警阈值百分比，默认为 90",
                "default": 90,
            },
        },
    },
    "battery_health": {
        "type": "object",
        "properties": {},
    },
    "sensor_temp": {
        "type": "object",
        "properties": {
            "sensor": {
                "type": "string",
                "description": "传感器类型，默认为 cpu",
                "default": "cpu",
            },
        },
    },
}
