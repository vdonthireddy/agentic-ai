"""System information and host diagnostic tools for MCP Server."""

import os
import platform
import psutil
from typing import Dict, Any

def get_system_metrics() -> Dict[str, Any]:
    """
    Retrieves current operating system, CPU, memory, and disk utilization metrics.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        return {
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            },
            "cpu": {
                "usage_percent": cpu_percent,
                "logical_cores": cpu_count_logical,
                "physical_cores": cpu_count_physical
            },
            "memory": {
                "total_gb": round(vm.total / (1024**3), 2),
                "available_gb": round(vm.available / (1024**3), 2),
                "used_gb": round(vm.used / (1024**3), 2),
                "percent_used": vm.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            }
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve system metrics: {str(e)}"
        }
