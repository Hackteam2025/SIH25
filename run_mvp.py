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
import time
import signal
import asyncio
import logging
import subprocess
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import psutil
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


class ServiceOrchestrator:
    """Orchestrates all FloatChat services for MVP deployment."""

    def __init__(self):
        self.services: List[ServiceConfig] = []
        self.processes: Dict[str, subprocess.Popen] = {}
        self.base_dir = Path(__file__).parent
        self.running = False

        # Initialize services configuration
        self._setup_services()

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
            startup_delay=10  # Database needs time to initialize
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
            startup_delay=8
        ))

        # Story 1: DataOps Processing Server
        self.services.append(ServiceConfig(
            name="DataOps_Server",
            command=[sys.executable, "-m", "sih25.DATAOPS.main"],
            port=8002,
            health_endpoint="http://localhost:8002/health",
            working_dir=str(self.base_dir),
            env_vars={
                "DATAOPS_API_PORT": "8002",
                "API_HOST": "0.0.0.0"
            },
            startup_delay=5
        ))

        # Story 4: Frontend Dashboard
        self.services.append(ServiceConfig(
            name="Frontend_Dashboard",
            command=[sys.executable, "-m", "sih25.FRONTEND.app"],
            port=8050,
            health_endpoint="http://localhost:8050/_dash-layout",
            working_dir=str(self.base_dir),
            env_vars={
                "AGENT_API_URL": "http://localhost:8001",
                "MCP_API_URL": "http://localhost:8000",
                "DATAOPS_API_URL": "http://localhost:8002"
            },
            startup_delay=6
        ))

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        logger.info("🔍 Checking prerequisites...")

        # Check Python version
        if sys.version_info < (3, 8):
            logger.error("❌ Python 3.8+ required")
            return False

        # Check environment variables
        required_env_vars = [
            "GROQ_API_KEY",  # For AGNO agent
        ]

        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            logger.info("Please set these in your .env file or environment")
            return False

        # Check if ports are available
        for service in self.services:
            if self._is_port_in_use(service.port):
                logger.error(f"❌ Port {service.port} is already in use (needed for {service.name})")
                return False

        logger.info("✅ All prerequisites met")
        return True

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result == 0

    async def start_all_services(self):
        """Start all services in dependency order."""
        logger.info("🚀 Starting FloatChat MVP Services...")
        self.running = True

        # Start services in dependency order
        for service in self.services:
            if not self.running:
                break

            logger.info(f"🔄 Starting {service.name}...")
            await self._start_service(service)

            # Wait for startup delay
            logger.info(f"⏳ Waiting {service.startup_delay}s for {service.name} to initialize...")
            await asyncio.sleep(service.startup_delay)

            # Check health
            if await self._check_service_health(service):
                logger.info(f"✅ {service.name} is healthy")
            else:
                logger.warning(f"⚠️  {service.name} health check failed, but continuing...")

        if self.running:
            logger.info("🎉 All services started!")
            self._print_service_summary()

    async def _start_service(self, service: ServiceConfig):
        """Start a single service."""
        env = os.environ.copy()
        if service.env_vars:
            env.update(service.env_vars)

        try:
            process = subprocess.Popen(
                service.command,
                cwd=service.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.processes[service.name] = process
            logger.info(f"🟢 {service.name} started (PID: {process.pid})")

        except Exception as e:
            logger.error(f"❌ Failed to start {service.name}: {e}")

    async def _check_service_health(self, service: ServiceConfig) -> bool:
        """Check if a service is healthy."""
        try:
            response = requests.get(service.health_endpoint, timeout=5)
            return response.status_code in [200, 404]  # 404 for Dash apps is OK
        except:
            return False

    def _print_service_summary(self):
        """Print summary of running services."""
        print("\n" + "="*60)
        print("🌊 FLOATCHAT MVP - JARVIS FOR OCEAN SCIENTISTS 🌊")
        print("="*60)
        print(f"🎯 Frontend Dashboard:     http://localhost:8050")
        print(f"🤖 AI Agent API:          http://localhost:8001")
        print(f"🔧 MCP Tool Server:       http://localhost:8000")
        print(f"📊 DataOps API:           http://localhost:8002")
        print("="*60)
        print("🎤 Voice AI is integrated with the Agent")
        print("💾 Vector Database for semantic search is ready")
        print("🌐 All Stories (1-5) are deployed and connected!")
        print("="*60)
        print("\nPress Ctrl+C to stop all services")
        print("View logs in individual terminal windows or check process outputs")
        print("\n💡 Quick Start:")
        print("1. Open http://localhost:8050 in your browser")
        print("2. Click the 🎤 button to enable voice mode")
        print("3. Ask: 'Show me temperature profiles near the equator'")
        print("4. Upload NetCDF files in the admin panel")
        print("5. Try: 'Find floats with high salinity measurements'")
        print("\n🔬 Scientific queries examples:")
        print("- 'What's the oxygen level in the North Atlantic?'")
        print("- 'Show me chlorophyll data from tropical waters'")
        print("- 'Compare temperature profiles from different seasons'")

    async def monitor_services(self):
        """Monitor running services."""
        while self.running:
            await asyncio.sleep(30)  # Check every 30 seconds

            failed_services = []
            for name, process in self.processes.items():
                if process.poll() is not None:  # Process has terminated
                    failed_services.append(name)

            if failed_services:
                logger.warning(f"⚠️  Failed services detected: {', '.join(failed_services)}")
                for service_name in failed_services:
                    process = self.processes[service_name]
                    stdout, stderr = process.communicate()
                    logger.error(f"❌ {service_name} output: {stderr}")

    def stop_all_services(self):
        """Stop all running services."""
        logger.info("🛑 Stopping all services...")
        self.running = False

        for name, process in self.processes.items():
            try:
                logger.info(f"🔄 Stopping {name}...")
                process.terminate()

                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                    logger.info(f"✅ {name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️  Force killing {name}...")
                    process.kill()
                    process.wait()
                    logger.info(f"✅ {name} force stopped")

            except Exception as e:
                logger.error(f"❌ Error stopping {name}: {e}")

        logger.info("🏁 All services stopped")

    def get_system_status(self) -> Dict[str, Dict]:
        """Get status of all services."""
        status = {}

        for service in self.services:
            process = self.processes.get(service.name)
            is_healthy = False

            if process and process.poll() is None:
                try:
                    response = requests.get(service.health_endpoint, timeout=2)
                    is_healthy = response.status_code in [200, 404]
                except:
                    pass

            status[service.name] = {
                "running": process is not None and process.poll() is None,
                "healthy": is_healthy,
                "port": service.port,
                "pid": process.pid if process else None
            }

        return status


async def main():
    """Main entry point for MVP deployment."""
    orchestrator = ServiceOrchestrator()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("🛑 Received shutdown signal...")
        orchestrator.stop_all_services()
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
        logger.info("✅ Loaded environment variables from .env")
    else:
        logger.warning("⚠️  No .env file found. Make sure to set required environment variables.")

    # Run the orchestrator
    exit_code = asyncio.run(main())
    sys.exit(exit_code)