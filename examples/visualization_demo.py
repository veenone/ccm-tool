"""
Example demonstrating visualization capabilities of the tool.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from globalplatform import SecurityDomainInfo, ApplicationInfo, LifeCycleState
from visualization import SecurityDomainVisualizer


def create_sample_data():
    """Create sample security domains and applications for demonstration"""
    
    # Sample security domains
    security_domains = [
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151000000"),
            life_cycle=LifeCycleState.SECURED,
            privileges=0xA0,
            domain_type="ISD",
            associated_applications=[]
        ),
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151100000"),
            life_cycle=LifeCycleState.SELECTABLE,
            privileges=0xC0,
            domain_type="SSD",
            associated_applications=[]
        ),
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151200000"),
            life_cycle=LifeCycleState.PERSONALIZED,
            privileges=0x80,
            domain_type="AMSD",
            associated_applications=[]
        ),
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151300000"),
            life_cycle=LifeCycleState.SELECTABLE,
            privileges=0xE0,
            domain_type="DMSD",
            associated_applications=[]
        ),
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151400000"),
            life_cycle=LifeCycleState.LOCKED,
            privileges=0x80,
            domain_type="SSD",
            associated_applications=[]
        )
    ]
    
    # Sample applications
    applications = [
        ApplicationInfo(
            aid=bytes.fromhex("A0000001515555AA"),
            life_cycle=LifeCycleState.SELECTABLE,
            privileges=0x00
        ),
        ApplicationInfo(
            aid=bytes.fromhex("A0000001515555BB"),
            life_cycle=LifeCycleState.PERSONALIZED,
            privileges=0x00
        ),
        ApplicationInfo(
            aid=bytes.fromhex("A0000001515555CC"),
            life_cycle=LifeCycleState.INSTALLED,
            privileges=0x00
        ),
        ApplicationInfo(
            aid=bytes.fromhex("A0000001515555DD"),
            life_cycle=LifeCycleState.BLOCKED,
            privileges=0x00
        ),
        ApplicationInfo(
            aid=bytes.fromhex("A0000001515555EE"),
            life_cycle=LifeCycleState.LOCKED,
            privileges=0x00
        ),
        ApplicationInfo(
            aid=bytes.fromhex("A0000001515555FF"),
            life_cycle=LifeCycleState.TERMINATED,
            privileges=0x00
        )
    ]
    
    return security_domains, applications


def demonstrate_visualizations():
    """Demonstrate all visualization capabilities"""
    
    print("Creating sample smartcard data...")
    security_domains, applications = create_sample_data()
    
    print(f"Sample data created:")
    print(f"  • {len(security_domains)} security domains")
    print(f"  • {len(applications)} applications")
    
    # Initialize visualizer
    visualizer = SecurityDomainVisualizer("output/demo")
    
    print("\nGenerating visualizations...")
    
    try:
        # Generate hierarchy diagram
        print("  • Creating hierarchy diagram...")
        hierarchy_path = visualizer.create_hierarchy_diagram(
            security_domains, applications, "demo_hierarchy.png"
        )
        print(f"    ✓ Saved to: {hierarchy_path}")
        
        # Generate network graph
        print("  • Creating network graph...")
        network_path = visualizer.create_network_graph(
            security_domains, applications, "demo_network.png"
        )
        print(f"    ✓ Saved to: {network_path}")
        
        # Generate privilege matrix
        print("  • Creating privilege matrix...")
        matrix_path = visualizer.create_privilege_matrix(
            security_domains, applications, "demo_privileges.png"
        )
        print(f"    ✓ Saved to: {matrix_path}")
        
        # Generate lifecycle timeline
        print("  • Creating lifecycle timeline...")
        timeline_path = visualizer.create_lifecycle_timeline(
            security_domains, applications, "demo_lifecycle.png"
        )
        print(f"    ✓ Saved to: {timeline_path}")
        
        # Generate all visualizations at once
        print("  • Generating complete visualization set...")
        all_files = visualizer.generate_all_visualizations(security_domains, applications)
        print(f"    ✓ Generated {len(all_files)} files")
        
        print(f"\n✓ All visualizations completed successfully!")
        print(f"Output directory: {visualizer.output_dir}")
        
        # Summary of generated files
        print("\nGenerated files:")
        for file_path in all_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  • {os.path.basename(file_path)} ({file_size:,} bytes)")
        
    except Exception as e:
        print(f"✗ Error generating visualizations: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_custom_visualization():
    """Demonstrate custom visualization options"""
    
    print("\n" + "="*50)
    print("Custom Visualization Demo")
    print("="*50)
    
    # Create more complex sample data
    security_domains, applications = create_sample_data()
    
    # Add more diverse lifecycle states
    additional_domains = [
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151500000"),
            life_cycle=LifeCycleState.CARD_LOCKED,
            privileges=0x70,
            domain_type="SSD",
            associated_applications=[]
        ),
        SecurityDomainInfo(
            aid=bytes.fromhex("A000000151600000"),
            life_cycle=LifeCycleState.TERMINATED,
            privileges=0x00,
            domain_type="AMSD",
            associated_applications=[]
        )
    ]
    
    security_domains.extend(additional_domains)
    
    # Custom visualizer with different output directory
    custom_visualizer = SecurityDomainVisualizer("output/custom_demo")
    
    print("Creating custom visualizations...")
    
    try:
        # Create visualizations with custom names
        files = []
        
        files.append(custom_visualizer.create_hierarchy_diagram(
            security_domains, applications, "custom_hierarchy_detailed.png"
        ))
        
        files.append(custom_visualizer.create_privilege_matrix(
            security_domains, applications, "custom_privilege_analysis.png"
        ))
        
        files.append(custom_visualizer.create_lifecycle_timeline(
            security_domains, applications, "custom_lifecycle_distribution.png"
        ))
        
        print(f"✓ Custom visualizations created:")
        for file_path in files:
            if os.path.exists(file_path):
                print(f"  • {file_path}")
        
        # Print detailed analysis
        print(f"\nDetailed Analysis:")
        print(f"  Total Objects: {len(security_domains) + len(applications)}")
        
        # Domain type analysis
        domain_counts = {}
        for domain in security_domains:
            domain_counts[domain.domain_type] = domain_counts.get(domain.domain_type, 0) + 1
        
        print("  Domain Types:")
        for domain_type, count in sorted(domain_counts.items()):
            print(f"    {domain_type}: {count}")
        
        # Lifecycle analysis
        lifecycle_counts = {}
        for domain in security_domains:
            lc_name = domain.life_cycle.name
            lifecycle_counts[lc_name] = lifecycle_counts.get(lc_name, 0) + 1
        
        for app in applications:
            lc_name = app.life_cycle.name
            lifecycle_counts[lc_name] = lifecycle_counts.get(lc_name, 0) + 1
        
        print("  Lifecycle States:")
        for state, count in sorted(lifecycle_counts.items()):
            print(f"    {state}: {count}")
        
        # Privilege analysis
        privilege_summary = {}
        for domain in security_domains:
            priv_key = f"0x{domain.privileges:02X}"
            privilege_summary[priv_key] = privilege_summary.get(priv_key, 0) + 1
        
        print("  Privilege Distribution:")
        for priv, count in sorted(privilege_summary.items()):
            print(f"    {priv}: {count}")
    
    except Exception as e:
        print(f"✗ Error in custom visualization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Smartcard Visualization Demo")
    print("============================")
    
    try:
        demonstrate_visualizations()
        demonstrate_custom_visualization()
        
        print(f"\n🎉 Visualization demo completed!")
        print(f"Check the 'output/' directory for generated files.")
        
    except KeyboardInterrupt:
        print("\n⚠ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
