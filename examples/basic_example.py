"""
Example script demonstrating basic smartcard operations.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from smartcard_manager import SmartcardManager
from globalplatform import GlobalPlatformManager
from secure_channel import SecureChannelManager
from config_manager import ConfigManager
from visualization import SecurityDomainVisualizer


def main():
    """Basic example of smartcard operations"""
    
    # Initialize managers
    config_manager = ConfigManager()
    sc_manager = SmartcardManager()
    gp_manager = GlobalPlatformManager(sc_manager)
    secure_channel = SecureChannelManager(sc_manager)
    visualizer = SecurityDomainVisualizer()
    
    try:
        # List available readers
        print("Available readers:")
        readers = sc_manager.list_readers()
        for i, reader in enumerate(readers, 1):
            print(f"  {i}. {reader}")
        
        if not readers:
            print("No readers found!")
            return
        
        # Connect to first reader
        reader_name = readers[0]
        print(f"\nConnecting to: {reader_name}")
        
        if sc_manager.connect_to_reader(reader_name):
            print("Connected successfully!")
            
            # Select Card Manager
            if gp_manager.select_card_manager():
                print("Card Manager selected")
                
                # List security domains
                print("\nSecurity Domains:")
                domains = gp_manager.list_security_domains()
                for domain in domains:
                    print(f"  {domain}")
                
                # List applications
                print("\nApplications:")
                applications = gp_manager.list_applications()
                for app in applications:
                    print(f"  {app}")
                
                # Try to establish secure channel if keyset available
                keyset = config_manager.get_keyset('default_scp03')
                if keyset:
                    print(f"\nTrying to establish secure channel with SCP03...")
                    if secure_channel.establish_secure_channel(keyset):
                        print("Secure channel established!")
                        
                        # Close secure channel
                        secure_channel.close_secure_channel()
                        print("Secure channel closed")
                    else:
                        print("Failed to establish secure channel")
                
                # Generate visualizations if data available
                if domains or applications:
                    print("\nGenerating visualizations...")
                    output_files = visualizer.generate_all_visualizations(domains, applications)
                    print(f"Generated {len(output_files)} visualization files")
            
            else:
                print("Failed to select Card Manager")
        else:
            print("Failed to connect to reader")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Cleanup
        sc_manager.disconnect_all()
        print("\nDisconnected from all readers")


if __name__ == "__main__":
    main()
