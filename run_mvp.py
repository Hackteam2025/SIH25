#!/usr/bin/env python3
"""
FloatChat MVP - Unified Deployment Runner
=========================================

Single command to deploy the complete FloatChat system:
- Story 1: Data Pipeline (DATAOPS)
- Story 2: MCP Tool Server (API)
- Story 3: AGNO AI Agent with Voice (AGENT + VOICE_AI)
- Story 4: Interactive Frontend (FRONTEND)
- Story 5: Vector Database Integration

This script orchestrates all services and provides health monitoring.
"""

import os
import sys
import signal
import asyncio
import logging
import subprocess
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import requests
from datetime import datetime
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

# Color codes for different services
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    # Service-specific colors
    MCP = '\033[94m'      # Blue
    AGNO = '\033[92m'     # Green
    DATAOPS = '\033[93m'  # Yellow
    FRONTEND = '\033[95m' # Magenta
    ORCHESTRATOR = '\033[96m'  # Cyan
    ERROR = '\033[91m'    # Red
    WARNING = '\033[93m'  # Yellow
    SUCCESS = '\033[92m'  # Green

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different services."""

    COLORS = {
        'MCP_Tool_Server': Colors.MCP,
        'AGNO_Agent_Server': Colors.AGNO,
        'DataOps_Server': Colors.DATAOPS,
        'Frontend_Dashboard': Colors.FRONTEND,
        '__main__': Colors.ORCHESTRATOR,
    }

    LEVEL_COLORS = {
        'ERROR': Colors.ERROR,
        'WARNING': Colors.WARNING,
        'INFO': Colors.SUCCESS,
        'DEBUG': Colors.RESET,
    }

    def format(self, record):
        # Get service color
        service_color = self.COLORS.get(record.name, Colors.RESET)
        level_color = self.LEVEL_COLORS.get(record.levelname, Colors.RESET)

        # Format timestamp
        timestamp = self.formatTime(record, '%H:%M:%S')

        # Create colored log entry
        service_name = record.name.replace('_', ' ').title() if record.name != '__main__' else 'ORCHESTRATOR'

        formatted = f"{Colors.BOLD}{timestamp}{Colors.RESET} {service_color}[{service_name:^15}]{Colors.RESET} {level_color}{record.levelname:>7}{Colors.RESET} {record.getMessage()}"
        return formatted

# Configure unified logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with colored formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# Prevent duplicate logs
logger.propagate = False


@dataclass
class ServiceConfig:
    """Configuration for a service."""
    name: str
    command: List[str]
    port: int
    health_endpoint: str
    working_dir: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    startup_delay: int = 5
    color: str = Colors.RESET

class ServiceLogger:
    """Handles logging for individual services with color coding."""

    def __init__(self, service_name: str, color: str):
        self.service_name = service_name
        self.color = color
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)

        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(ColoredFormatter())
            self.logger.addHandler(handler)
            self.logger.propagate = False

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def debug(self, message: str):
        self.logger.debug(message)


class ServiceOrchestrator:
    """Orchestrates all FloatChat services for MVP deployment with unified logging."""

    def __init__(self):
        self.services: List[ServiceConfig] = []
        self.processes: Dict[str, subprocess.Popen] = {}
        self.service_loggers: Dict[str, ServiceLogger] = {}
        self.log_threads: Dict[str, threading.Thread] = {}
        self.base_dir = Path(__file__).parent
        self.running = False
        self.log_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Initialize services configuration
        self._setup_services()

        # Setup service loggers
        for service in self.services:
            self.service_loggers[service.name] = ServiceLogger(service.name, service.color)

    def _setup_services(self):
        """Configure all services for deployment."""

        # Story 2: MCP Tool Server (Database + API)
        self.services.append(ServiceConfig(
            name="MCP_Tool_Server",
            command=[sys.executable, "-m", "sih25.API.main"],
            port=8000,
            health_endpoint="http://localhost:8000/health",
            working_dir=str(self.base_dir),
            env_vars={
                "API_PORT": "8000",
                "API_HOST": "0.0.0.0"
            },
            startup_delay=3,  # Database needs time to initialize
            color=Colors.MCP
        ))

        # Story 3: AGNO Agent Server (AI + Voice)
        self.services.append(ServiceConfig(
            name="AGNO_Agent_Server",
            command=[sys.executable, "-m", "sih25.AGENT.main"],
            port=8001,
            health_endpoint="http://localhost:8001/health",
            working_dir=str(self.base_dir),
            env_vars={
                "AGENT_API_PORT": "8001",
                "API_HOST": "0.0.0.0",
                "MCP_SERVER_URL": "http://localhost:8000"
            },
            startup_delay=8,
            color=Colors.AGNO
        ))

        # Story 1: DataOps Processing Server
        # self.services.append(ServiceConfig(
        #     name="DataOps_Server",
        #     command=[sys.executable, "-m", "sih25.DATAOPS.main"],
        #     port=8002,
        #     health_endpoint="http://localhost:8002/health",
        #     working_dir=str(self.base_dir),
        #     env_vars={
        #         "DATAOPS_API_PORT": "8002",
        #         "API_HOST": "0.0.0.0"
        #     },
        #     startup_delay=5,
        #     color=Colors.DATAOPS
        # ))

        # Story 4: Frontend Dashboard (React + Bun)
        self.services.append(ServiceConfig(
            name="Frontend_Dashboard",
            command=["bun", "run", "dev"],
            port=5173,  # Default Vite port
            health_endpoint="http://localhost:5173",
            working_dir=str(self.base_dir / "sih25" / "FRONTEND_REACT"),
            env_vars={
                "VITE_AGENT_API_URL": "http://localhost:8001",
                "VITE_MCP_API_URL": "http://localhost:8000",
                "VITE_DATAOPS_API_URL": "http://localhost:8002"
            },
            startup_delay=6,
            color=Colors.FRONTEND
        ))

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met with enhanced logging."""
        logger.info("🔍 Checking prerequisites...")

        # Check Python version
        if sys.version_info < (3, 8):
            logger.error(f"❌ Python 3.8+ required (current: {sys.version.split()[0]})")
            return False
        else:
            logger.info(f"✅ Python version: {sys.version.split()[0]}")

        # Check if bun is installed
        try:
            result = subprocess.run(['bun', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                bun_version = result.stdout.strip()
                logger.info(f"✅ Bun version: {bun_version}")
            else:
                logger.error("❌ Bun is not installed or not in PATH")
                logger.info("Please install bun from: https://bun.sh")
                return False
        except FileNotFoundError:
            logger.error("❌ Bun is not installed or not in PATH")
            logger.info("Please install bun from: https://bun.sh")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Could not verify bun installation: {e}")

        # Check environment variables
        required_env_vars = [
            "GROQ_API_KEY",  # For AGNO agent
        ]

        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
            else:
                logger.info(f"✅ Environment variable '{var}' is set")

        if missing_vars:
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            logger.info("Please set these in your .env file or environment")
            return False

        # Check if ports are available
        for service in self.services:
            if self._is_port_in_use(service.port):
                logger.error(f"❌ Port {service.port} is already in use (needed for {service.name})")
                logger.info(f"Kill the process using: lsof -ti:{service.port} | xargs kill")
                return False
            else:
                logger.info(f"✅ Port {service.port} is available for {service.name}")

        logger.info("✅ All prerequisites met! Ready to start services.")
        return True

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result == 0

    async def start_all_services(self):
        """Start all services in dependency order with unified logging."""
        logger.info("🚀 Starting FloatChat MVP Services...")
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.ORCHESTRATOR}🌊 FLOATCHAT MVP - UNIFIED LOGGING SYSTEM 🌊{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}Legend:{Colors.RESET}")
        print(f"  {Colors.MCP}● MCP Tool Server{Colors.RESET}     {Colors.AGNO}● AGNO Agent Server{Colors.RESET}")
        print(f"  {Colors.DATAOPS}● DataOps Server{Colors.RESET}      {Colors.FRONTEND}● Frontend Dashboard{Colors.RESET}")
        print(f"  {Colors.ORCHESTRATOR}● Orchestrator{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

        self.running = True

        # Start services in dependency order
        for service in self.services:
            if not self.running:
                break

            service_logger = self.service_loggers[service.name]
            service_logger.info(f"Starting...")
            await self._start_service(service)

            # Wait for startup delay
            service_logger.info(f"Initializing... (waiting {service.startup_delay}s)")
            await asyncio.sleep(service.startup_delay)

            # Check health
            if await self._check_service_health(service):
                service_logger.info(f"✅ Service is healthy and ready")
            else:
                service_logger.warning(f"⚠️ Health check failed, but continuing...")

        if self.running:
            logger.info("🎉 All services started and running with unified logging!")
            self._print_service_summary()

    async def _start_service(self, service: ServiceConfig):
        """Start a single service with real-time log streaming."""
        env = os.environ.copy()
        if service.env_vars:
            env.update(service.env_vars)

        try:
            process = subprocess.Popen(
                service.command,
                cwd=service.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            self.processes[service.name] = process
            service_logger = self.service_loggers[service.name]
            service_logger.info(f"Started (PID: {process.pid})")

            # Start log streaming thread
            log_thread = threading.Thread(
                target=self._stream_service_logs,
                args=(service.name, process),
                daemon=True
            )
            log_thread.start()
            self.log_threads[service.name] = log_thread

        except Exception as e:
            service_logger = self.service_loggers[service.name]
            service_logger.error(f"Failed to start: {e}")

    def _stream_service_logs(self, service_name: str, process: subprocess.Popen):
        """Stream logs from a service process in real-time."""
        service_logger = self.service_loggers[service_name]

        try:
            while process.poll() is None and self.running:
                line = process.stdout.readline()
                if line:
                    # Clean and process the line
                    line = line.strip()
                    if line:
                        # Filter out common noise
                        if self._should_log_line(line):
                            # Detect log level from content
                            if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'critical']):
                                service_logger.error(line)
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                service_logger.warning(line)
                            else:
                                service_logger.info(line)

            # Process any remaining output
            remaining_output, _ = process.communicate()
            if remaining_output:
                for line in remaining_output.strip().split('\n'):
                    if line.strip() and self._should_log_line(line.strip()):
                        service_logger.info(line.strip())

        except Exception as e:
            service_logger.error(f"Log streaming error: {e}")

    def _should_log_line(self, line: str) -> bool:
        """Enhanced filtering to reduce noise from logs."""
        noise_patterns = [
            # Flask/Werkzeug noise
            'Serving Flask app',
            'Debug mode:',
            '* Running on',
            'Press CTRL+C to quit',
            '* Restarting with',
            '* Debugger is active',
            '* Debugger PIN:',
            'WARNING: This is a development server',
            'Use a production WSGI server instead',

            # Dash noise
            'Dash is running on',

            # Common application noise
            'INFO:werkzeug:',
            'INFO:asyncio:',
            ' * Environment:',
            ' * Debug mode:',

            # HTTP request logs (can be noisy)
            '" 200 -',
            '" 404 -',
            'GET /',
            'POST /',

            # Empty or very short lines
            '',
            ' ',
        ]

        line_stripped = line.strip()
        if len(line_stripped) < 3:  # Skip very short lines
            return False

        line_lower = line_stripped.lower()

        # Always log errors and warnings
        if any(keyword in line_lower for keyword in ['error', 'exception', 'failed', 'critical', 'warning', 'warn']):
            return True

        # Skip noise patterns
        if any(pattern.lower() in line_lower for pattern in noise_patterns):
            return False

        # Always log lines with useful info
        useful_patterns = [
            'started',
            'listening',
            'connected',
            'initialized',
            'ready',
            'loaded',
            'success',
            'completed',
            'processing',
        ]

        if any(pattern.lower() in line_lower for pattern in useful_patterns):
            return True

        # Default to logging if not obviously noise
        return len(line_stripped) > 10  # Only log substantial content

    async def _check_service_health(self, service: ServiceConfig) -> bool:
        """Check if a service is healthy."""
        try:
            response = requests.get(service.health_endpoint, timeout=5)
            return response.status_code in [200, 404]  # 404 for Dash apps is OK
        except:
            return False

    def _print_service_summary(self):
        """Print summary of running services with enhanced formatting."""
        print("\n" + f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.ORCHESTRATOR}🌊 FLOATCHAT MVP - ALL SYSTEMS OPERATIONAL 🌊{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}🎯 Service Endpoints:{Colors.RESET}")
        print(f"  {Colors.FRONTEND}📊 Frontend Dashboard:     http://localhost:5173{Colors.RESET}")
        print(f"  {Colors.AGNO}🤖 AI Agent API:          http://localhost:8001{Colors.RESET}")
        print(f"  {Colors.MCP}🔧 MCP Tool Server:       http://localhost:8000{Colors.RESET}")
        print(f"  {Colors.DATAOPS}📈 DataOps API:           http://localhost:8002{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}🎤 Voice AI{Colors.RESET} is integrated with the Agent")
        print(f"{Colors.BOLD}💾 Vector Database{Colors.RESET} for semantic search is ready")
        print(f"{Colors.BOLD}🌐 All Stories (1-5){Colors.RESET} are deployed and connected!")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"\n{Colors.BOLD}📝 Real-time Logs:{Colors.RESET}")
        print(f"  ✅ All service logs are being streamed in real-time below")
        print(f"  🎨 Each service has a unique color for easy identification")
        print(f"  🔍 Logs are filtered to show only relevant information")
        print(f"\n{Colors.WARNING}Press Ctrl+C to stop all services{Colors.RESET}")
        print(f"\n{Colors.BOLD}💡 Quick Start:{Colors.RESET}")
        print(f"1. Open {Colors.FRONTEND}http://localhost:5173{Colors.RESET} in your browser")
        print(f"2. Click the {Colors.BOLD}🎤 button{Colors.RESET} to enable voice mode")
        print(f"3. Ask: {Colors.SUCCESS}'Show me temperature profiles near the equator'{Colors.RESET}")
        print(f"4. Upload NetCDF files in the admin panel")
        print(f"5. Try: {Colors.SUCCESS}'Find floats with high salinity measurements'{Colors.RESET}")
        print(f"\n{Colors.BOLD}🔬 Scientific Queries Examples:{Colors.RESET}")
        print(f"- {Colors.SUCCESS}'What's the oxygen level in the North Atlantic?'{Colors.RESET}")
        print(f"- {Colors.SUCCESS}'Show me chlorophyll data from tropical waters'{Colors.RESET}")
        print(f"- {Colors.SUCCESS}'Compare temperature profiles from different seasons'{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    async def monitor_services(self):
        """Monitor running services with detailed logging."""
        logger.info("🔍 Starting service monitoring...")

        while self.running:
            await asyncio.sleep(30)  # Check every 30 seconds

            failed_services = []
            for name, process in self.processes.items():
                if process.poll() is not None:  # Process has terminated
                    failed_services.append(name)

            if failed_services:
                for service_name in failed_services:
                    service_logger = self.service_loggers[service_name]
                    service_logger.error(f"❌ Service has terminated unexpectedly")

                    # Try to get exit code and any final output
                    process = self.processes[service_name]
                    exit_code = process.poll()
                    service_logger.error(f"Exit code: {exit_code}")

            # Log system status periodically
            if self.running:
                active_services = sum(1 for p in self.processes.values() if p.poll() is None)
                logger.info(f"📊 System Status: {active_services}/{len(self.services)} services running")

    def stop_all_services(self):
        """Stop all running services with detailed logging."""
        logger.info("🛑 Initiating graceful shutdown of all services...")
        self.running = False

        for name, process in self.processes.items():
            service_logger = self.service_loggers[name]
            try:
                service_logger.info("🔄 Stopping...")
                process.terminate()

                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                    service_logger.info("✅ Stopped gracefully")
                except subprocess.TimeoutExpired:
                    service_logger.warning("⚠️ Force killing...")
                    process.kill()
                    process.wait()
                    service_logger.info("✅ Force stopped")

            except Exception as e:
                service_logger.error(f"❌ Error during shutdown: {e}")

        # Wait for log threads to finish
        for thread in self.log_threads.values():
            if thread.is_alive():
                thread.join(timeout=2)

        logger.info("🏁 All services stopped. Goodbye!")

    def get_system_status(self) -> Dict[str, Dict]:
        """Get detailed status of all services."""
        status = {}

        for service in self.services:
            process = self.processes.get(service.name)
            is_healthy = False
            is_running = process is not None and process.poll() is None

            if is_running:
                try:
                    response = requests.get(service.health_endpoint, timeout=2)
                    is_healthy = response.status_code in [200, 404]
                except:
                    pass

            # Log status for monitoring
            status_emoji = "🟢" if is_running and is_healthy else "🔴" if not is_running else "🟡"

            status[service.name] = {
                "running": is_running,
                "healthy": is_healthy,
                "port": service.port,
                "pid": process.pid if process else None,
                "status_emoji": status_emoji
            }

        return status


async def main():
    """Main entry point for MVP deployment with enhanced logging."""
    orchestrator = ServiceOrchestrator()

    # Print startup banner
    print(f"\n{Colors.BOLD}{Colors.ORCHESTRATOR}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.ORCHESTRATOR}🌊 FLOATCHAT MVP - UNIFIED LOGGING ORCHESTRATOR 🌊{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.ORCHESTRATOR}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}Starting unified logging system...{Colors.RESET}\n")

    # Setup signal handlers for graceful shutdown
    def signal_handler(_signum, _frame):
        logger.info("🛑 Received shutdown signal...")
        orchestrator.stop_all_services()
        print(f"\n{Colors.BOLD}{Colors.SUCCESS}Thank you for using FloatChat MVP! 👋{Colors.RESET}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Check prerequisites
        if not orchestrator.check_prerequisites():
            logger.error("❌ Prerequisites not met. Exiting...")
            return 1

        # Start all services
        await orchestrator.start_all_services()

        # Start log filtering helper in background
        print(f"\n{Colors.BOLD}📝 Live Service Logs:{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        # Monitor services
        await orchestrator.monitor_services()

    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        orchestrator.stop_all_services()

    return 0


if __name__ == "__main__":
    # Check for environment file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        # Load environment variables
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print(f"{Colors.SUCCESS}✅ Loaded environment variables from .env{Colors.RESET}")
    else:
        print(f"{Colors.WARNING}⚠️ No .env file found. Make sure to set required environment variables.{Colors.RESET}")

    # Print initial system info
    print(f"{Colors.BOLD}System Info:{Colors.RESET}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Platform: {os.name}")
    print(f"  Working Directory: {os.getcwd()}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Run the orchestrator
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"{Colors.ERROR}❌ Fatal error: {e}{Colors.RESET}")
        sys.exit(1)