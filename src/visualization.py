"""
Visualization module for security domains and application hierarchy.
Provides graphical representation of the smartcard structure.
"""

import logging
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
from matplotlib.patches import FancyBboxPatch
import numpy as np
from .globalplatform import SecurityDomainInfo, ApplicationInfo
from smartcard.util import toHexString
import os

logger = logging.getLogger(__name__)


class SecurityDomainVisualizer:
    """Creates visual representations of security domain hierarchies"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Color scheme for different types
        self.colors = {
            'ISD': '#FF6B6B',      # Red for Issuer Security Domain
            'SSD': '#4ECDC4',      # Teal for Supplementary Security Domain
            'AMSD': '#45B7D1',     # Blue for Application Security Domain
            'DMSD': '#96CEB4',     # Green for Delegated Management Security Domain
            'Application': '#FFEAA7',  # Yellow for Applications
            'LoadFile': '#DDA0DD'   # Plum for Load Files
        }
        
        # Lifecycle state colors
        self.lifecycle_colors = {
            0x01: '#90EE90',  # Light Green - OP_READY
            0x03: '#87CEEB',  # Sky Blue - INITIALIZED/INSTALLED
            0x07: '#98FB98',  # Pale Green - SELECTABLE
            0x0F: '#FFE4B5',  # Moccasin - SECURED/PERSONALIZED
            0x7F: '#FFA07A',  # Light Salmon - CARD_LOCKED
            0x83: '#FFB6C1',  # Light Pink - BLOCKED
            0x87: '#F0E68C',  # Khaki - LOCKED
            0xFF: '#D3D3D3'   # Light Gray - TERMINATED
        }
    
    def create_hierarchy_diagram(self, security_domains: List[SecurityDomainInfo], 
                               applications: List[ApplicationInfo], 
                               filename: str = "security_domain_hierarchy.png") -> str:
        """Create a hierarchical diagram of security domains and applications"""
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes for security domains
        for sd in security_domains:
            aid_short = toHexString(sd.aid)[-8:]  # Last 4 bytes for readability
            G.add_node(aid_short, 
                      type=sd.domain_type,
                      full_aid=toHexString(sd.aid),
                      lifecycle=sd.life_cycle.value,
                      privileges=sd.privileges,
                      label=f"{sd.domain_type}\n{aid_short}\nLC:{sd.life_cycle.value:02X}")
        
        # Add nodes for applications
        for app in applications:
            aid_short = toHexString(app.aid)[-8:]
            G.add_node(aid_short,
                      type='Application',
                      full_aid=toHexString(app.aid),
                      lifecycle=app.life_cycle.value,
                      privileges=app.privileges,
                      label=f"APP\n{aid_short}\nLC:{app.life_cycle.value:02X}")
        
        # Create hierarchical layout
        pos = self._create_hierarchical_layout(G, security_domains, applications)
        
        # Create the plot
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        ax.set_title("Security Domain and Application Hierarchy", fontsize=16, fontweight='bold')
        
        # Draw nodes
        for node, (x, y) in pos.items():
            node_data = G.nodes[node]
            node_type = node_data['type']
            
            # Choose color based on type
            color = self.colors.get(node_type, '#CCCCCC')
            
            # Add lifecycle state indicator
            lc_color = self.lifecycle_colors.get(node_data['lifecycle'], '#FFFFFF')
            
            # Create fancy box for the node
            bbox = FancyBboxPatch(
                (x - 0.4, y - 0.3), 0.8, 0.6,
                boxstyle="round,pad=0.1",
                facecolor=color,
                edgecolor='black',
                linewidth=2,
                alpha=0.8
            )
            ax.add_patch(bbox)
            
            # Add lifecycle indicator
            lc_circle = plt.Circle((x + 0.3, y + 0.2), 0.08, 
                                 color=lc_color, ec='black', linewidth=1)
            ax.add_patch(lc_circle)
            
            # Add text
            ax.text(x, y, node_data['label'], 
                   ha='center', va='center', fontsize=8, fontweight='bold')
            
            # Add privilege information
            priv_text = f"Priv: {node_data['privileges']:02X}"
            ax.text(x, y - 0.4, priv_text, 
                   ha='center', va='center', fontsize=6)
        
        # Draw edges (associations)
        for edge in G.edges():
            x1, y1 = pos[edge[0]]
            x2, y2 = pos[edge[1]]
            ax.arrow(x1, y1 - 0.3, x2 - x1, y2 - y1 + 0.6, 
                    head_width=0.05, head_length=0.05, fc='black', ec='black')
        
        # Add legend
        self._add_legend(ax)
        
        # Set axis properties
        ax.set_xlim(-2, 8)
        ax.set_ylim(-6, 2)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Save the plot
        output_path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Hierarchy diagram saved to: {output_path}")
        return output_path
    
    def _create_hierarchical_layout(self, G, security_domains: List[SecurityDomainInfo], 
                                  applications: List[ApplicationInfo]) -> Dict[str, tuple]:
        """Create a hierarchical layout for the graph"""
        pos = {}
        
        # Find ISD (root)
        isd_nodes = [sd for sd in security_domains if sd.domain_type == 'ISD']
        
        if isd_nodes:
            isd_aid = toHexString(isd_nodes[0].aid)[-8:]
            pos[isd_aid] = (3, 0)  # Root at top center
        
        # Position other security domains
        ssd_nodes = [sd for sd in security_domains if sd.domain_type == 'SSD']
        amsd_nodes = [sd for sd in security_domains if sd.domain_type == 'AMSD']
        dmsd_nodes = [sd for sd in security_domains if sd.domain_type == 'DMSD']
        
        # Position SSDs
        for i, sd in enumerate(ssd_nodes):
            aid_short = toHexString(sd.aid)[-8:]
            pos[aid_short] = (i * 2 - 1, -2)
        
        # Position AMSDs
        for i, sd in enumerate(amsd_nodes):
            aid_short = toHexString(sd.aid)[-8:]
            pos[aid_short] = (i * 2 + 1, -3)
        
        # Position DMSDs
        for i, sd in enumerate(dmsd_nodes):
            aid_short = toHexString(sd.aid)[-8:]
            pos[aid_short] = (i * 2 + 3, -2)
        
        # Position applications
        for i, app in enumerate(applications):
            aid_short = toHexString(app.aid)[-8:]
            pos[aid_short] = (i * 1.5 - 2, -5)
        
        return pos
    
    def _add_legend(self, ax):
        """Add legend to the plot"""
        legend_elements = []
        
        # Type legend
        for type_name, color in self.colors.items():
            legend_elements.append(
                patches.Patch(color=color, label=type_name)
            )
        
        # Add some lifecycle state examples
        legend_elements.append(patches.Patch(color='white', label='--- Lifecycle States ---'))
        legend_elements.append(patches.Patch(color=self.lifecycle_colors[0x03], label='Installed (03)'))
        legend_elements.append(patches.Patch(color=self.lifecycle_colors[0x07], label='Selectable (07)'))
        legend_elements.append(patches.Patch(color=self.lifecycle_colors[0x0F], label='Personalized (0F)'))
        legend_elements.append(patches.Patch(color=self.lifecycle_colors[0x87], label='Locked (87)'))
        
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1))
    
    def create_network_graph(self, security_domains: List[SecurityDomainInfo], 
                           applications: List[ApplicationInfo],
                           filename: str = "network_graph.png") -> str:
        """Create a network graph representation"""
        
        G = nx.Graph()
        
        # Add nodes
        node_colors = []
        node_sizes = []
        labels = {}
        
        for sd in security_domains:
            aid_short = toHexString(sd.aid)[-8:]
            G.add_node(aid_short)
            node_colors.append(self.colors[sd.domain_type])
            node_sizes.append(2000 if sd.domain_type == 'ISD' else 1500)
            labels[aid_short] = f"{sd.domain_type}\n{aid_short}"
        
        for app in applications:
            aid_short = toHexString(app.aid)[-8:]
            G.add_node(aid_short)
            node_colors.append(self.colors['Application'])
            node_sizes.append(1000)
            labels[aid_short] = f"APP\n{aid_short}"
        
        # Create layout
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Create plot
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # Draw the network
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=node_sizes, alpha=0.8, ax=ax)
        nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
        nx.draw_networkx_edges(G, pos, alpha=0.6, ax=ax)
        
        ax.set_title("Security Domain Network View", fontsize=16, fontweight='bold')
        ax.axis('off')
        
        # Save plot
        output_path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Network graph saved to: {output_path}")
        return output_path
    
    def create_privilege_matrix(self, security_domains: List[SecurityDomainInfo], 
                              applications: List[ApplicationInfo],
                              filename: str = "privilege_matrix.png") -> str:
        """Create a privilege matrix visualization"""
        
        # Privilege bits
        privilege_names = [
            'Security Domain', 'DAP Verification', 'Delegated Management',
            'Card Lock', 'Card Terminate', 'Card Reset', 'CVM Management', 'Mandated DAP'
        ]
        
        all_objects = []
        all_objects.extend([(f"{sd.domain_type}:{toHexString(sd.aid)[-8:]}", sd.privileges) 
                           for sd in security_domains])
        all_objects.extend([(f"APP:{toHexString(app.aid)[-8:]}", app.privileges) 
                           for app in applications])
        
        if not all_objects:
            logger.warning("No objects to visualize")
            return ""
        
        # Create privilege matrix
        matrix = np.zeros((len(all_objects), 8))
        object_names = []
        
        for i, (name, privileges) in enumerate(all_objects):
            object_names.append(name)
            for bit in range(8):
                if privileges & (0x80 >> bit):
                    matrix[i, bit] = 1
        
        # Create heatmap
        fig, ax = plt.subplots(1, 1, figsize=(12, max(6, len(all_objects) * 0.5)))
        
        im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto')
        
        # Set ticks and labels
        ax.set_xticks(range(8))
        ax.set_xticklabels(privilege_names, rotation=45, ha='right')
        ax.set_yticks(range(len(object_names)))
        ax.set_yticklabels(object_names)
        
        # Add text annotations
        for i in range(len(object_names)):
            for j in range(8):
                text = '✓' if matrix[i, j] else '✗'
                color = 'white' if matrix[i, j] else 'black'
                ax.text(j, i, text, ha='center', va='center', color=color, fontweight='bold')
        
        ax.set_title("Privilege Matrix", fontsize=16, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Privilege Granted')
        
        # Save plot
        output_path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Privilege matrix saved to: {output_path}")
        return output_path
    
    def create_lifecycle_timeline(self, security_domains: List[SecurityDomainInfo], 
                                applications: List[ApplicationInfo],
                                filename: str = "lifecycle_timeline.png") -> str:
        """Create a lifecycle state timeline visualization"""
        
        # Lifecycle order for visualization
        lifecycle_order = [0x01, 0x03, 0x07, 0x0F, 0x83, 0x87, 0x7F, 0xFF]
        lifecycle_names = ['OP_READY', 'INSTALLED', 'SELECTABLE', 'PERSONALIZED', 
                          'BLOCKED', 'LOCKED', 'CARD_LOCKED', 'TERMINATED']
        
        # Count objects in each lifecycle state
        all_objects = []
        all_objects.extend([(sd.domain_type, sd.life_cycle.value) for sd in security_domains])
        all_objects.extend([('Application', app.life_cycle.value) for app in applications])
        
        # Create data for plotting
        types = list(set([obj[0] for obj in all_objects]))
        data = {}
        
        for obj_type in types:
            data[obj_type] = [0] * len(lifecycle_order)
            for _, lc in all_objects:
                if lc in lifecycle_order:
                    idx = lifecycle_order.index(lc)
                    data[obj_type][idx] += 1
        
        # Create stacked bar chart
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        
        x = np.arange(len(lifecycle_names))
        bottom = np.zeros(len(lifecycle_names))
        
        for obj_type in types:
            color = self.colors.get(obj_type, '#CCCCCC')
            ax.bar(x, data[obj_type], bottom=bottom, label=obj_type, color=color, alpha=0.8)
            bottom += data[obj_type]
        
        ax.set_xlabel('Lifecycle State')
        ax.set_ylabel('Number of Objects')
        ax.set_title('Object Distribution by Lifecycle State')
        ax.set_xticks(x)
        ax.set_xticklabels(lifecycle_names, rotation=45, ha='right')
        ax.legend()
        
        # Save plot
        output_path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Lifecycle timeline saved to: {output_path}")
        return output_path
    
    def generate_all_visualizations(self, security_domains: List[SecurityDomainInfo], 
                                  applications: List[ApplicationInfo]) -> List[str]:
        """Generate all visualization types"""
        output_files = []
        
        try:
            output_files.append(self.create_hierarchy_diagram(security_domains, applications))
        except Exception as e:
            logger.error(f"Error creating hierarchy diagram: {e}")
        
        try:
            output_files.append(self.create_network_graph(security_domains, applications))
        except Exception as e:
            logger.error(f"Error creating network graph: {e}")
        
        try:
            output_files.append(self.create_privilege_matrix(security_domains, applications))
        except Exception as e:
            logger.error(f"Error creating privilege matrix: {e}")
        
        try:
            output_files.append(self.create_lifecycle_timeline(security_domains, applications))
        except Exception as e:
            logger.error(f"Error creating lifecycle timeline: {e}")
        
        return output_files
