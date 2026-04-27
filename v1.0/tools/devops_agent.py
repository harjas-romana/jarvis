import subprocess
import platform

TOOL_SCHEMA = {
    "name": "system_diagnostic",
    "description": "Returns real-time hardware diagnostics for this Mac: CPU usage, memory (RAM), disk space, battery status, or network info.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "What to check: 'cpu', 'memory', 'disk', 'battery', or 'network'"
            }
        },
        "required": ["target"]
    }
}

def _run(cmd: list) -> str:
    """Safe subprocess wrapper."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.stdout.strip()

def execute(target: str) -> str:
    """Parses raw macOS system data into clean, human-readable summaries."""
    try:
        target = target.lower().strip()
        
        if target == "cpu":
            raw = _run(["top", "-l", "1", "-n", "0", "-stats", "cpu"])
            for line in raw.split("\n"):
                if "CPU usage" in line:
                    return f"CPU Status: {line.strip()}"
            return "CPU data could not be parsed."
            
        elif target == "memory" or target == "ram":
            # Parse vm_stat into actual GB values
            raw = _run(["vm_stat"])
            page_size = 16384  # macOS default page size (16KB on Apple Silicon, 4KB on Intel)
            
            # Detect actual page size
            ps_raw = _run(["sysctl", "-n", "hw.pagesize"])
            if ps_raw.isdigit():
                page_size = int(ps_raw)
            
            stats = {}
            for line in raw.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().rstrip(".")
                    if val.isdigit():
                        stats[key.strip()] = int(val)
            
            # Calculate real values
            total_raw = _run(["sysctl", "-n", "hw.memsize"])
            total_gb = int(total_raw) / (1024**3) if total_raw.isdigit() else 0
            
            free_pages = stats.get("Pages free", 0) + stats.get("Pages speculative", 0)
            active_pages = stats.get("Pages active", 0)
            wired_pages = stats.get("Pages wired down", 0)
            compressed_pages = stats.get("Pages occupied by compressor", 0)
            
            used_gb = (active_pages + wired_pages + compressed_pages) * page_size / (1024**3)
            free_gb = total_gb - used_gb
            
            return (
                f"Memory: {used_gb:.1f} GB used out of {total_gb:.0f} GB total. "
                f"{free_gb:.1f} GB available. "
                f"(Active: {active_pages * page_size / (1024**3):.1f} GB, "
                f"Wired: {wired_pages * page_size / (1024**3):.1f} GB, "
                f"Compressed: {compressed_pages * page_size / (1024**3):.1f} GB)"
            )
            
        elif target == "disk":
            raw = _run(["df", "-h", "/"])
            lines = raw.split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                # parts: [Filesystem, Size, Used, Avail, Capacity, Mounted]
                if len(parts) >= 5:
                    return f"Disk: {parts[2]} used of {parts[1]} total. {parts[3]} available. {parts[4]} capacity."
            return f"Raw disk output: {raw}"
            
        elif target == "battery":
            raw = _run(["pmset", "-g", "batt"])
            # Extract percentage and charging state
            for line in raw.split("\n"):
                if "%" in line:
                    # Typical: "  -InternalBattery-0 (id=...)  85%; charging; 1:23 remaining"
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        return f"Battery: {parts[1].strip()}"
                    return f"Battery: {line.strip()}"
            return "Battery information unavailable (this may be a desktop Mac)."
            
        elif target == "network":
            # Get WiFi SSID
            ssid_raw = _run([
                "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", 
                "-I"
            ])
            ssid = "Unknown"
            for line in ssid_raw.split("\n"):
                if " SSID:" in line and "BSSID" not in line:
                    ssid = line.split(":")[1].strip()
                    
            # Get IP address
            ip = _run(["ipconfig", "getifaddr", "en0"])
            if not ip:
                ip = _run(["ipconfig", "getifaddr", "en1"])
            if not ip:
                ip = "No active connection"
                
            return f"Network: Connected to '{ssid}'. Local IP: {ip}."
            
        else:
            return f"Unknown diagnostic target: '{target}'. Available: cpu, memory, disk, battery, network."
            
    except subprocess.TimeoutExpired:
        return f"Diagnostic for '{target}' timed out."
    except Exception as e:
        return f"Diagnostic failed: {str(e)}"