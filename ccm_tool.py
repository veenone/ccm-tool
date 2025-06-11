"""
Main command-line interface for the Smartcard Management Tool.
"""

import logging
import os
import sys
import click
from typing import Optional, List
import colorama
from colorama import Fore, Back, Style
from tabulate import tabulate
from smartcard.util import toHexString

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.smartcard_manager import SmartcardManager, SmartcardException
from src.globalplatform import GlobalPlatformManager, SecurityDomainInfo, ApplicationInfo
from src.secure_channel import SecureChannelManager, KeySet
from src.config_manager import ConfigManager
from src.visualization import SecurityDomainVisualizer
from src.database_manager import DatabaseManager, KeysetRecord
from src.ota_manager import OTAManager

# Initialize colorama for cross-platform color support
colorama.init()

# Setup logging
def setup_logging(config_manager: ConfigManager):
    """Setup logging configuration"""
    log_config = config_manager.logging_config
    if log_config:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_config.file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_config.level.upper()),
            format=log_config.format,
            handlers=[
                logging.FileHandler(log_config.file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class SmartcardCLI:
    """Command-line interface for smartcard management"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        setup_logging(self.config_manager)
        
        self.sc_manager = SmartcardManager()
        self.gp_manager = GlobalPlatformManager(self.sc_manager)
        self.secure_channel = SecureChannelManager(self.sc_manager)
        self.visualizer = SecurityDomainVisualizer(
            self.config_manager.get_visualization_output_dir()
        )
        
        self.connected_reader: Optional[str] = None
        self.secure_channel_active = False
    
    def print_banner(self):
        """Print application banner"""
        app_config = self.config_manager.app_config
        if app_config:
            print(f"{Fore.CYAN}{Style.BRIGHT}")
            print("╔" + "═" * 60 + "╗")
            print(f"║{app_config.name:^60}║")
            print(f"║{f'Version {app_config.version}':^60}║")
            print("╚" + "═" * 60 + "╝")
            print(f"{Style.RESET_ALL}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


@click.group()
@click.pass_context
def cli(ctx):
    """Smartcard Management Tool - Comprehensive PC/SC and GlobalPlatform interface"""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = SmartcardCLI()
    ctx.obj['cli'].print_banner()


@cli.command()
@click.pass_context
def list_readers(ctx):
    """List all available PC/SC readers"""
    cli_obj = ctx.obj['cli']
    
    try:
        readers = cli_obj.sc_manager.list_readers()
        if readers:
            cli_obj.print_success(f"Found {len(readers)} reader(s):")
            for i, reader in enumerate(readers, 1):
                print(f"  {i}. {reader}")
        else:
            cli_obj.print_warning("No PC/SC readers found")
    except Exception as e:
        cli_obj.print_error(f"Error listing readers: {e}")


@cli.command()
@click.argument('reader_name')
@click.option('--timeout', default=5000, help='Connection timeout in milliseconds')
@click.pass_context
def connect(ctx, reader_name: str, timeout: int):
    """Connect to a smartcard reader"""
    cli_obj = ctx.obj['cli']
    
    try:
        if cli_obj.sc_manager.connect_to_reader(reader_name, timeout):
            cli_obj.connected_reader = reader_name
            cli_obj.print_success(f"Connected to reader: {reader_name}")
            
            # Try to select Card Manager
            if cli_obj.gp_manager.select_card_manager():
                cli_obj.print_success("Card Manager selected")
            else:
                cli_obj.print_warning("Could not select Card Manager")
        else:
            cli_obj.print_error(f"Failed to connect to reader: {reader_name}")
    except Exception as e:
        cli_obj.print_error(f"Connection error: {e}")


@cli.command()
@click.pass_context
def disconnect(ctx):
    """Disconnect from all readers"""
    cli_obj = ctx.obj['cli']
    
    try:
        if cli_obj.secure_channel_active:
            cli_obj.secure_channel.close_secure_channel()
            cli_obj.secure_channel_active = False
        
        cli_obj.sc_manager.disconnect_all()
        cli_obj.connected_reader = None
        cli_obj.print_success("Disconnected from all readers")
    except Exception as e:
        cli_obj.print_error(f"Disconnect error: {e}")


@cli.command()
@click.pass_context
def list_keysets(ctx):
    """List all configured keysets"""
    cli_obj = ctx.obj['cli']
    
    keysets = cli_obj.config_manager.list_keysets()
    if keysets:
        cli_obj.print_success(f"Found {len(keysets)} keyset(s):")
        
        table_data = []
        for name in keysets:
            keyset = cli_obj.config_manager.get_keyset(name)
            if keyset:
                table_data.append([
                    name,
                    keyset.protocol,
                    keyset.key_version,
                    keyset.enc_key.hex()[:16] + "..."
                ])
        
        print(tabulate(table_data, 
                      headers=['Name', 'Protocol', 'Version', 'ENC Key (partial)'],
                      tablefmt='grid'))
    else:
        cli_obj.print_warning("No keysets configured")


@cli.command()
@click.argument('keyset_name')
@click.option('--security-level', default=3, help='Security level (1=MAC, 2=MAC+ENC, 3=MAC+ENC+RMAC)')
@click.pass_context
def establish_secure_channel(ctx, keyset_name: str, security_level: int):
    """Establish secure channel with specified keyset"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    keyset = cli_obj.config_manager.get_keyset(keyset_name)
    if not keyset:
        cli_obj.print_error(f"Keyset '{keyset_name}' not found")
        return
    
    try:
        cli_obj.print_info(f"Establishing {keyset.protocol} secure channel...")
        
        if cli_obj.secure_channel.establish_secure_channel(keyset, security_level):
            cli_obj.secure_channel_active = True
            cli_obj.print_success(f"Secure channel established ({keyset.protocol}, SL={security_level})")
        else:
            cli_obj.print_error("Failed to establish secure channel")
    except Exception as e:
        cli_obj.print_error(f"Secure channel error: {e}")


@cli.command()
@click.pass_context
def close_secure_channel(ctx):
    """Close the active secure channel"""
    cli_obj = ctx.obj['cli']
    
    if cli_obj.secure_channel_active:
        cli_obj.secure_channel.close_secure_channel()
        cli_obj.secure_channel_active = False
        cli_obj.print_success("Secure channel closed")
    else:
        cli_obj.print_warning("No active secure channel")


@cli.command()
@click.pass_context
def list_applications(ctx):
    """List all applications on the card"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    try:
        applications = cli_obj.gp_manager.list_applications()
        
        if applications:
            cli_obj.print_success(f"Found {len(applications)} application(s):")
            
            table_data = []
            for app in applications:
                table_data.append([
                    toHexString(app.aid),
                    app.life_cycle.name,
                    f"0x{app.privileges:02X}",
                    f"0x{app.life_cycle.value:02X}"
                ])
            
            print(tabulate(table_data,
                          headers=['AID', 'Lifecycle', 'Privileges', 'LC Value'],
                          tablefmt='grid'))
        else:
            cli_obj.print_warning("No applications found")
            
    except Exception as e:
        cli_obj.print_error(f"Error listing applications: {e}")


@cli.command()
@click.pass_context
def list_security_domains(ctx):
    """List all security domains on the card"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    try:
        domains = cli_obj.gp_manager.list_security_domains()
        
        if domains:
            cli_obj.print_success(f"Found {len(domains)} security domain(s):")
            
            table_data = []
            for domain in domains:
                table_data.append([
                    toHexString(domain.aid),
                    domain.domain_type,
                    domain.life_cycle.name,
                    f"0x{domain.privileges:02X}",
                    f"0x{domain.life_cycle.value:02X}"
                ])
            
            print(tabulate(table_data,
                          headers=['AID', 'Type', 'Lifecycle', 'Privileges', 'LC Value'],
                          tablefmt='grid'))
        else:
            cli_obj.print_warning("No security domains found")
            
    except Exception as e:
        cli_obj.print_error(f"Error listing security domains: {e}")


@cli.command()
@click.argument('aid', type=str)
@click.option('--domain-type', type=click.Choice(['SSD', 'AMSD', 'DMSD']), 
              default='SSD', help='Type of security domain to create')
@click.option('--privileges', default=0x80, help='Privilege bytes (hex)')
@click.pass_context
def create_security_domain(ctx, aid: str, domain_type: str, privileges: int):
    """Create a new security domain"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    if not cli_obj.secure_channel_active:
        cli_obj.print_error("Secure channel required. Use 'establish-secure-channel' command first.")
        return
    
    try:
        aid_bytes = bytes.fromhex(aid)
        cli_obj.print_info(f"Creating {domain_type} with AID: {aid}")
        
        if cli_obj.gp_manager.create_security_domain(aid_bytes, domain_type, privileges):
            cli_obj.print_success(f"Security domain created successfully")
        else:
            cli_obj.print_error("Failed to create security domain")
            
    except ValueError:
        cli_obj.print_error("Invalid AID format. Use hex string (e.g., A00000015100)")
    except Exception as e:
        cli_obj.print_error(f"Error creating security domain: {e}")


@cli.command()
@click.argument('target_aid', type=str)
@click.option('--operation', type=click.Choice(['lock', 'unlock', 'terminate']),
              required=True, help='CLFDB operation to perform')
@click.pass_context
def clfdb(ctx, target_aid: str, operation: str):
    """Perform Card Life Cycle Database operation"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    if not cli_obj.secure_channel_active:
        cli_obj.print_error("Secure channel required. Use 'establish-secure-channel' command first.")
        return
    
    try:
        aid_bytes = bytes.fromhex(target_aid)
        cli_obj.print_info(f"Performing CLFDB {operation} on: {target_aid}")
        
        if cli_obj.gp_manager.perform_clfdb(aid_bytes, operation):
            cli_obj.print_success(f"CLFDB {operation} completed successfully")
        else:
            cli_obj.print_error(f"CLFDB {operation} failed")
            
    except ValueError:
        cli_obj.print_error("Invalid AID format. Use hex string (e.g., A00000015100)")
    except Exception as e:
        cli_obj.print_error(f"Error performing CLFDB: {e}")


@cli.command()
@click.argument('object_aid', type=str)
@click.argument('target_sd_aid', type=str)
@click.pass_context
def extradite(ctx, object_aid: str, target_sd_aid: str):
    """Extradite application or security domain to another security domain"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    if not cli_obj.secure_channel_active:
        cli_obj.print_error("Secure channel required. Use 'establish-secure-channel' command first.")
        return
    
    try:
        object_aid_bytes = bytes.fromhex(object_aid)
        target_aid_bytes = bytes.fromhex(target_sd_aid)
        
        cli_obj.print_info(f"Extraditing {object_aid} to {target_sd_aid}")
        
        if cli_obj.gp_manager.extradite_object(object_aid_bytes, target_aid_bytes):
            cli_obj.print_success("Extradition completed successfully")
        else:
            cli_obj.print_error("Extradition failed")
            
    except ValueError:
        cli_obj.print_error("Invalid AID format. Use hex string (e.g., A00000015100)")
    except Exception as e:
        cli_obj.print_error(f"Error performing extradition: {e}")


@cli.command()
@click.option('--output-dir', default=None, help='Output directory for visualizations')
@click.pass_context
def visualize(ctx, output_dir: Optional[str]):
    """Generate visualization of security domains and applications"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    try:
        # Set output directory if provided
        if output_dir:
            cli_obj.visualizer.output_dir = output_dir
            os.makedirs(output_dir, exist_ok=True)
        
        cli_obj.print_info("Collecting card data for visualization...")
        
        # Get current card state
        domains = cli_obj.gp_manager.list_security_domains()
        applications = cli_obj.gp_manager.list_applications()
        
        if not domains and not applications:
            cli_obj.print_warning("No security domains or applications found to visualize")
            return
        
        cli_obj.print_info("Generating visualizations...")
        
        # Generate all visualizations
        output_files = cli_obj.visualizer.generate_all_visualizations(domains, applications)
        
        if output_files:
            cli_obj.print_success(f"Generated {len(output_files)} visualization(s):")
            for file_path in output_files:
                if os.path.exists(file_path):
                    print(f"  • {file_path}")
        else:
            cli_obj.print_warning("No visualizations were generated")
            
    except Exception as e:
        cli_obj.print_error(f"Error generating visualizations: {e}")


@cli.command()
@click.pass_context
def card_info(ctx):
    """Display general card information"""
    cli_obj = ctx.obj['cli']
    
    if not cli_obj.connected_reader:
        cli_obj.print_error("Not connected to any reader. Use 'connect' command first.")
        return
    
    try:
        # Get ATR
        if cli_obj.sc_manager.active_reader:
            atr = cli_obj.sc_manager.active_reader.get_atr()
            print(f"\n{Fore.CYAN}Card Information:{Style.RESET_ALL}")
            print(f"ATR: {toHexString(atr)}")
        
        # Get card-specific information
        card_info = cli_obj.gp_manager.get_card_info()
        
        if card_info:
            for key, value in card_info.items():
                print(f"{key}: {value}")
        
        # Status summary
        domains = cli_obj.gp_manager.list_security_domains()
        applications = cli_obj.gp_manager.list_applications()
        
        print(f"\n{Fore.CYAN}Summary:{Style.RESET_ALL}")
        print(f"Security Domains: {len(domains)}")
        print(f"Applications: {len(applications)}")
        print(f"Secure Channel: {'Active' if cli_obj.secure_channel_active else 'Inactive'}")
        
    except Exception as e:
        cli_obj.print_error(f"Error getting card information: {e}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show current connection and secure channel status"""
    cli_obj = ctx.obj['cli']
    
    print(f"\n{Fore.CYAN}Current Status:{Style.RESET_ALL}")
    print(f"Connected Reader: {cli_obj.connected_reader or 'None'}")
    print(f"Secure Channel: {'Active' if cli_obj.secure_channel_active else 'Inactive'}")
    
    if cli_obj.secure_channel_active and cli_obj.secure_channel.session:
        session = cli_obj.secure_channel.session
        print(f"  Protocol: {session.protocol}")
        print(f"  Security Level: {session.security_level}")
        print(f"  Sequence Counter: {session.sequence_counter}")


# ============================================================================
# Keyset Management Commands
# ============================================================================

@cli.group()
def keyset():
    """Keyset management commands"""
    pass


@keyset.command('list')
@click.option('--value-set', help='Filter by value set')
@click.option('--protocol', help='Filter by protocol (SCP02/SCP03)')
@click.pass_context
def list_keysets(ctx, value_set: str, protocol: str):
    """List available keysets"""
    cli_obj = ctx.obj['cli']
    
    try:
        db_manager = DatabaseManager()
        keysets = db_manager.get_keysets(value_set=value_set, protocol=protocol)
        
        if keysets:
            cli_obj.print_success(f"Found {len(keysets)} keyset(s):")
            
            # Group by value set
            by_value_set = {}
            for keyset in keysets:
                if keyset.value_set not in by_value_set:
                    by_value_set[keyset.value_set] = []
                by_value_set[keyset.value_set].append(keyset)
            
            for vs, ks_list in by_value_set.items():
                print(f"\n{Fore.YELLOW}Value Set: {vs}{Style.RESET_ALL}")
                table_data = []
                for ks in ks_list:
                    table_data.append([
                        ks.name,
                        ks.protocol,
                        f"v{ks.key_version}",
                        f"L{ks.security_level}",
                        ks.description[:40] + "..." if len(ks.description) > 40 else ks.description
                    ])
                
                print(tabulate(table_data, 
                             headers=['Name', 'Protocol', 'Version', 'Security', 'Description'],
                             tablefmt='grid'))
        else:
            cli_obj.print_warning("No keysets found")
    except Exception as e:
        cli_obj.print_error(f"Error listing keysets: {e}")


@keyset.command('add')
@click.argument('name')
@click.argument('value_set')
@click.option('--protocol', type=click.Choice(['SCP02', 'SCP03']), required=True, help='Security protocol')
@click.option('--enc-key', required=True, help='Encryption key (hex)')
@click.option('--mac-key', required=True, help='MAC key (hex)')
@click.option('--dek-key', required=True, help='DEK key (hex)')
@click.option('--key-version', type=int, default=1, help='Key version')
@click.option('--security-level', type=int, default=3, help='Security level (1-3)')
@click.option('--description', default='', help='Description')
@click.pass_context
def add_keyset(ctx, name: str, value_set: str, protocol: str, enc_key: str, 
               mac_key: str, dek_key: str, key_version: int, security_level: int, description: str):
    """Add a new keyset"""
    cli_obj = ctx.obj['cli']
    
    try:
        # Validate hex keys
        for key_name, key_value in [('enc-key', enc_key), ('mac-key', mac_key), ('dek-key', dek_key)]:
            try:
                bytes.fromhex(key_value)
                if len(key_value) not in [32, 48]:  # 16 or 24 bytes in hex
                    raise ValueError(f"Invalid key length")
            except ValueError:
                cli_obj.print_error(f"Invalid {key_name}: must be 32 or 48 hex characters")
                return
        
        if cli_obj.config_manager.add_keyset(name, value_set, protocol, enc_key, mac_key, 
                                           dek_key, key_version, security_level, description):
            cli_obj.print_success(f"Added keyset '{name}' to value set '{value_set}'")
        else:
            cli_obj.print_error("Failed to add keyset")
    except Exception as e:
        cli_obj.print_error(f"Error adding keyset: {e}")


@keyset.command('export')
@click.argument('value_set')
@click.argument('output_file')
@click.pass_context
def export_keysets(ctx, value_set: str, output_file: str):
    """Export keysets from a value set to YAML file"""
    cli_obj = ctx.obj['cli']
    
    try:
        if cli_obj.config_manager.export_keysets_to_yaml(value_set, output_file):
            cli_obj.print_success(f"Exported keysets from '{value_set}' to {output_file}")
        else:
            cli_obj.print_error("Failed to export keysets")
    except Exception as e:
        cli_obj.print_error(f"Error exporting keysets: {e}")


@keyset.command('import')
@click.argument('yaml_file')
@click.argument('target_value_set')
@click.pass_context
def import_keysets(ctx, yaml_file: str, target_value_set: str):
    """Import keysets from YAML file to a value set"""
    cli_obj = ctx.obj['cli']
    
    try:
        imported, skipped = cli_obj.config_manager.import_keysets_from_yaml(yaml_file, target_value_set)
        cli_obj.print_success(f"Imported {imported} keysets to '{target_value_set}', skipped {skipped}")
    except Exception as e:
        cli_obj.print_error(f"Error importing keysets: {e}")


@keyset.command('value-sets')
@click.pass_context
def list_value_sets(ctx):
    """List all available value sets"""
    cli_obj = ctx.obj['cli']
    
    try:
        value_sets = cli_obj.config_manager.get_value_sets()
        if value_sets:
            cli_obj.print_success(f"Available value sets:")
            for vs in value_sets:
                print(f"  • {vs}")
        else:
            cli_obj.print_warning("No value sets found")
    except Exception as e:
        cli_obj.print_error(f"Error listing value sets: {e}")


# ============================================================================
# OTA SMS-PP Commands
# ============================================================================

@cli.group()
def ota():
    """OTA SMS-PP envelope management commands"""
    pass


@ota.command('clfdb')
@click.argument('target_aid')
@click.argument('operation', type=click.Choice(['LOCK', 'UNLOCK', 'TERMINATE', 'MAKE_SELECTABLE']))
@click.option('--template', default='clfdb_lock', help='OTA template name')
@click.option('--keyset', required=True, help='Keyset name for encryption/MAC')
@click.option('--value-set', default='production', help='Value set containing keyset')
@click.pass_context
def create_clfdb_ota(ctx, target_aid: str, operation: str, template: str, keyset: str, value_set: str):
    """Create OTA SMS-PP envelope for CLFDB operation"""
    cli_obj = ctx.obj['cli']
    
    try:
        db_manager = DatabaseManager()
        ota_manager = OTAManager(db_manager)
        
        # Validate AID
        if not ota_manager.validate_aid(target_aid):
            cli_obj.print_error("Invalid AID format (must be 5-16 bytes in hex)")
            return
        
        # Create OTA message
        message = ota_manager.create_clfdb_sms_pp(template, target_aid, operation, keyset, value_set)
        
        cli_obj.print_success(f"Created CLFDB OTA message for {operation} operation")
        print(f"\nMessage Details:")
        print(f"  Target AID: {target_aid}")
        print(f"  Operation: {operation}")
        print(f"  Message ID: {message.id}")
        print(f"  SMS TPDU: {message.sms_tpdu}")
        print(f"  UDH: {message.udh}")
        print(f"  User Data: {message.user_data}")
        
    except Exception as e:
        cli_obj.print_error(f"Error creating CLFDB OTA: {e}")


@ota.command('custom')
@click.argument('target_aid')
@click.argument('apdu')
@click.option('--template', default='clfdb_lock', help='OTA template name')
@click.option('--keyset', required=True, help='Keyset name for encryption/MAC')
@click.option('--value-set', default='production', help='Value set containing keyset')
@click.pass_context
def create_custom_ota(ctx, target_aid: str, apdu: str, template: str, keyset: str, value_set: str):
    """Create OTA SMS-PP envelope with custom APDU"""
    cli_obj = ctx.obj['cli']
    
    try:
        db_manager = DatabaseManager()
        ota_manager = OTAManager(db_manager)
        
        # Validate AID and APDU
        if not ota_manager.validate_aid(target_aid):
            cli_obj.print_error("Invalid AID format (must be 5-16 bytes in hex)")
            return
        
        try:
            bytes.fromhex(apdu)
        except ValueError:
            cli_obj.print_error("Invalid APDU format (must be hex)")
            return
        
        # Create OTA message
        message = ota_manager.create_custom_ota_command(template, target_aid, apdu, keyset, value_set)
        
        cli_obj.print_success(f"Created custom OTA message")
        print(f"\nMessage Details:")
        print(f"  Target AID: {target_aid}")
        print(f"  Custom APDU: {apdu}")
        print(f"  Message ID: {message.id}")
        print(f"  SMS TPDU: {message.sms_tpdu}")
        
    except Exception as e:
        cli_obj.print_error(f"Error creating custom OTA: {e}")


@ota.command('list')
@click.option('--status', help='Filter by status')
@click.option('--target-aid', help='Filter by target AID')
@click.pass_context
def list_ota_messages(ctx, status: str, target_aid: str):
    """List OTA messages"""
    cli_obj = ctx.obj['cli']
    
    try:
        db_manager = DatabaseManager()
        messages = db_manager.get_ota_messages(status=status, target_aid=target_aid)
        
        if messages:
            cli_obj.print_success(f"Found {len(messages)} OTA message(s):")
            
            table_data = []
            for msg in messages:
                table_data.append([
                    msg.id,
                    msg.target_aid,
                    msg.operation,
                    msg.status,
                    msg.created_at[:19],  # Show date/time without microseconds
                    msg.sms_tpdu[:20] + "..." if len(msg.sms_tpdu) > 20 else msg.sms_tpdu
                ])
            
            print(tabulate(table_data,
                         headers=['ID', 'Target AID', 'Operation', 'Status', 'Created', 'SMS TPDU'],
                         tablefmt='grid'))
        else:
            cli_obj.print_warning("No OTA messages found")
    except Exception as e:
        cli_obj.print_error(f"Error listing OTA messages: {e}")


@ota.command('templates')
@click.option('--type', help='Filter by template type')
@click.pass_context
def list_ota_templates(ctx, type: str):
    """List available OTA templates"""
    cli_obj = ctx.obj['cli']
    
    try:
        db_manager = DatabaseManager()
        templates = db_manager.get_ota_templates(template_type=type)
        
        if templates:
            cli_obj.print_success(f"Found {len(templates)} OTA template(s):")
            
            table_data = []
            for tmpl in templates:
                table_data.append([
                    tmpl.name,
                    tmpl.template_type,
                    tmpl.spi,
                    tmpl.tar,
                    tmpl.description[:40] + "..." if len(tmpl.description) > 40 else tmpl.description
                ])
            
            print(tabulate(table_data,
                         headers=['Name', 'Type', 'SPI', 'TAR', 'Description'],
                         tablefmt='grid'))
        else:
            cli_obj.print_warning("No OTA templates found")
    except Exception as e:
        cli_obj.print_error(f"Error listing OTA templates: {e}")


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)
