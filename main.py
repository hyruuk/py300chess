#!/usr/bin/env python3
"""
py300chess - Main System Orchestrator

This is the primary entry point for the py300chess system. It manages the 
lifecycle of all components and provides different operating modes for 
development, testing, and actual gameplay.
"""

import sys
import os
import time
import signal
import argparse
import logging
import threading
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional
import atexit

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import project components
from config.config_loader import get_config, reload_config
from src.eeg_processing.signal_simulator import SimulatedEEGStreamer
from src.eeg_processing.lsl_stream import RealEEGStreamer
from src.eeg_processing.p300_detector import P300Detector

# Import chess components (will be implemented soon)
try:
    from src.chess_game.chess_engine import ChessEngine
    CHESS_ENGINE_AVAILABLE = True
except ImportError:
    CHESS_ENGINE_AVAILABLE = False

try:
    from src.gui.p300_interface import P300ChessGUI
    CHESS_GUI_AVAILABLE = True
except ImportError:
    CHESS_GUI_AVAILABLE = False


class SystemOrchestrator:
    """
    Main system orchestrator for py300chess.
    
    Manages component lifecycle, monitors system health, and provides
    clean startup/shutdown procedures. Can spawn components in separate
    terminals for easy monitoring.
    """
    
    def __init__(self, config, use_separate_terminals: bool = False):
        """Initialize the system orchestrator."""
        self.config = config
        self.use_separate_terminals = use_separate_terminals
        self.logger = logging.getLogger(__name__)
        
        # Component instances (for in-process mode)
        self.eeg_streamer = None
        self.p300_detector = None
        self.chess_engine = None
        self.chess_gui = None
        
        # Component processes (for separate terminal mode)
        self.component_processes = {}
        self.terminal_processes = {}
        
        # System state
        self.is_running = False
        self.startup_complete = False
        self.components_started = []
        
        # Statistics
        self.start_time = None
        self.component_status = {}
        
        # Shutdown handling
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup)
    
    def start_system(self, mode: str = "full"):
        """
        Start the py300chess system in specified mode.
        
        Args:
            mode: System operating mode
                - "full": Complete BCI chess system
                - "eeg_only": EEG streaming and P300 detection only
                - "simulation": Simulated EEG pipeline testing
                - "hardware": Real EEG hardware testing
                - "chess_only": Chess game without BCI (future)
        """
        if self.is_running:
            self.logger.warning("System already running")
            return False
        
        self.logger.info(f"🚀 Starting py300chess system in '{mode}' mode...")
        self.start_time = time.time()
        
        try:
            # Validate configuration
            self._validate_configuration()
            
            # Start components based on mode
            if mode == "full":
                success = self._start_full_system()
            elif mode == "eeg_only":
                success = self._start_eeg_pipeline()
            elif mode == "simulation":
                success = self._start_simulation_mode()
            elif mode == "hardware":
                success = self._start_hardware_mode()
            elif mode == "chess_only":
                success = self._start_chess_only()
            else:
                raise ValueError(f"Unknown mode: {mode}")
            
            if success:
                self.is_running = True
                self.startup_complete = True
                self._log_system_status()
                self.logger.info("✅ py300chess system startup complete!")
                return True
            else:
                self.logger.error("❌ System startup failed")
                self.shutdown()
                return False
        
        except Exception as e:
            self.logger.error(f"💥 System startup error: {e}")
            import traceback
            traceback.print_exc()
            self.shutdown()
            return False
    
    def _start_full_system(self) -> bool:
        """Start complete BCI chess system."""
        self.logger.info("Starting complete BCI chess system...")
        
        # 1. Start EEG source
        if not self._start_eeg_source():
            return False
        
        # 2. Start P300 detection
        if not self._start_p300_detector():
            return False
        
        # 3. Start chess engine
        if not self._start_chess_engine():
            return False
        
        # 4. Start chess GUI
        if not self._start_chess_gui():
            return False
        
        self.logger.info("🎮 Full BCI chess system ready!")
        return True
    
    def _start_eeg_pipeline(self) -> bool:
        """Start EEG streaming and P300 detection only."""
        self.logger.info("Starting EEG processing pipeline...")
        
        # 1. Start EEG source
        if not self._start_eeg_source():
            return False
        
        # 2. Start P300 detection
        if not self._start_p300_detector():
            return False
        
        self.logger.info("🧠 EEG pipeline ready!")
        return True
    
    def _start_simulation_mode(self) -> bool:
        """Start with simulated EEG for testing."""
        self.logger.info("Starting simulation mode...")
        
        # Force simulation mode
        self.config.eeg.use_simulation = True
        
        # Start EEG pipeline
        return self._start_eeg_pipeline()
    
    def _start_hardware_mode(self) -> bool:
        """Start with real EEG hardware."""
        self.logger.info("Starting hardware mode...")
        
        # Force hardware mode
        self.config.eeg.use_simulation = False
        
        # Start EEG pipeline
        return self._start_eeg_pipeline()
    
    def _start_chess_only(self) -> bool:
        """Start chess game without BCI (future implementation)."""
        self.logger.info("Starting chess-only mode...")
        
        # 1. Start chess engine
        if not self._start_chess_engine():
            return False
        
        # 2. Start chess GUI
        if not self._start_chess_gui():
            return False
        
        self.logger.info("♟️ Chess game ready!")
        return True
    
    def _start_eeg_source(self) -> bool:
        """Start appropriate EEG source (simulated or real)."""
        try:
            if self.use_separate_terminals:
                return self._start_eeg_source_in_terminal()
            else:
                return self._start_eeg_source_in_process()
        except Exception as e:
            self.logger.error(f"❌ Failed to start EEG source: {e}")
            return False
    
    def _start_eeg_source_in_terminal(self) -> bool:
        """Start EEG source in separate terminal."""
        if self.config.eeg.use_simulation:
            self.logger.info("🧠 Starting simulated EEG streamer in new terminal...")
            script_path = project_root / "src" / "eeg_processing" / "signal_simulator.py"
            terminal_title = "py300chess - EEG Simulator"
            
            # Build command with configuration
            cmd_args = [str(script_path)]
            if self.config.feedback.debug_mode:
                cmd_args.append("--verbose")
            
            process = self._spawn_terminal(cmd_args, terminal_title, "eeg_simulator")
            if process:
                self.component_processes["eeg_simulator"] = process
                self.components_started.append("eeg_simulator")
                self.component_status["eeg_source"] = "simulated (terminal)"
            else:
                return False
        else:
            self.logger.info("🔌 Starting real EEG streamer in new terminal...")
            script_path = project_root / "src" / "eeg_processing" / "lsl_stream.py"
            terminal_title = "py300chess - Real EEG"
            
            process = self._spawn_terminal([str(script_path)], terminal_title, "eeg_hardware")
            if process:
                self.component_processes["eeg_hardware"] = process
                self.components_started.append("eeg_hardware")
                self.component_status["eeg_source"] = "hardware (terminal)"
            else:
                return False
        
        # Give EEG source time to initialize
        self.logger.info("⏳ Waiting for EEG source to initialize...")
        time.sleep(3.0)
        
        # Verify LSL streams are available
        if not self._wait_for_lsl_stream("SimulatedEEG" if self.config.eeg.use_simulation else "ProcessedEEG"):
            self.logger.error("❌ EEG stream not available after startup")
            return False
        
        self.logger.info("✅ EEG source started successfully")
        return True
    
    def _start_eeg_source_in_process(self) -> bool:
        """Start EEG source in same process (original method)."""
        if self.config.eeg.use_simulation:
            self.logger.info("🧠 Starting simulated EEG streamer...")
            self.eeg_streamer = SimulatedEEGStreamer(self.config)
            self.eeg_streamer.start()
            self.components_started.append("eeg_simulator")
            self.component_status["eeg_source"] = "simulated"
        else:
            self.logger.info("🔌 Starting real EEG streamer...")
            self.eeg_streamer = RealEEGStreamer(self.config)
            self.eeg_streamer.start()
            self.components_started.append("eeg_hardware")
            self.component_status["eeg_source"] = "hardware"
        
        # Give EEG source time to initialize
        time.sleep(2.0)
        
        # Verify EEG source is working
        if hasattr(self.eeg_streamer, 'get_status'):
            status = self.eeg_streamer.get_status()
            if not status.get('is_running', False):
                raise RuntimeError("EEG source failed to start")
        
        self.logger.info("✅ EEG source started successfully")
        return True
    
    def _start_p300_detector(self) -> bool:
        """Start P300 detection component."""
        try:
            if self.use_separate_terminals:
                return self._start_p300_detector_in_terminal()
            else:
                return self._start_p300_detector_in_process()
        except Exception as e:
            self.logger.error(f"❌ Failed to start P300 detector: {e}")
            return False
    
    def _start_p300_detector_in_terminal(self) -> bool:
        """Start P300 detector in separate terminal."""
        self.logger.info("🧠 Starting P300 detector in new terminal...")
        script_path = project_root / "src" / "eeg_processing" / "p300_detector.py"
        terminal_title = "py300chess - P300 Detector"
        
        process = self._spawn_terminal([str(script_path)], terminal_title, "p300_detector")
        if process:
            self.component_processes["p300_detector"] = process
            self.components_started.append("p300_detector")
            self.component_status["p300_detector"] = "running (terminal)"
        else:
            return False
        
        # Give detector time to connect to streams
        self.logger.info("⏳ Waiting for P300 detector to connect...")
        time.sleep(2.0)
        
        # Verify P300Detection stream is available
        if not self._wait_for_lsl_stream("P300Detection"):
            self.logger.error("❌ P300Detection stream not available after startup")
            return False
        
        self.logger.info("✅ P300 detector started successfully")
        return True
    
    def _start_p300_detector_in_process(self) -> bool:
        """Start P300 detector in same process (original method)."""
        self.logger.info("🧠 Starting P300 detector...")
        self.p300_detector = P300Detector(self.config)
        self.p300_detector.start()
        self.components_started.append("p300_detector")
        self.component_status["p300_detector"] = "running"
        
        # Give detector time to connect to streams
        time.sleep(1.0)
        
        # Verify detector is working
        status = self.p300_detector.get_status()
        if not status.get('is_running', False):
            raise RuntimeError("P300 detector failed to start")
        
        self.logger.info("✅ P300 detector started successfully")
        return True
    
    def _start_chess_engine(self) -> bool:
        """Start chess engine component."""
        if not CHESS_ENGINE_AVAILABLE:
            self.logger.warning("⚠️ Chess engine not yet implemented")
            self.component_status["chess_engine"] = "not_available"
            return True  # Don't fail if chess engine isn't ready yet
        
        try:
            if self.use_separate_terminals:
                return self._start_chess_engine_in_terminal()
            else:
                return self._start_chess_engine_in_process()
        except Exception as e:
            self.logger.error(f"❌ Failed to start chess engine: {e}")
            return False
    
    def _start_chess_engine_in_terminal(self) -> bool:
        """Start chess engine in separate terminal."""
        self.logger.info("♟️ Starting chess engine in new terminal...")
        script_path = project_root / "src" / "chess_game" / "chess_engine.py"
        terminal_title = "py300chess - Chess Engine"
        
        process = self._spawn_terminal([str(script_path)], terminal_title, "chess_engine")
        if process:
            self.component_processes["chess_engine"] = process
            self.components_started.append("chess_engine")
            self.component_status["chess_engine"] = "running (terminal)"
        else:
            return False
        
        self.logger.info("✅ Chess engine started successfully")
        return True
    
    def _start_chess_engine_in_process(self) -> bool:
        """Start chess engine in same process (original method)."""
        self.logger.info("♟️ Starting chess engine...")
        self.chess_engine = ChessEngine(self.config)
        self.chess_engine.start()
        self.components_started.append("chess_engine")
        self.component_status["chess_engine"] = "running"
        
        self.logger.info("✅ Chess engine started successfully")
        return True
    
    def _start_chess_gui(self) -> bool:
        """Start chess GUI component."""
        if not CHESS_GUI_AVAILABLE:
            self.logger.warning("⚠️ Chess GUI not yet implemented")
            self.component_status["chess_gui"] = "not_available"
            return True  # Don't fail if GUI isn't ready yet
        
        try:
            if self.use_separate_terminals:
                return self._start_chess_gui_in_terminal()
            else:
                return self._start_chess_gui_in_process()
        except Exception as e:
            self.logger.error(f"❌ Failed to start chess GUI: {e}")
            return False
    
    def _start_chess_gui_in_terminal(self) -> bool:
        """Start chess GUI in separate terminal."""
        self.logger.info("🖥️ Starting chess GUI in new terminal...")
        script_path = project_root / "src" / "gui" / "p300_interface.py"
        terminal_title = "py300chess - Chess GUI"
        
        process = self._spawn_terminal([str(script_path)], terminal_title, "chess_gui")
        if process:
            self.component_processes["chess_gui"] = process
            self.components_started.append("chess_gui")
            self.component_status["chess_gui"] = "running (terminal)"
        else:
            return False
        
        self.logger.info("✅ Chess GUI started successfully")
        return True
    
    def _start_chess_gui_in_process(self) -> bool:
        """Start chess GUI in same process (original method)."""
        self.logger.info("🖥️ Starting chess GUI...")
        self.chess_gui = P300ChessGUI(self.config)
        self.chess_gui.start()
        self.components_started.append("chess_gui")
        self.component_status["chess_gui"] = "running"
        
        self.logger.info("✅ Chess GUI started successfully")
        return True
    
    def _spawn_terminal(self, command_args: List[str], title: str, component_name: str) -> Optional[subprocess.Popen]:
        """
        Spawn a new terminal window with the given command.
        
        Args:
            command_args: Command and arguments to run
            title: Terminal window title
            component_name: Component identifier for tracking
            
        Returns:
            Process handle or None if failed
        """
        try:
            system = platform.system().lower()
            python_executable = sys.executable
            
            # Build the python command
            python_cmd = [python_executable] + command_args
            
            if system == "windows":
                # Windows - use cmd with start
                cmd = ["cmd", "/c", "start", f'"{title}"', "cmd", "/k"] + python_cmd
                
            elif system == "darwin":  # macOS
                # macOS - use osascript to open Terminal
                script = f'''
                tell application "Terminal"
                    do script "{' '.join([python_executable] + command_args)}"
                    set custom title of front window to "{title}"
                    activate
                end tell
                '''
                cmd = ["osascript", "-e", script]
                
            else:  # Linux and other Unix-like systems
                # Try different terminal emulators in order of preference
                terminals = [
                    # GNOME Terminal
                    ["gnome-terminal", "--title", title, "--", python_executable] + command_args,
                    # Konsole (KDE)
                    ["konsole", "--title", title, "-e", python_executable] + command_args,
                    # xterm (fallback)
                    ["xterm", "-title", title, "-e", python_executable] + command_args,
                    # Alacritty
                    ["alacritty", "--title", title, "-e", python_executable] + command_args,
                    # Terminator
                    ["terminator", "--title", title, "-e", f"{python_executable} {' '.join(command_args)}"],
                ]
                
                cmd = None
                for terminal_cmd in terminals:
                    try:
                        # Check if terminal is available
                        subprocess.run([terminal_cmd[0], "--version"], 
                                     capture_output=True, timeout=2)
                        cmd = terminal_cmd
                        break
                    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                        continue
                
                if cmd is None:
                    self.logger.error(f"❌ No suitable terminal found for {component_name}")
                    return None
            
            # Start the process
            if system == "darwin":
                # For macOS, we need to handle the osascript differently
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                process = subprocess.Popen(cmd, 
                                         stdout=subprocess.DEVNULL, 
                                         stderr=subprocess.DEVNULL,
                                         stdin=subprocess.DEVNULL)
            
            self.terminal_processes[component_name] = process
            self.logger.info(f"✅ Spawned {component_name} in new terminal: {title}")
            return process
            
        except Exception as e:
            self.logger.error(f"❌ Failed to spawn terminal for {component_name}: {e}")
            return None
    
    def _wait_for_lsl_stream(self, stream_name: str, timeout: float = 10.0) -> bool:
        """
        Wait for an LSL stream to become available.
        
        Args:
            stream_name: Name of the LSL stream to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if stream is found, False if timeout
        """
        import pylsl as lsl
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                streams = lsl.resolve_streams()
                for stream in streams:
                    if stream.name() == stream_name:
                        self.logger.debug(f"Found LSL stream: {stream_name}")
                        return True
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                self.logger.warning(f"Error checking for LSL stream {stream_name}: {e}")
                time.sleep(1.0)
        
        self.logger.warning(f"Timeout waiting for LSL stream: {stream_name}")
        return False
    
    def _validate_configuration(self):
        """Validate system configuration before startup."""
        self.logger.info("🔧 Validating configuration...")
        
        # Basic configuration validation happens in config loader
        # Add any additional runtime validation here
        
        if self.config.eeg.sampling_rate <= 0:
            raise ValueError("Invalid EEG sampling rate")
        
        if self.config.p300.min_confidence < 0 or self.config.p300.min_confidence > 1:
            raise ValueError("P300 confidence must be between 0 and 1")
        
        self.logger.info("✅ Configuration validated")
    
    def shutdown(self):
        """Gracefully shutdown all system components."""
        if self.shutdown_requested:
            return
        
        self.shutdown_requested = True
        self.logger.info("🛑 Shutting down py300chess system...")
        
        if self.use_separate_terminals:
            # Terminate spawned processes
            for component_name, process in self.component_processes.items():
                try:
                    self.logger.info(f"Stopping {component_name} (PID: {process.pid})...")
                    process.terminate()
                    
                    # Give process time to shut down gracefully
                    try:
                        process.wait(timeout=5.0)
                        self.logger.info(f"✅ {component_name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"⚠️ {component_name} didn't stop gracefully, forcing...")
                        process.kill()
                        process.wait()
                        self.logger.info(f"✅ {component_name} stopped (forced)")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error stopping {component_name}: {e}")
            
            # Clean up terminal processes
            for component_name, process in self.terminal_processes.items():
                try:
                    if process.poll() is None:  # Still running
                        process.terminate()
                        process.wait(timeout=2.0)
                except:
                    pass
        
        else:
            # Stop components in reverse order (original method)
            components_to_stop = [
                ("chess_gui", self.chess_gui),
                ("chess_engine", self.chess_engine),
                ("p300_detector", self.p300_detector),
                ("eeg_streamer", self.eeg_streamer)
            ]
            
            for component_name, component in components_to_stop:
                if component is not None:
                    try:
                        self.logger.info(f"Stopping {component_name}...")
                        component.stop()
                        self.logger.info(f"✅ {component_name} stopped")
                    except Exception as e:
                        self.logger.error(f"❌ Error stopping {component_name}: {e}")
        
        self.is_running = False
        
        # Show session summary
        if self.start_time:
            runtime = time.time() - self.start_time
            self.logger.info(f"📊 Session duration: {runtime:.1f} seconds")
            self.logger.info(f"📊 Components started: {', '.join(self.components_started)}")
            if self.use_separate_terminals:
                self.logger.info(f"📊 Terminal mode: {len(self.component_processes)} separate terminals")
        
        self.logger.info("✅ py300chess system shutdown complete")
    
    def run_interactive(self):
        """Run system with interactive status monitoring."""
        if not self.is_running:
            self.logger.error("System not running")
            return
        
        mode_msg = "Multi-Terminal Debug Mode" if self.use_separate_terminals else "Single Terminal Mode"
        
        self.logger.info("\n" + "="*60)
        self.logger.info(f"🎮 py300chess Interactive Mode ({mode_msg})")
        self.logger.info("="*60)
        self.logger.info("Commands:")
        self.logger.info("  'status' - Show system status")
        self.logger.info("  'config' - Show configuration")
        self.logger.info("  'test' - Run system tests")
        self.logger.info("  'reload' - Reload configuration")
        self.logger.info("  'quit' - Shutdown system")
        if self.use_separate_terminals:
            self.logger.info("  Note: Check separate terminals for component logs")
        self.logger.info("="*60)
        
        try:
            while self.is_running and not self.shutdown_requested:
                try:
                    # Simple command input - no automatic status updates
                    command = input("\npy300chess> ").strip().lower()
                    
                    if command == "quit" or command == "exit":
                        break
                    elif command == "status":
                        self._show_detailed_status()
                    elif command == "config":
                        self._show_configuration()
                    elif command == "test":
                        self._run_system_tests()
                    elif command == "reload":
                        self._reload_configuration()
                    elif command == "help":
                        self._show_help()
                    elif command:
                        self.logger.info(f"Unknown command: {command}")
                
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                except Exception as e:
                    self.logger.error(f"Command error: {e}")
        
        except Exception as e:
            self.logger.error(f"Interactive mode error: {e}")
        
        finally:
            self.shutdown()
    
    def run_headless(self, duration: Optional[float] = None):
        """Run system in headless mode with periodic status updates."""
        if not self.is_running:
            self.logger.error("System not running")
            return
        
        if self.use_separate_terminals:
            self.logger.info("🤖 Running in headless mode with multi-terminal debugging...")
        else:
            self.logger.info("🤖 Running in headless mode...")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            start_time = time.time()
            
            while self.is_running and not self.shutdown_requested:
                # Only show periodic status in debug mode
                if self.use_separate_terminals and time.time() - start_time >= 30:
                    self._show_status_update()
                    start_time = time.time()
                
                # Check duration limit
                if duration and time.time() - self.start_time >= duration:
                    self.logger.info(f"Duration limit reached ({duration}s)")
                    break
                
                time.sleep(1.0)
        
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Headless mode error: {e}")
        finally:
            self.shutdown()
    
    def _show_status_update(self):
        """Show brief system status update."""
        runtime = time.time() - self.start_time if self.start_time else 0
        
        status_parts = []
        for component, status in self.component_status.items():
            if status == "running":
                status_parts.append(f"{component}:✅")
            elif status == "not_available":
                status_parts.append(f"{component}:⚠️")
            else:
                status_parts.append(f"{component}:{status}")
        
        self.logger.info(f"📊 Runtime: {runtime:.1f}s | {' | '.join(status_parts)}")
    
    def _show_detailed_status(self):
        """Show detailed system status."""
        self.logger.info("\n" + "="*50)
        self.logger.info("📊 SYSTEM STATUS")
        self.logger.info("="*50)
        
        runtime = time.time() - self.start_time if self.start_time else 0
        self.logger.info(f"Runtime: {runtime:.1f} seconds")
        self.logger.info(f"Components: {len(self.components_started)} started")
        
        # Component details
        for component_name, component in [
            ("EEG Source", self.eeg_streamer),
            ("P300 Detector", self.p300_detector),
            ("Chess Engine", self.chess_engine),
            ("Chess GUI", self.chess_gui)
        ]:
            if self.use_separate_terminals:
                # Show process status for terminal mode
                comp_key = component_name.lower().replace(' ', '_')
                if 'eeg_source' in comp_key:
                    comp_key = comp_key.replace('eeg_source', 'eeg_simulator')
                
                if comp_key in self.component_processes:
                    process = self.component_processes[comp_key]
                    status = "running" if process.poll() is None else "stopped"
                    self.logger.info(f"\n{component_name} (Terminal):")
                    self.logger.info(f"  PID: {process.pid}")
                    self.logger.info(f"  Status: {status}")
                else:
                    status = self.component_status.get(comp_key, 'not_started')
                    self.logger.info(f"\n{component_name}: {status}")
            else:
                # Original in-process status checking
                if component and hasattr(component, 'get_status'):
                    try:
                        status = component.get_status()
                        self.logger.info(f"\n{component_name}:")
                        for key, value in status.items():
                            self.logger.info(f"  {key}: {value}")
                    except Exception as e:
                        self.logger.error(f"  Error getting {component_name} status: {e}")
                else:
                    status = self.component_status.get(component_name.lower().replace(' ', '_'), 'not_started')
                    self.logger.info(f"\n{component_name}: {status}")
        
        # Show LSL streams
        try:
            import pylsl
            streams = pylsl.resolve_streams()
            if streams:
                self.logger.info(f"\nLSL Streams ({len(streams)} active):")
                for stream in streams:
                    self.logger.info(f"  - {stream.name()} ({stream.type()})")
        except Exception as e:
            self.logger.warning(f"Could not check LSL streams: {e}")
        
        # Show terminal mode info
        if self.use_separate_terminals:
            self.logger.info(f"\nTerminal Mode: {len(self.component_processes)} separate terminals")
            for comp_name, process in self.component_processes.items():
                status = "running" if process.poll() is None else "stopped"
                self.logger.info(f"  {comp_name}: PID {process.pid} ({status})")
        
        if component and hasattr(component, 'get_status'):
            try:
                status = component.get_status()
                self.logger.info(f"\n{component_name}:")
                for key, value in status.items():
                    self.logger.info(f"  {key}: {value}")
            except Exception as e:
                self.logger.error(f"  Error getting {component_name} status: {e}")
        else:
            status = self.component_status.get(component_name.lower().replace(' ', '_'), 'not_started')
            self.logger.info(f"\n{component_name}: {status}")
        
        self.logger.info("="*50)
    
    def _show_configuration(self):
        """Show current configuration."""
        self.logger.info("\n" + "="*50)
        self.logger.info("🔧 CONFIGURATION")
        self.logger.info("="*50)
        self.logger.info(f"EEG Mode: {'Simulation' if self.config.eeg.use_simulation else 'Hardware'}")
        self.logger.info(f"Sample Rate: {self.config.eeg.sampling_rate} Hz")
        self.logger.info(f"Channels: {self.config.eeg.n_channels}")
        self.logger.info(f"P300 Threshold: {self.config.p300.detection_threshold} μV")
        self.logger.info(f"Min Confidence: {self.config.p300.min_confidence}")
        self.logger.info(f"Flash Duration: {self.config.stimulus.flash_duration} ms")
        self.logger.info("="*50)
    
    def _run_system_tests(self):
        """Run basic system tests."""
        self.logger.info("🧪 Running system tests...")
        
        # Test LSL streams availability
        try:
            import pylsl
            streams = pylsl.resolve_streams()
            expected_streams = []
            
            if self.config.eeg.use_simulation:
                expected_streams.extend(["SimulatedEEG", "ChessTarget", "ChessFlash"])
            else:
                expected_streams.append("ProcessedEEG")
            
            if "p300_detector" in self.components_started:
                expected_streams.append("P300Detection")
            
            found_streams = [s.name() for s in streams]
            self.logger.info(f"Expected streams: {expected_streams}")
            self.logger.info(f"Found streams: {found_streams}")
            
            for stream_name in expected_streams:
                if stream_name in found_streams:
                    self.logger.info(f"✅ {stream_name} stream available")
                else:
                    self.logger.warning(f"⚠️ {stream_name} stream missing")
        
        except Exception as e:
            self.logger.error(f"❌ LSL stream test failed: {e}")
        
        # Test P300 pipeline if available
        if self.use_separate_terminals and "p300_detector" in self.component_processes:
            self.logger.info("🧠 Testing P300 detection pipeline...")
            self._test_p300_pipeline()
        
        # Test component processes if in terminal mode
        if self.use_separate_terminals:
            self.logger.info("🖥️ Testing component processes...")
            for comp_name, process in self.component_processes.items():
                if process.poll() is None:
                    self.logger.info(f"✅ {comp_name} process running (PID: {process.pid})")
                else:
                    self.logger.warning(f"⚠️ {comp_name} process stopped")
        
        self.logger.info("✅ System tests complete")
    
    def _test_p300_pipeline(self):
        """Test the P300 detection pipeline with manual commands."""
        try:
            import pylsl
            
            # Test target setting
            self.logger.info("Testing target setting...")
            target_info = pylsl.StreamInfo('TestChessTarget', 'Markers', 1, pylsl.IRREGULAR_RATE, pylsl.cf_string)
            target_outlet = pylsl.StreamOutlet(target_info)
            target_outlet.push_sample(['set_target|square=e4'])
            time.sleep(0.5)
            
            # Test flash command  
            self.logger.info("Testing flash command...")
            flash_info = pylsl.StreamInfo('TestChessFlash', 'Markers', 1, pylsl.IRREGULAR_RATE, pylsl.cf_string)
            flash_outlet = pylsl.StreamOutlet(flash_info)
            flash_outlet.push_sample(['square_flash|square=e4'])
            
            self.logger.info("✅ P300 pipeline test commands sent")
            self.logger.info("Check P300 detector terminal for responses...")
            
        except Exception as e:
            self.logger.error(f"❌ P300 pipeline test failed: {e}")
    
    def _reload_configuration(self):
        """Reload configuration from file."""
        try:
            self.logger.info("🔄 Reloading configuration...")
            self.config = reload_config()
            self.logger.info("✅ Configuration reloaded")
        except Exception as e:
            self.logger.error(f"❌ Failed to reload configuration: {e}")
    
    def _show_help(self):
        """Show help information."""
        self.logger.info("\n" + "="*50)
        self.logger.info("🆘 HELP")
        self.logger.info("="*50)
        self.logger.info("Available commands:")
        self.logger.info("  status  - Show detailed system status")
        self.logger.info("  config  - Show current configuration")
        self.logger.info("  test    - Run system diagnostics")
        self.logger.info("  reload  - Reload configuration file")
        self.logger.info("  help    - Show this help")
        self.logger.info("  quit    - Shutdown system")
        self.logger.info("="*50)
    
    def _log_system_status(self):
        """Log initial system status after startup."""
        mode_info = " (Multi-Terminal Debug Mode)" if self.use_separate_terminals else " (Single Terminal Mode)"
        
        self.logger.info("\n" + "="*60)
        self.logger.info(f"🎮 py300chess SYSTEM READY{mode_info}")
        self.logger.info("="*60)
        
        # Show what's running
        for component, status in self.component_status.items():
            if status == "running":
                self.logger.info(f"✅ {component.replace('_', ' ').title()}")
            elif status == "not_available":
                self.logger.info(f"⚠️ {component.replace('_', ' ').title()} (not implemented)")
            else:
                self.logger.info(f"📊 {component.replace('_', ' ').title()}: {status}")
        
        # Show available streams
        try:
            import pylsl
            streams = pylsl.resolve_streams()
            if streams:
                self.logger.info("\n📡 Available LSL Streams:")
                for stream in streams:
                    self.logger.info(f"  - {stream.name()} ({stream.type()})")
        except:
            pass
        
        self.logger.info("="*60)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}")
        self.shutdown()
    
    def _cleanup(self):
        """Final cleanup on exit."""
        if self.is_running and not self.shutdown_requested:
            self.shutdown()


def setup_logging(debug_mode: bool = False, log_file: Optional[str] = None):
    """Setup logging configuration."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Reduce noise from some libraries
    logging.getLogger('pylsl').setLevel(logging.WARNING)


def main():
    """Main entry point for py300chess system."""
    parser = argparse.ArgumentParser(
        description='py300chess - P300-based Chess Control System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
OPERATING MODES:
  full        Complete BCI chess system (default)
  eeg_only    EEG streaming and P300 detection only
  simulation  Force simulated EEG mode for testing
  hardware    Force real EEG hardware mode
  chess_only  Chess game without BCI (future)

EXAMPLES:
  python main.py                    # Clean single-terminal mode
  python main.py --mode eeg_only    # EEG pipeline in single terminal
  python main.py --debug           # Multi-terminal debug mode
  python main.py --mode simulation --debug  # Debug with simulated EEG
  python main.py --headless --duration 300  # Run for 5 minutes
  python main.py --debug --log-file session.log  # Debug with file logging
        """
    )
    
    # Operating mode
    parser.add_argument(
        '--mode', 
        choices=['full', 'eeg_only', 'simulation', 'hardware', 'chess_only'],
        default='full',
        help='System operating mode (default: full)'
    )
    
    # Interface mode
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode without interactive console'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        help='Runtime duration in seconds (headless mode only)'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path (default: config.yaml)'
    )
    
    # Logging
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging and multi-terminal mode'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log to file in addition to console'
    )
    
    # Development options
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate configuration and exit'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug_mode=args.debug, log_file=args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info("🔧 Loading configuration...")
        config = get_config(args.config)
        
        # Apply command line overrides
        if args.mode in ['simulation']:
            config.eeg.use_simulation = True
        elif args.mode in ['hardware']:
            config.eeg.use_simulation = False
        
        if args.debug:
            config.feedback.debug_mode = True
        
        # Validate only mode
        if args.validate_only:
            logger.info("✅ Configuration valid")
            return 0
        
        # Create and start system orchestrator
        orchestrator = SystemOrchestrator(config, use_separate_terminals=args.debug)
        
        # Start system
        if not orchestrator.start_system(mode=args.mode):
            logger.error("Failed to start system")
            return 1
        
        # Run in appropriate mode
        if args.headless:
            orchestrator.run_headless(duration=args.duration)
        else:
            orchestrator.run_interactive()
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"System error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())