"""
    Game03 Network Server Application
    Run this to start a dedicated game server
    
    Usage:
        python network_server_app.py [--host 0.0.0.0] [--port 5000] [--max-players 4]
"""

import argparse
import sys
import signal
from network_server import NetworkServer


def main():
    """Main entry point for server application"""
    parser = argparse.ArgumentParser(description='Game03 Network Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=4001, help='Server port (default: 5001)')
    parser.add_argument('--max-players', type=int, default=4, help='Maximum players (default: 4)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Create and start server
    server = NetworkServer(
        host=args.host,
        port=args.port,
        max_players=args.max_players
    )
    
    def signal_handler(sig, frame):
        print("\n[MAIN] Shutting down server...")
        server.stop()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.start()
        print(f"[MAIN] Game03 Server running on {args.host}:{args.port}")
        print("[MAIN] Press Ctrl+C to stop")
        
        # Keep server running
        while True:
            import time
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted")
        server.stop()
    except Exception as e:
        print(f"[MAIN] Error: {e}")
        server.stop()


if __name__ == '__main__':
    main()
