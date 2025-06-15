import os
import subprocess
import sys
import time
import signal
import shutil
import atexit
from pathlib import Path

# Global variables to track processes
backend_process = None
frontend_process = None

def cleanup_processes():
    """Clean up all spawned processes."""
    global backend_process, frontend_process
    print("\n🧹 Cleaning up processes...")
    
    if backend_process:
        terminate_process(backend_process, "Backend")
        backend_process = None
    
    if frontend_process:
        terminate_process(frontend_process, "Frontend")
        frontend_process = None
    
    print("✓ Cleanup completed")

def signal_handler(signum, frame):
    """Handle interrupt signals (Ctrl+C, etc.)."""
    print(f"\n⚠️  Received signal {signum}")
    cleanup_processes()
    sys.exit(0)

def install_requirements():
    """Install Python requirements with proper error handling."""
    try:
        print("Installing Python dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("✓ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        return False
    except FileNotFoundError:
        print("✗ requirements.txt not found")
        return False

def run_backend():
    """Start the backend server using uvicorn."""
    global backend_process
    try:
        print("Starting backend server...")
        # Use the current working directory explicitly
        cwd = os.getcwd()
          # Start uvicorn with proper arguments for production
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=cwd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        # Store reference to the process globally
        backend_process = proc
        
        # Wait a moment for the process to start
        time.sleep(3)
        
        # Check if the process is still running (not terminated due to error)
        if proc.poll() is not None:
            print(f"✗ Backend server failed to start (exit code: {proc.returncode})")
            backend_process = None
            return None
        
        print("✓ Backend server started successfully")
        return proc
    except Exception as e:
        print(f"✗ Failed to start backend server: {e}")
        backend_process = None
        return None

def find_npm_path():
    """Find npm executable path."""
    import shutil
    npm_path = shutil.which("npm")
    if npm_path:
        return npm_path
    
    # Common npm installation paths on Windows
    possible_paths = [
        r"C:\Program Files\nodejs\npm.cmd",
        r"C:\Program Files (x86)\nodejs\npm.cmd",
        os.path.expanduser(r"~\AppData\Roaming\npm\npm.cmd"),
        os.path.expanduser(r"~\scoop\apps\nodejs\current\npm.cmd"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def run_frontend():
    """Start the frontend development server."""
    global frontend_process
    current_dir = os.getcwd()  # Save current directory
    frontend_dir = Path(current_dir) / "frontend"
    
    if not frontend_dir.is_dir():
        print("✗ Frontend directory not found")
        return None
    
    # Find npm executable
    npm_cmd = find_npm_path()
    if not npm_cmd:
        print("✗ npm not found. Please install Node.js and npm")
        print("Download from: https://nodejs.org/")
        return None
    
    print(f"Found npm at: {npm_cmd}")
        
    try:
        print("Setting up frontend dependencies...")
        # Change to frontend directory temporarily
        os.chdir(frontend_dir)
        
        # Check if node_modules exists, if not install dependencies
        if not os.path.exists("node_modules"):
            print("Installing frontend dependencies...")
            subprocess.check_call([npm_cmd, "install","--force"], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print("✓ Frontend dependencies installed")
        else:
            print("✓ Frontend dependencies already installed")
        
        # Check if .next build directory exists, if not build the project
        if not os.path.exists(".next"):
            print("Building frontend...")
            subprocess.check_call([npm_cmd, "run", "build"], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print("✓ Frontend built successfully")
        else:
            print("✓ Frontend already built")
        
        # Start the server
        print("Starting frontend server...")
        proc = subprocess.Popen([npm_cmd, "start"],
                              creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
        
        # Store reference to the process globally
        frontend_process = proc
        
        # Wait a moment to ensure it starts
        time.sleep(2)
        if proc.poll() is not None:
            print(f"✗ Frontend server failed to start (exit code: {proc.returncode})")
            frontend_process = None
            return None
            
        print("✓ Frontend server started successfully")
        return proc
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to setup/start frontend: {e}")
        frontend_process = None
        return None
    except FileNotFoundError:
        print("✗ npm not found. Please install Node.js and npm")
        print("Download from: https://nodejs.org/")
        frontend_process = None
        return None
    finally:
        # Always restore the original directory
        os.chdir(current_dir)

def terminate_process(proc, name="Process"):
    """Safely terminate a process with timeout."""
    if not proc or proc.poll() is not None:
        return
        
    try:
        print(f"Terminating {name}...")
        proc.terminate()
        
        # Wait for graceful shutdown
        try:
            proc.wait(timeout=5)
            print(f"✓ {name} terminated gracefully")
        except subprocess.TimeoutExpired:
            print(f"Force killing {name}...")
            proc.kill()
            proc.wait()
            print(f"✓ {name} force killed")
            
    except Exception as e:
        print(f"Error terminating {name}: {e}")
        try:
            proc.kill()
        except:
            pass

def monitor_processes(backend_proc, frontend_proc):
    """Monitor both processes and handle shutdowns."""
    print("\n🚀 Both servers are running!")
    print("Backend: http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("Press Ctrl+C to stop both servers\n")
    
    try:
        while True:
            # Check if backend process has stopped
            if backend_proc and backend_proc.poll() is not None:
                print("Backend process stopped unexpectedly")
                terminate_process(frontend_proc, "Frontend")
                break
                
            # Check if frontend process has stopped  
            if frontend_proc and frontend_proc.poll() is not None:
                print("Frontend process stopped unexpectedly")
                terminate_process(backend_proc, "Backend")
                break
                
            # Sleep to reduce CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down servers...")
        terminate_process(backend_proc, "Backend")
        terminate_process(frontend_proc, "Frontend")
        print("✓ All processes terminated")

if __name__ == "__main__":
    print("🔧 VoiceBot Setup & Launch Script")
    print("=" * 40)
    
    # Register cleanup function to run at exit
    atexit.register(cleanup_processes)
    
    # Register signal handlers for graceful shutdown
    if os.name == 'nt':  # Windows
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:  # Unix-like systems
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGHUP, signal_handler)
    
    try:
        # Install backend requirements
        if not install_requirements():
            print("❌ Failed to install requirements. Exiting...")
            sys.exit(1)

        # Start backend server
        backend_proc = run_backend()
        if not backend_proc:
            print("❌ Failed to start backend. Exiting...")
            sys.exit(1)
            
        # Give backend time to start
        print("Waiting for backend to initialize...")
        time.sleep(5)
        
        # Check if backend is still running
        if backend_proc.poll() is not None:
            print("❌ Backend server stopped during initialization")
            sys.exit(1)

        # Start frontend server
        frontend_proc = run_frontend()
        if not frontend_proc:
            print("❌ Failed to start frontend. Terminating backend...")
            terminate_process(backend_proc, "Backend")
            sys.exit(1)

        # Monitor both processes
        monitor_processes(backend_proc, frontend_proc)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cleanup_processes()
        sys.exit(1)
    except SystemExit:
        # Handle explicit sys.exit() calls
        cleanup_processes()
        raise
    finally:
        # Final cleanup (belt and suspenders approach)
        cleanup_processes()