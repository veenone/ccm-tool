"""
Advanced example demonstrating secure channel operations and security domain management.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from smartcard_manager import SmartcardManager, APDUCommand
from globalplatform import GlobalPlatformManager
from secure_channel import SecureChannelManager, KeySet
from config_manager import ConfigManager
from visualization import SecurityDomainVisualizer
from smartcard.util import toHexString


def demonstrate_secure_operations():
    """Demonstrate secure channel and security domain operations"""
    
    # Initialize components
    config_manager = ConfigManager()
    sc_manager = SmartcardManager()
    gp_manager = GlobalPlatformManager(sc_manager)
    secure_channel = SecureChannelManager(sc_manager)
    visualizer = SecurityDomainVisualizer()
    
    try:
        # List and connect to reader
        readers = sc_manager.list_readers()
        if not readers:
            print("No PC/SC readers found!")
            return
        
        print(f"Connecting to reader: {readers[0]}")
        if not sc_manager.connect_to_reader(readers[0]):
            print("Failed to connect to reader")
            return
        
        # Select Card Manager
        if not gp_manager.select_card_manager():
            print("Failed to select Card Manager")
            return
        
        print("Card Manager selected successfully")
        
        # Get card information
        print("\n=== Card Information ===")
        card_info = gp_manager.get_card_info()
        for key, value in card_info.items():
            print(f"{key}: {value}")
        
        # List current state
        print("\n=== Current Security Domains ===")
        domains = gp_manager.list_security_domains()
        for domain in domains:
            print(f"  {domain}")
        
        print("\n=== Current Applications ===")
        applications = gp_manager.list_applications()
        for app in applications:
            print(f"  {app}")
        
        # Try to establish secure channel
        print("\n=== Establishing Secure Channel ===")
        
        # Try different keysets
        keyset_names = ['default_scp03', 'default_scp02', 'test_keyset']
        secure_channel_established = False
        
        for keyset_name in keyset_names:
            keyset = config_manager.get_keyset(keyset_name)
            if keyset:
                print(f"Trying keyset: {keyset_name} ({keyset.protocol})")
                
                if secure_channel.establish_secure_channel(keyset, security_level=1):
                    print(f"✓ Secure channel established with {keyset_name}")
                    secure_channel_established = True
                    break
                else:
                    print(f"✗ Failed with {keyset_name}")
        
        if not secure_channel_established:
            print("Could not establish secure channel with any keyset")
            print("Continuing with basic operations...")
        
        # Demonstrate secure operations (if secure channel is active)
        if secure_channel_established:
            print("\n=== Secure Operations ===")
            
            # Example: Create a new security domain
            new_sd_aid = bytes.fromhex("A000000151DEAD01")
            print(f"Creating new SSD with AID: {toHexString(new_sd_aid)}")
            
            try:
                if gp_manager.create_security_domain(new_sd_aid, "SSD", 0x80):
                    print("✓ Security domain created successfully")
                    
                    # Refresh domain list
                    domains = gp_manager.list_security_domains()
                    print("Updated security domains:")
                    for domain in domains:
                        print(f"  {domain}")
                else:
                    print("✗ Failed to create security domain")
            except Exception as e:
                print(f"✗ Error creating security domain: {e}")
            
            # Example: CLFDB operations
            if domains:
                target_domain = domains[-1]  # Use last domain
                print(f"\nDemonstrating CLFDB on: {toHexString(target_domain.aid)}")
                
                # Lock the domain
                try:
                    if gp_manager.perform_clfdb(target_domain.aid, "lock"):
                        print("✓ Domain locked successfully")
                        
                        # Unlock it
                        if gp_manager.perform_clfdb(target_domain.aid, "unlock"):
                            print("✓ Domain unlocked successfully")
                        else:
                            print("✗ Failed to unlock domain")
                    else:
                        print("✗ Failed to lock domain")
                except Exception as e:
                    print(f"✗ CLFDB error: {e}")
            
            # Close secure channel
            secure_channel.close_secure_channel()
            print("Secure channel closed")
        
        # Generate comprehensive visualizations
        print("\n=== Generating Visualizations ===")
        
        # Refresh data for visualization
        final_domains = gp_manager.list_security_domains()
        final_applications = gp_manager.list_applications()
        
        if final_domains or final_applications:
            output_files = visualizer.generate_all_visualizations(final_domains, final_applications)
            print(f"Generated {len(output_files)} visualization files:")
            for file_path in output_files:
                if os.path.exists(file_path):
                    print(f"  • {file_path}")
        else:
            print("No data available for visualization")
        
        # Summary report
        print("\n=== Summary Report ===")
        print(f"Total Security Domains: {len(final_domains)}")
        print(f"Total Applications: {len(final_applications)}")
        print(f"Secure Channel Used: {secure_channel_established}")
        
        # Detailed breakdown
        domain_types = {}
        for domain in final_domains:
            domain_types[domain.domain_type] = domain_types.get(domain.domain_type, 0) + 1
        
        print("\nDomain Type Breakdown:")
        for domain_type, count in domain_types.items():
            print(f"  {domain_type}: {count}")
        
        # Lifecycle state analysis
        lifecycle_states = {}
        for domain in final_domains:
            lc_name = domain.life_cycle.name
            lifecycle_states[lc_name] = lifecycle_states.get(lc_name, 0) + 1
        
        for app in final_applications:
            lc_name = app.life_cycle.name
            lifecycle_states[lc_name] = lifecycle_states.get(lc_name, 0) + 1
        
        print("\nLifecycle State Distribution:")
        for state, count in lifecycle_states.items():
            print(f"  {state}: {count}")
    
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            if secure_channel.is_secure_channel_active():
                secure_channel.close_secure_channel()
        except:
            pass
        
        sc_manager.disconnect_all()
        print("\nDisconnected from all readers")


def demonstrate_keyset_management():
    """Demonstrate keyset configuration management"""
    
    print("\n=== Keyset Management Demo ===")
    
    config_manager = ConfigManager()
    
    # List existing keysets
    print("Existing keysets:")
    for name in config_manager.list_keysets():
        keyset = config_manager.get_keyset(name)
        print(f"  {name}: {keyset.protocol} v{keyset.key_version}")
    
    # Create a new keyset
    new_keyset = KeySet.from_hex(
        enc_hex="000102030405060708090A0B0C0D0E0F",
        mac_hex="101112131415161718191A1B1C1D1E1F",
        dek_hex="202122232425262728292A2B2C2D2E2F",
        key_version=5,
        protocol="SCP03"
    )
    
    config_manager.add_keyset("demo_keyset", new_keyset)
    print("Added new demo keyset")
    
    # Save configuration
    config_manager.save_keysets()
    print("Configuration saved")
    
    # List security domain templates
    print("\nSecurity Domain Templates:")
    for name in config_manager.list_security_domain_templates():
        template = config_manager.get_security_domain_template(name)
        print(f"  {name}: {template}")


if __name__ == "__main__":
    print("Advanced Smartcard Management Demo")
    print("==================================")
    
    try:
        demonstrate_keyset_management()
        demonstrate_secure_operations()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
