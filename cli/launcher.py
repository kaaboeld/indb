"""
INDB Multi-Protocol Launcher with Rich Terminal UI

Unified launcher for all INDB protocols with beautiful console output:
- HTTP/REST API (FastAPI) on port 8000
- UDP Protocol on port 8001
- WebSocket (via FastAPI) on port 8000/ws

Usage:
    python cli/launcher.py              # Start all protocols
    python cli/launcher.py --http-only  # HTTP only
    python cli/launcher.py --udp-only   # UDP only
"""

import asyncio
import signal
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from multiprocessing import Process
import time

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.live import Live
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import after path setup
from core.config_schema import get_config
from core.indb import INDB
from core.kernel import INDBKernel
from auth.manager import AuthManager
from storage.migration_manager import MigrationManager

console = Console() if RICH_AVAILABLE else None
config = get_config()


class MultiProtocolLauncher:
    """Launch and manage all INDB protocols with rich UI"""
    
    def __init__(self):
        self.processes = []
        self.kernel = None
        self.auth_manager = None
        self.db = None
        self.shutdown_event = asyncio.Event()
    
    def print_banner(self):
        """Print beautiful startup banner."""
        if RICH_AVAILABLE:
            banner = Text()
            banner.append("╔═══════════════════════════════════════════════════════════╗\n", style="cyan")
            banner.append("║                                                           ║\n", style="cyan")
            banner.append("║   ", style="cyan")
            banner.append("🚀 INDB Multi-Protocol Server", style="bold magenta")
            banner.append("                    ║\n", style="cyan")
            banner.append("║   ", style="cyan")
            banner.append("Interpretative Neural Database v2.0", style="dim")
            banner.append("              ║\n", style="cyan")
            banner.append("║                                                           ║\n", style="cyan")
            banner.append("╚═══════════════════════════════════════════════════════════╝", style="cyan")
            
            console.print(banner)
        else:
            print("\n" + "="*60)
            print("🚀 INDB Multi-Protocol Server")
            print("   Interpretative Neural Database v2.0")
            print("="*60)
    
    def initialize_core(self):
        """Initialize INDB core components with progress."""
        self.print_banner()
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                # Migrations
                task1 = progress.add_task("[cyan]Running database migrations...", total=None)
                migration_manager = MigrationManager()
                temp_db = INDB()
                migration_success = migration_manager.run_migrations(temp_db)
                progress.update(task1, completed=True)
                
                if not migration_success:
                    console.print("[red]❌ Migration failed[/red]")
                    sys.exit(1)
                
                self.db = temp_db
                console.print("[green]✅ Database initialized[/green]")
                
                # Kernel
                task2 = progress.add_task("[cyan]Initializing kernel...", total=None)
                self.kernel = INDBKernel()
                self.kernel.initialize(self.db)
                progress.update(task2, completed=True)
                console.print("[green]✅ Kernel initialized[/green]")
                
                # Auth
                task3 = progress.add_task("[cyan]Initializing auth manager...", total=None)
                self.auth_manager = AuthManager()
                progress.update(task3, completed=True)
                console.print("[green]✅ Auth manager initialized[/green]")
        else:
            print("\n📦 Initializing core components...")
            
            migration_manager = MigrationManager()
            temp_db = INDB()
            migration_success = migration_manager.run_migrations(temp_db)
            
            if not migration_success:
                print("❌ Migration failed")
                sys.exit(1)
            
            self.db = temp_db
            print("✅ Database initialized")
            
            self.kernel = INDBKernel()
            self.kernel.initialize(self.db)
            print("✅ Kernel initialized")
            
            self.auth_manager = AuthManager()
            print("✅ Auth manager initialized")
    
    def show_endpoints_table(self):
        """Show endpoints in a beautiful table."""
        if RICH_AVAILABLE:
            table = Table(
                title="📍 Active Endpoints",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            
            table.add_column("Protocol", style="cyan", no_wrap=True)
            table.add_column("Endpoint", style="green")
            table.add_column("Status", justify="center")
            
            table.add_row(
                "HTTP API",
                f"http://localhost:{config.server_port}",
                "[green]●[/green] Running"
            )
            table.add_row(
                "Swagger UI",
                f"http://localhost:{config.server_port}/docs",
                "[green]●[/green] Running"
            )
            table.add_row(
                "WebSocket",
                f"ws://localhost:{config.server_port}/ws",
                "[green]●[/green] Running"
            )
            
            if config.udp_enabled:
                table.add_row(
                    "UDP",
                    f"udp://localhost:{config.udp_port}",
                    "[green]●[/green] Running"
                )
            
            console.print(table)
            
            console.print(Panel(
                "[yellow]💡 Press Ctrl+C to stop all servers[/yellow]",
                border_style="yellow"
            ))
        else:
            print("\n" + "="*60)
            print("🎉 All servers running!")
            print("="*60)
            print(f"\n📍 Endpoints:")
            print(f"   HTTP API:    http://localhost:{config.server_port}")
            print(f"   Swagger UI:  http://localhost:{config.server_port}/docs")
            print(f"   WebSocket:   ws://localhost:{config.server_port}/ws")
            if config.udp_enabled:
                print(f"   UDP:         udp://localhost:{config.udp_port}")
            print(f"\n💡 Press Ctrl+C to stop all servers")
            print("="*60 + "\n")
    
    def start_http_server(self):
        """Start HTTP/WebSocket server (FastAPI)."""
        if RICH_AVAILABLE:
            console.print(f"\n[cyan]🌐 Starting HTTP/WebSocket server on port {config.server_port}...[/cyan]")
        else:
            print(f"\n🌐 Starting HTTP/WebSocket server on port {config.server_port}...")
        
        # Import here to avoid circular imports
        import main
        
        uvicorn.run(
            "main:app",
            host=config.server_host,
            port=config.server_port,
            log_level="info",
            access_log=True
        )
    
    def start_udp_server(self):
        """Start UDP server."""
        if RICH_AVAILABLE:
            console.print(f"\n[cyan]📡 Starting UDP server on port {config.udp_port}...[/cyan]")
        else:
            print(f"\n📡 Starting UDP server on port {config.udp_port}...")
        
        from protocols.udp_server import run_udp_server
        
        # Create new event loop for this process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize components for this process
        migration_manager = MigrationManager()
        temp_db = INDB()
        migration_manager.run_migrations(temp_db)
        
        kernel = INDBKernel()
        kernel.initialize(temp_db)
        auth_manager = AuthManager()
        
        # Run UDP server
        loop.run_until_complete(run_udp_server(kernel, auth_manager))
    
    def start_all(self):
        """Start all protocol servers."""
        self.initialize_core()
        
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]🚀 Starting all protocol servers...[/bold cyan]\n")
        else:
            print("\n🚀 Starting all protocol servers...\n")
        
        # Start UDP server in separate process if enabled
        if config.udp_enabled:
            udp_process = Process(target=self.start_udp_server, name="UDP-Server")
            udp_process.start()
            self.processes.append(udp_process)
            
            if RICH_AVAILABLE:
                console.print(f"[green]✅ UDP server started (PID: {udp_process.pid})[/green]")
            else:
                print(f"✅ UDP server started (PID: {udp_process.pid})")
            
            time.sleep(2)  # Give UDP time to start
        
        # Show endpoints
        self.show_endpoints_table()
        
        # Start HTTP/WebSocket server (blocking, runs in main process)
        try:
            self.start_http_server()
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown of all servers."""
        print("\n")
        
        if RICH_AVAILABLE:
            console.print(Panel(
                "[bold red]🛑 Shutting down all servers...[/bold red]",
                border_style="red"
            ))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                for process in self.processes:
                    if process.is_alive():
                        task = progress.add_task(
                            f"[yellow]Stopping {process.name} (PID: {process.pid})...[/yellow]",
                            total=None
                        )
                        process.terminate()
                        process.join(timeout=5)
                        
                        if process.is_alive():
                            progress.update(task, description=f"[red]Force killing {process.name}...[/red]")
                            process.kill()
                            process.join()
                        
                        progress.update(task, completed=True)
            
            console.print("[green]✅ All servers stopped[/green]")
        else:
            print("="*60)
            print("🛑 Shutting down all servers...")
            print("="*60)
            
            for process in self.processes:
                if process.is_alive():
                    print(f"   Stopping {process.name} (PID: {process.pid})...")
                    process.terminate()
                    process.join(timeout=5)
                    
                    if process.is_alive():
                        print(f"   Force killing {process.name}...")
                        process.kill()
                        process.join()
            
            print("✅ All servers stopped")
            print("="*60 + "\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="INDB Multi-Protocol Server")
    parser.add_argument("--http-only", action="store_true", help="Start HTTP/WebSocket only")
    parser.add_argument("--udp-only", action="store_true", help="Start UDP only")
    args = parser.parse_args()
    
    launcher = MultiProtocolLauncher()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        launcher.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.http_only:
        launcher.initialize_core()
        if RICH_AVAILABLE:
            console.print("\n[cyan]🌐 Starting HTTP/WebSocket server only...[/cyan]\n")
        else:
            print("\n🌐 Starting HTTP/WebSocket server only...\n")
        launcher.start_http_server()
    elif args.udp_only:
        launcher.initialize_core()
        if RICH_AVAILABLE:
            console.print("\n[cyan]📡 Starting UDP server only...[/cyan]\n")
        else:
            print("\n📡 Starting UDP server only...\n")
        launcher.start_udp_server()
    else:
        launcher.start_all()


if __name__ == "__main__":
    main()
