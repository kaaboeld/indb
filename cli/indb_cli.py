#!/usr/bin/env python3
"""
INDB CLI - Modern Terminal Interface
Beautiful command-line interface for INDB operations
"""

import sys
import os
sys.path.append(os.getcwd())
import argparse
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from core.indb import INDB
from core.indb import INDB
try:
    from storage.migration_manager import MigrationManager
except ImportError:
    # Fallback/Mock for when running in environments where storage isn't fully set up
    class MigrationManager:
        def get_status(self): return {'applied_count': 0, 'total_migrations': 0, 'pending_count': 0, 'applied_migrations': [], 'pending_migrations': []}
        def run_migrations(self, db): return True
        def rollback_last(self, db): return True

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text: str):
    """Print styled header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.END} {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_table(headers: list, rows: list):
    """Print formatted table"""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # Print header
    header_row = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(f"{Colors.BOLD}{header_row}{Colors.END}")
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))

# ============================================================================
# Commands
# ============================================================================

def cmd_status(args):
    """Show database status"""
    print_header("INDB Status")
    
    try:
        db = INDB()
        
        # Basic stats
        total_events = len(db.memory)
        print_info(f"Total Events: {Colors.BOLD}{total_events}{Colors.END}")
        
        # Temporal distribution
        if total_events > 0:
            seasons = {}
            quarters = {}
            for event in db.memory:
                if hasattr(event, 'temporal_metadata') and event.temporal_metadata:
                    season = event.temporal_metadata.get('season', 'unknown')
                    quarter = event.temporal_metadata.get('quarter', 0)
                    seasons[season] = seasons.get(season, 0) + 1
                    quarters[f"Q{quarter}"] = quarters.get(f"Q{quarter}", 0) + 1
            
            print(f"\n{Colors.BOLD}Temporal Distribution:{Colors.END}")
            for season, count in sorted(seasons.items()):
                bar = "█" * (count // 10)
                print(f"  {season.capitalize():10} {bar} {count}")
            
            print(f"\n{Colors.BOLD}Quarterly Distribution:{Colors.END}")
            for quarter, count in sorted(quarters.items()):
                bar = "█" * (count // 10)
                print(f"  {quarter:10} {bar} {count}")
        
        # Migration status
        print(f"\n{Colors.BOLD}Migration Status:{Colors.END}")
        migration_manager = MigrationManager()
        status = migration_manager.get_status()
        
        print_info(f"Applied: {status['applied_count']}/{status['total_migrations']}")
        if status['pending_count'] > 0:
            print_warning(f"Pending: {status['pending_count']} migration(s)")
        else:
            print_success("All migrations applied")
        
        print()
        
    except Exception as e:
        print_error(f"Failed to get status: {e}")
        sys.exit(1)

def cmd_query(args):
    """Execute query against INDB"""
    print_header("INDB Query")
    
    try:
        # Build context
        context = {
            "mood": args.mood,
            "location": args.location
        }
        
        # Build request
        payload = {"context": context}
        if args.temporal:
            payload["temporal_query"] = args.temporal
        
        print_info(f"Context: {args.mood} @ {args.location}")
        if args.temporal:
            print_info(f"Temporal Filter: {args.temporal}")
        
        # Execute query
        url = f"{args.api}/api/v2/interpret"
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print_error(f"Query failed: {response.status_code}")
            sys.exit(1)
        
        data = response.json()
        
        # Display results
        print(f"\n{Colors.BOLD}Results:{Colors.END}")
        print_info(f"Total in DB: {data['metadata']['total_memory_size']}")
        if 'temporal_filtered_count' in data['metadata']:
            print_info(f"Temporal Filtered: {data['metadata']['temporal_filtered_count']}")
        print_info(f"Activated: {data['metadata']['activated_count']}")
        print_info(f"Query Time: {data['metadata']['performance']['query_time_ms']}ms")
        
        # Show events
        if data['events']:
            print(f"\n{Colors.BOLD}Top Events:{Colors.END}")
            for i, event in enumerate(data['events'][:args.limit], 1):
                print(f"\n{Colors.CYAN}[{i}] {event['derived_emotion']}{Colors.END} (score: {event['activation_score']})")
                print(f"    Location: {event['original_location']}")
                print(f"    Narrative: {event['interpretation']['narrative'][:80]}...")
        else:
            print_warning("No events activated")
        
        print()
        
    except Exception as e:
        print_error(f"Query failed: {e}")
        sys.exit(1)

def cmd_migrations(args):
    """Manage migrations"""
    print_header("Migration Management")
    
    try:
        migration_manager = MigrationManager()
        
        if args.action == "status":
            status = migration_manager.get_status()
            
            print(f"{Colors.BOLD}Applied Migrations:{Colors.END}")
            if status['applied_migrations']:
                headers = ["Version", "Name", "Status", "Applied At"]
                rows = []
                for m in status['applied_migrations']:
                    applied_at = datetime.fromtimestamp(m['applied_at']).strftime('%Y-%m-%d %H:%M')
                    rows.append([m['version'], m['name'], m['status'], applied_at])
                print_table(headers, rows)
            else:
                print_info("No migrations applied yet")
            
            print(f"\n{Colors.BOLD}Pending Migrations:{Colors.END}")
            if status['pending_migrations']:
                for m in status['pending_migrations']:
                    print(f"  • {m['version']}: {m['name']}")
            else:
                print_success("No pending migrations")
        
        elif args.action == "apply":
            db = INDB()
            success = migration_manager.run_migrations(db)
            if success:
                print_success("All migrations applied successfully")
            else:
                print_error("Migration failed")
                sys.exit(1)
        
        elif args.action == "rollback":
            db = INDB()
            success = migration_manager.rollback_last(db)
            if success:
                print_success("Last migration rolled back")
            else:
                print_error("Rollback failed")
                sys.exit(1)
        
        print()
        
    except Exception as e:
        print_error(f"Migration operation failed: {e}")
        sys.exit(1)

def cmd_stats(args):
    """Show detailed statistics"""
    print_header("INDB Statistics")
    
    try:
        db = INDB()
        
        total = len(db.memory)
        
        if total == 0:
            print_warning("Database is empty")
            return
        
        # Location distribution
        locations = {}
        for event in db.memory:
            loc = event.location
            locations[loc] = locations.get(loc, 0) + 1
        
        print(f"{Colors.BOLD}Top Locations:{Colors.END}")
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {loc:15} {bar} {count:4} ({percentage:5.1f}%)")
        
        # Token analysis
        token_freq = {}
        for event in db.memory:
            for token in event.raw_data_anchor:
                if not token.startswith('ts_'):
                    token_freq[token] = token_freq.get(token, 0) + 1
        
        print(f"\n{Colors.BOLD}Top Tokens:{Colors.END}")
        for token, count in sorted(token_freq.items(), key=lambda x: x[1], reverse=True)[:15]:
            bar = "█" * (count // 5)
            print(f"  {token:20} {bar} {count}")
        
        print()
        
    except Exception as e:
        print_error(f"Failed to generate statistics: {e}")
        sys.exit(1)

def cmd_auth(args):
    """Test authentication"""
    print_header("Authentication Test")
    
    try:
        url = f"{args.api}/token"
        data = {
            "username": args.username,
            "password": args.password
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            print_success("Authentication successful")
            print_info(f"Token Type: {token_data['token_type']}")
            print(f"\n{Colors.BOLD}Access Token:{Colors.END}")
            print(f"{token_data['access_token'][:50]}...")
        else:
            print_error(f"Authentication failed: {response.status_code}")
            sys.exit(1)
        
        print()
        
    except Exception as e:
        print_error(f"Authentication failed: {e}")
        sys.exit(1)

def cmd_firewall(args):
    """Manage Cognitive Firewall rules"""
    print_header("Cognitive Firewall")
    
    from services.interpretation.cognitive_firewall import CognitiveFirewall, CognitiveRule, FirewallAction
    
    if args.action == "generate":
        # Generate a sample firewall profile
        print_info(f"Generating firewall profile: {Colors.BOLD}{args.name}{Colors.END}")
        
        rules = []
        if args.template == "strict":
            rules.append({
                "name": "Block All Debug",
                "condition": {"event.tag": "DEBUG"},
                "action": "block",
                "priority": 100
            })
            rules.append({
                "name": "Redact PII",
                "condition": {"event.raw_data_anchor": "regex:(email|phone|ssn)"},
                "action": "redact",
                "redaction_fields": ["raw_data_anchor", "narrative"],
                "priority": 90
            })
        elif args.template == "therapy":
            rules.append({
                 "name": "Allow Trauma Processing",
                 "condition": {"context.mode": "Therapy"},
                 "action": "allow",
                 "priority": 1000
            })
        elif args.template == "wizard":
            print(f"\n{Colors.BOLD}Interactive Firewall Builder{Colors.END}")
            print("Define rules to filter events based on Context and Event properties.\n")
            
            while True:
                name = input(f"{Colors.CYAN}Rule Name{Colors.END} (or 'q' to finish): ").strip()
                if name.lower() in ('q', 'quit', ''):
                    break
                    
                print(f"  {Colors.YELLOW}Condition:{Colors.END}")
                cond_key = input("    Field (e.g. context.mood, event.tag): ").strip()
                cond_val = input("    Value (start with regex: for pattern): ").strip()
                
                action = input(f"  {Colors.YELLOW}Action{Colors.END} (block/redact/warn/allow): ").strip().lower()
                
                rule = {
                    "name": name,
                    "condition": {cond_key: cond_val},
                    "action": action,
                    "priority": 10
                }
                
                if action == "redact":
                    fields = input("    Fields to redact (comma sep, e.g. narrative,tokens): ").strip()
                    rule["redaction_fields"] = [f.strip() for f in fields.split(",")]
                    
                rules.append(rule)
                print_success(f"Added rule '{name}'\n")
            
        # Write to file
        filename = f"firewall_{args.name}.json"
        with open(filename, "w") as f:
            json.dump(rules, f, indent=2)
            
        print_success(f"Generated {filename}")
        
    elif args.action == "test":
        # Test a context against rules
        print_info("Testing firewall rules...")
        
        # Load rules (mock loading from file or default for now)
        fw = CognitiveFirewall()
        if args.file and os.path.exists(args.file):
            with open(args.file, "r") as f:
                data = json.load(f)
                fw = CognitiveFirewall.from_dict_list(data)
            print_info(f"Loaded rules from {args.file}")
        
        # Parse context
        try:
            context = json.loads(args.context)
        except:
             print_error("Invalid JSON context")
             return

        # Mock event
        mock_event = {
            "raw_data_anchor": ["test", "debug", "panic"],
            "location": "TestLab",
            "derived_emotion": "Panic",
            "tag": "DEBUG"
        }
        
        decision = fw.inspect(mock_event, context)
        
        print(f"\n{Colors.BOLD}Decision:{Colors.END} {decision['action']}")
        if decision['rule_name']:
            print(f"Rule: {decision['rule_name']}")
        print(f"Reason: {decision['reason']}")
        
        if decision['modified']:
            print(f"Modified Event: {decision['event']}")
            
    print()

def cmd_fsck(args):
    """Check physical integrity of the database file"""
    print_header("INDB Fsck Diagnostics")
    
    try:
        from storage.binary import verify_integrity, repair_header, DB_FILE
        
        print_info(f"Checking file: {Colors.BOLD}{DB_FILE}{Colors.END}")
        
        result = verify_integrity()
        
        if result["valid"]:
            print_success("Integrity Check Passed")
            print_info(f"Version: v{result['version']}")
            print_info(f"CRC32: {result['crc']}")
            print_info(f"Size: {result['size']} bytes")
        else:
            print_error("INTEGRITY CHECK FAILED")
            print_error(f"Reason: {result['error']}")
            
            if "stored_crc" in result:
                 print_info(f"Stored CRC: {result['stored_crc']}")
                 print_info(f"Actual CRC: {result['actual_crc']}")
            
            if args.repair:
                print(f"\n{Colors.BOLD}Attempting Repair...{Colors.END}")
                if repair_header():
                    print_success("Header Repaired! (Payload verified)")
                    print_info("Run fsck again to confirm.")
                else:
                    print_error("Repair Failed: Payload is corrupted or undecryptable.")
                    sys.exit(1)
            else:
                print(f"\n{Colors.YELLOW}Tip: Run with --repair to attempt recovery{Colors.END}")
                sys.exit(1)
            
    except Exception as e:
        print_error(f"Fsck failed: {e}")
        sys.exit(1)
        
    print()

def cmd_tui(args):
    """Launch Terminal User Interface"""
    try:
        import importlib
        import shutil
        import sys
        from pathlib import Path

        tui_root = Path(__file__).resolve().parent / "tui"
        for cache in tui_root.rglob("__pycache__"):
            if cache.is_dir():
                shutil.rmtree(cache, ignore_errors=True)

        importlib.invalidate_caches()
        from cli.tui.app import INDBTuiApp, TUI_BUILD, _verify_tui_modules

        _verify_tui_modules()
        print_info(f"Starting INDB TUI ({TUI_BUILD})…")
        app = INDBTuiApp(api_url=args.api)
        app.run()
    except ImportError as e:
        print_error(f"Failed to load TUI: {e}")
        print_info("Make sure 'textual' is installed: pip install textual")
        sys.exit(1)
    except Exception as e:
        print_error(f"TUI Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description=f"{Colors.BOLD}{Colors.CYAN}INDB CLI{Colors.END} - Modern Terminal Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    parser_status = subparsers.add_parser('status', help='Show database status')
    parser_status.set_defaults(func=cmd_status)
    
    # Query command
    parser_query = subparsers.add_parser('query', help='Execute query')
    parser_query.add_argument('--mood', default='Neutral', help='Mood context')
    parser_query.add_argument('--location', default='Berlin', help='Location context')
    parser_query.add_argument('--temporal', help='Temporal query (e.g., "summer events")')
    parser_query.add_argument('--limit', type=int, default=5, help='Max results to show')
    parser_query.add_argument('--api', default='http://localhost:8000', help='API base URL')
    parser_query.set_defaults(func=cmd_query)
    
    # Migrations command
    parser_migrations = subparsers.add_parser('migrations', help='Manage migrations')
    parser_migrations.add_argument('action', choices=['status', 'apply', 'rollback'], help='Migration action')
    parser_migrations.set_defaults(func=cmd_migrations)
    
    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show detailed statistics')
    parser_stats.set_defaults(func=cmd_stats)
    
    # Auth command
    parser_auth = subparsers.add_parser('auth', help='Test authentication')
    parser_auth.add_argument('--username', default='admin', help='Username')
    parser_auth.add_argument('--password', default='rotterdam', help='Password')
    parser_auth.add_argument('--api', default='http://localhost:8000', help='API base URL')
    parser_auth.set_defaults(func=cmd_auth)

    # Firewall command
    parser_firewall = subparsers.add_parser('firewall', help='Manage Cognitive Firewall')
    parser_firewall.add_argument('action', choices=['generate', 'test'], help='Firewall action')
    parser_firewall.add_argument('--name', default='default', help='Profile name')
    parser_firewall.add_argument('--template', choices=['strict', 'therapy', 'default', 'wizard'], default='default', help='Template to use')
    parser_firewall.add_argument('--context', default='{"mood": "Neutral"}', help='Context JSON for testing')
    parser_firewall.add_argument('--file', help='Path to firewall rules JSON')
    parser_firewall.set_defaults(func=cmd_firewall)

    # Fsck command
    parser_fsck = subparsers.add_parser('fsck', help='Check database integrity')
    parser_fsck.add_argument('--repair', action='store_true', help='Attempt to repair corruption')
    parser_fsck.set_defaults(func=cmd_fsck)

    # TUI command
    parser_tui = subparsers.add_parser('tui', help='Launch Terminal UI')
    parser_tui.add_argument('--api', default=None, help='API base URL (auto-detects if omitted)')
    parser_tui.set_defaults(func=cmd_tui)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)

if __name__ == "__main__":
    main()
