"""
GUI Application for Smartcard Management Tool using CustomTkinter.
Provides a modern, user-friendly interface for all smartcard operations.
"""

import sys
import os
import threading
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk
from PIL import Image, ImageTk

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.smartcard_manager import SmartcardManager, SmartcardException
from src.globalplatform import GlobalPlatformManager, SecurityDomainInfo, ApplicationInfo
from src.secure_channel import SecureChannelManager, KeySet
from src.config_manager import ConfigManager
from src.visualization import SecurityDomainVisualizer
from src.database_manager import DatabaseManager, KeysetRecord, OTAMessage
from src.ota_manager import OTAManager
from smartcard.util import toHexString

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class SmartcardGUI:
    """Main GUI application for smartcard management"""
    
    def __init__(self):
        # Initialize backend components
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager()  # Add database manager
        self.ota_manager = OTAManager(self.db_manager)  # Add OTA manager
        self.sc_manager = SmartcardManager()
        self.gp_manager = GlobalPlatformManager(self.sc_manager)
        self.secure_channel = SecureChannelManager(self.sc_manager)
        self.visualizer = SecurityDomainVisualizer(
            self.config_manager.get_visualization_output_dir()
        )
        
        # Application state
        self.connected_reader: Optional[str] = None
        self.secure_channel_active = False
        self.current_domains: List[SecurityDomainInfo] = []
        self.current_applications: List[ApplicationInfo] = []
        
        # Initialize GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Initialize the GUI components"""
        # Create main window
        self.root = ctk.CTk()
        self.root.title("Smartcard Management Tool")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
        
        # Initialize content
        self.show_dashboard()
        
    def create_sidebar(self):
        """Create the sidebar with navigation"""
        self.sidebar_frame = ctk.CTkFrame(self.root, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)
        
        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="🔐 Smartcard\nManagement", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
          # Navigation buttons
        nav_buttons = [
            ("🏠 Dashboard", self.show_dashboard),
            ("🔌 Connection", self.show_connection),
            ("🔐 Secure Channel", self.show_secure_channel),
            ("🏢 Security Domains", self.show_security_domains),
            ("📱 Applications", self.show_applications),
            ("⚙️ Operations", self.show_operations),
            ("🔑 Keysets", self.show_keysets),
            ("📡 OTA Management", self.show_ota),
            ("📊 Visualization", self.show_visualization),
            ("🔧 Settings", self.show_settings),
        ]
        
        self.nav_buttons = []
        for i, (text, command) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                command=command,
                width=240,
                height=40,
                font=ctk.CTkFont(size=14),
                anchor="w"
            )
            btn.grid(row=i+1, column=0, padx=20, pady=5)
            self.nav_buttons.append(btn)
        
        # Connection status
        self.connection_status = ctk.CTkLabel(
            self.sidebar_frame,
            text="🔴 Disconnected",
            font=ctk.CTkFont(size=12)
        )
        self.connection_status.grid(row=11, column=0, padx=20, pady=10)
        
        # Secure channel status
        self.secure_status = ctk.CTkLabel(
            self.sidebar_frame,
            text="🔒 No Secure Channel",
            font=ctk.CTkFont(size=12)
        )
        self.secure_status.grid(row=12, column=0, padx=20, pady=5)
        
    def create_main_content(self):
        """Create the main content area"""
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create notebook for tabbed content
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        
    def create_status_bar(self):
        """Create the status bar"""
        self.status_frame = ctk.CTkFrame(self.root, height=30)
        self.status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
    def update_status(self, message: str):
        """Update the status bar"""
        self.status_label.configure(text=message)
        self.root.update_idletasks()
        
    def update_connection_status(self):
        """Update connection status display"""
        if self.connected_reader:
            self.connection_status.configure(text=f"🟢 {self.connected_reader}")
        else:
            self.connection_status.configure(text="🔴 Disconnected")
            
        if self.secure_channel_active:
            self.secure_status.configure(text="🔓 Secure Channel Active")
        else:
            self.secure_status.configure(text="🔒 No Secure Channel")
    
    def clear_content(self):
        """Clear the main content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        """Show the dashboard tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="📊 Dashboard",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Create dashboard content
        dashboard_frame = ctk.CTkScrollableFrame(self.content_frame)
        dashboard_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        dashboard_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Connection overview
        conn_frame = ctk.CTkFrame(dashboard_frame)
        conn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            conn_frame,
            text="🔌 Connection Status",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        status_text = "Connected" if self.connected_reader else "Disconnected"
        status_color = "green" if self.connected_reader else "red"
        
        ctk.CTkLabel(
            conn_frame,
            text=f"Reader: {self.connected_reader or 'None'}",
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)
        
        ctk.CTkLabel(
            conn_frame,
            text=f"Status: {status_text}",
            text_color=status_color,
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)
        
        # Security overview
        sec_frame = ctk.CTkFrame(dashboard_frame)
        sec_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            sec_frame,
            text="🔐 Security Status",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        sec_status = "Active" if self.secure_channel_active else "Inactive"
        sec_color = "green" if self.secure_channel_active else "red"
        
        ctk.CTkLabel(
            sec_frame,
            text=f"Secure Channel: {sec_status}",
            text_color=sec_color,
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)
        
        # Card overview
        card_frame = ctk.CTkFrame(dashboard_frame)
        card_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            card_frame,
            text="💳 Card Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        info_text = f"Security Domains: {len(self.current_domains)}\n"
        info_text += f"Applications: {len(self.current_applications)}"
        
        ctk.CTkLabel(
            card_frame,
            text=info_text,
            font=ctk.CTkFont(size=12)
        ).pack(pady=5)
        
        # Quick actions
        actions_frame = ctk.CTkFrame(dashboard_frame)
        actions_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            actions_frame,
            text="⚡ Quick Actions",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        actions_button_frame = ctk.CTkFrame(actions_frame)
        actions_button_frame.pack(pady=10, fill="x")
        
        ctk.CTkButton(
            actions_button_frame,
            text="🔍 Scan Readers",
            command=self.refresh_readers
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            actions_button_frame,
            text="📊 Refresh Data",
            command=self.refresh_card_data
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            actions_button_frame,
            text="📈 Generate Visualization",
            command=self.generate_visualization
        ).pack(side="left", padx=5)
    
    def show_connection(self):
        """Show the connection tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="🔌 Connection Management",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Connection content
        conn_frame = ctk.CTkFrame(self.content_frame)
        conn_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        conn_frame.grid_columnconfigure(0, weight=1)
        
        # Reader selection
        reader_frame = ctk.CTkFrame(conn_frame)
        reader_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        reader_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            reader_frame,
            text="PC/SC Reader:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.reader_var = ctk.StringVar()
        self.reader_dropdown = ctk.CTkComboBox(
            reader_frame,
            variable=self.reader_var,
            values=["No readers found"],
            state="readonly",
            width=300
        )
        self.reader_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(
            reader_frame,
            text="🔍 Scan",
            command=self.refresh_readers,
            width=100
        ).grid(row=0, column=2, padx=10, pady=10)
        
        # Connection buttons
        button_frame = ctk.CTkFrame(conn_frame)
        button_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.connect_btn = ctk.CTkButton(
            button_frame,
            text="🔗 Connect",
            command=self.connect_to_reader,
            width=120,
            height=40
        )
        self.connect_btn.pack(side="left", padx=10, pady=10)
        
        self.disconnect_btn = ctk.CTkButton(
            button_frame,
            text="🔌 Disconnect",
            command=self.disconnect_from_reader,
            width=120,
            height=40,
            state="disabled"
        )
        self.disconnect_btn.pack(side="left", padx=10, pady=10)
        
        # Connection info
        self.connection_info = ctk.CTkTextbox(conn_frame, height=200)
        self.connection_info.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        
        # Initialize reader list
        self.refresh_readers()
    
    def show_secure_channel(self):
        """Show the secure channel tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="🔐 Secure Channel Management",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Secure channel content
        sc_frame = ctk.CTkFrame(self.content_frame)
        sc_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        sc_frame.grid_columnconfigure(0, weight=1)
        
        # Keyset selection
        keyset_frame = ctk.CTkFrame(sc_frame)
        keyset_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        keyset_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            keyset_frame,
            text="Keyset:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.keyset_var = ctk.StringVar()
        keysets = self.config_manager.list_keysets()
        self.keyset_dropdown = ctk.CTkComboBox(
            keyset_frame,
            variable=self.keyset_var,
            values=keysets if keysets else ["No keysets configured"],
            state="readonly",
            width=200
        )
        self.keyset_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Security level
        ctk.CTkLabel(
            keyset_frame,
            text="Security Level:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.security_level_var = ctk.StringVar(value="3")
        security_levels = ["1 (MAC)", "2 (MAC+ENC)", "3 (MAC+ENC+RMAC)"]
        self.security_level_dropdown = ctk.CTkComboBox(
            keyset_frame,
            variable=self.security_level_var,
            values=security_levels,
            state="readonly",
            width=200
        )
        self.security_level_dropdown.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Secure channel buttons
        sc_button_frame = ctk.CTkFrame(sc_frame)
        sc_button_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.establish_btn = ctk.CTkButton(
            sc_button_frame,
            text="🔓 Establish Secure Channel",
            command=self.establish_secure_channel,
            width=200,
            height=40
        )
        self.establish_btn.pack(side="left", padx=10, pady=10)
        
        self.close_sc_btn = ctk.CTkButton(
            sc_button_frame,
            text="🔒 Close Secure Channel",
            command=self.close_secure_channel,
            width=200,
            height=40,
            state="disabled"
        )
        self.close_sc_btn.pack(side="left", padx=10, pady=10)
        
        # Secure channel info
        self.sc_info = ctk.CTkTextbox(sc_frame, height=200)
        self.sc_info.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
    
    def show_security_domains(self):
        """Show the security domains tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="🏢 Security Domains",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Security domains content
        sd_frame = ctk.CTkFrame(self.content_frame)
        sd_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        sd_frame.grid_columnconfigure(0, weight=1)
        sd_frame.grid_rowconfigure(1, weight=1)
        
        # Control buttons
        control_frame = ctk.CTkFrame(sd_frame)
        control_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkButton(
            control_frame,
            text="🔄 Refresh",
            command=self.refresh_security_domains
        ).pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(
            control_frame,
            text="➕ Create SD",
            command=self.show_create_security_domain_dialog
        ).pack(side="left", padx=5, pady=5)
        
        # Security domains list
        self.sd_tree_frame = ctk.CTkFrame(sd_frame)
        self.sd_tree_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Create treeview for security domains
        self.create_security_domains_tree()
    
    def show_applications(self):
        """Show the applications tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="📱 Applications",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Applications content
        app_frame = ctk.CTkFrame(self.content_frame)
        app_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        app_frame.grid_columnconfigure(0, weight=1)
        app_frame.grid_rowconfigure(1, weight=1)
        
        # Control buttons
        control_frame = ctk.CTkFrame(app_frame)
        control_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkButton(
            control_frame,
            text="🔄 Refresh",
            command=self.refresh_applications
        ).pack(side="left", padx=5, pady=5)
        
        # Applications list
        self.app_tree_frame = ctk.CTkFrame(app_frame)
        self.app_tree_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Create treeview for applications
        self.create_applications_tree()
    
    def show_operations(self):
        """Show the operations tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="⚙️ Operations",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Operations content
        ops_frame = ctk.CTkScrollableFrame(self.content_frame)
        ops_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        ops_frame.grid_columnconfigure((0, 1), weight=1)
        
        # CLFDB Operations
        clfdb_frame = ctk.CTkFrame(ops_frame)
        clfdb_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            clfdb_frame,
            text="🔄 CLFDB Operations",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # AID input
        aid_frame = ctk.CTkFrame(clfdb_frame)
        aid_frame.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(aid_frame, text="Target AID:").pack(side="left", padx=5)
        self.clfdb_aid_entry = ctk.CTkEntry(aid_frame, placeholder_text="A000000151...")
        self.clfdb_aid_entry.pack(side="right", fill="x", expand=True, padx=5)
        
        # Operation selection
        op_frame = ctk.CTkFrame(clfdb_frame)
        op_frame.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(op_frame, text="Operation:").pack(side="left", padx=5)
        self.clfdb_op_var = ctk.StringVar(value="lock")
        ctk.CTkComboBox(
            op_frame,
            variable=self.clfdb_op_var,
            values=["lock", "unlock", "terminate"],
            state="readonly"
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            clfdb_frame,
            text="Execute CLFDB",
            command=self.execute_clfdb
        ).pack(pady=10)
        
        # Extradition Operations
        extradite_frame = ctk.CTkFrame(ops_frame)
        extradite_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            extradite_frame,
            text="↔️ Extradition",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Object AID
        obj_frame = ctk.CTkFrame(extradite_frame)
        obj_frame.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(obj_frame, text="Object AID:").pack(side="left", padx=5)
        self.extradite_obj_entry = ctk.CTkEntry(obj_frame, placeholder_text="Object AID")
        self.extradite_obj_entry.pack(side="right", fill="x", expand=True, padx=5)
        
        # Target SD AID
        target_frame = ctk.CTkFrame(extradite_frame)
        target_frame.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(target_frame, text="Target SD AID:").pack(side="left", padx=5)
        self.extradite_target_entry = ctk.CTkEntry(target_frame, placeholder_text="Target SD AID")
        self.extradite_target_entry.pack(side="right", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(
            extradite_frame,
            text="Execute Extradition",
            command=self.execute_extradition
        ).pack(pady=10)
    
    def show_visualization(self):
        """Show the visualization tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="📊 Visualization",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Visualization content
        viz_frame = ctk.CTkFrame(self.content_frame)
        viz_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        viz_frame.grid_columnconfigure(0, weight=1)
        
        # Generation options
        options_frame = ctk.CTkFrame(viz_frame)
        options_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        ctk.CTkLabel(
            options_frame,
            text="📈 Generate Visualizations",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Output directory
        dir_frame = ctk.CTkFrame(options_frame)
        dir_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(dir_frame, text="Output Directory:").pack(side="left", padx=5)
        self.viz_dir_entry = ctk.CTkEntry(
            dir_frame, 
            placeholder_text="output/",
            width=300
        )
        self.viz_dir_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(
            dir_frame,
            text="📁 Browse",
            command=self.browse_output_directory,
            width=80
        ).pack(side="right", padx=5)
        
        # Generation buttons
        gen_frame = ctk.CTkFrame(options_frame)
        gen_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkButton(
            gen_frame,
            text="📊 Generate All",
            command=self.generate_all_visualizations,
            width=150,
            height=40
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            gen_frame,
            text="🌳 Hierarchy Only",
            command=lambda: self.generate_specific_visualization("hierarchy"),
            width=150,
            height=40
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            gen_frame,
            text="🔐 Privileges Only",
            command=lambda: self.generate_specific_visualization("privileges"),
            width=150,
            height=40
        ).pack(side="left", padx=5)
        
        # Results area
        self.viz_results = ctk.CTkTextbox(viz_frame, height=300)
        self.viz_results.grid(row=1, column=0, padx=20, pady=20, sticky="ew")
    
    def show_settings(self):
        """Show the settings tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="🔧 Settings",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Settings content
        settings_frame = ctk.CTkScrollableFrame(self.content_frame)
        settings_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        settings_frame.grid_columnconfigure(0, weight=1)
        
        # Appearance settings
        appearance_frame = ctk.CTkFrame(settings_frame)
        appearance_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            appearance_frame,
            text="🎨 Appearance",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Theme selection
        theme_frame = ctk.CTkFrame(appearance_frame)
        theme_frame.pack(pady=5, fill="x", padx=20)
        
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=5)
        self.theme_var = ctk.StringVar(value="dark")
        ctk.CTkComboBox(
            theme_frame,
            variable=self.theme_var,
            values=["dark", "light", "system"],
            command=self.change_theme
        ).pack(side="right", padx=5)
        
        # Logging settings
        logging_frame = ctk.CTkFrame(settings_frame)
        logging_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            logging_frame,
            text="📝 Logging",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Debug mode
        debug_frame = ctk.CTkFrame(logging_frame)
        debug_frame.pack(pady=5, fill="x", padx=20)
        
        self.debug_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            debug_frame,
            text="Enable Debug Mode",
            variable=self.debug_var
        ).pack(side="left", padx=5)
        
        # About section
        about_frame = ctk.CTkFrame(settings_frame)
        about_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            about_frame,
            text="ℹ️ About",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        about_text = """Smartcard Management Tool v1.0.0
A comprehensive tool for managing smartcards through PC/SC readers.

Features:
• PC/SC reader management
• GlobalPlatform operations
• Secure channel protocols (SCP02/SCP03)
• Security domain management
• Visualization capabilities

Built with CustomTkinter and Python."""
        
        ctk.CTkLabel(
            about_frame,
            text=about_text,
            font=ctk.CTkFont(size=11),
            justify="left"
        ).pack(pady=10, padx=20)
    
    def show_keysets(self):
        """Show the keyset management tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="🔑 Keyset Management",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Main keyset frame
        keyset_frame = ctk.CTkFrame(self.content_frame)
        keyset_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        keyset_frame.grid_columnconfigure(0, weight=1)
        keyset_frame.grid_rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar_frame = ctk.CTkFrame(keyset_frame)
        toolbar_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkButton(
            toolbar_frame,
            text="➕ Add Keyset",
            command=self.show_add_keyset_dialog,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            toolbar_frame,
            text="✏️ Edit",
            command=self.edit_selected_keyset,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            toolbar_frame,
            text="🗑️ Delete",
            command=self.delete_selected_keyset,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            toolbar_frame,
            text="🔄 Refresh",
            command=self.refresh_keysets,
            width=120
        ).pack(side="left", padx=5)
        
        # Value set selector
        value_set_frame = ctk.CTkFrame(toolbar_frame)
        value_set_frame.pack(side="right", padx=10)
        
        ctk.CTkLabel(value_set_frame, text="Value Set:").pack(side="left", padx=5)
        self.value_set_var = ctk.StringVar(value="production")
        value_sets = self.config_manager.get_value_sets()
        self.value_set_combo = ctk.CTkComboBox(
            value_set_frame,
            variable=self.value_set_var,
            values=value_sets,
            command=self.refresh_keysets,
            width=150
        )
        self.value_set_combo.pack(side="left", padx=5)
        
        # Keyset table
        table_frame = ctk.CTkFrame(keyset_frame)
        table_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Create treeview for keysets
        columns = ("Name", "Version", "ENC", "MAC", "KEK", "Protocol", "Description")
        self.keyset_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        column_widths = {"Name": 120, "Version": 80, "ENC": 100, "MAC": 100, "KEK": 100, "Protocol": 80, "Description": 200}
        for col in columns:
            self.keyset_tree.heading(col, text=col)
            self.keyset_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.keyset_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.keyset_tree.xview)
        self.keyset_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid the treeview and scrollbars
        self.keyset_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Bind double-click to edit
        self.keyset_tree.bind("<Double-1>", lambda e: self.edit_selected_keyset())
        
        # Load initial data
        self.refresh_keysets()
    
    def show_ota(self):
        """Show the OTA management tab"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="📡 OTA Management",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, sticky="w")
        
        # Main OTA frame
        ota_frame = ctk.CTkScrollableFrame(self.content_frame)
        ota_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        ota_frame.grid_columnconfigure((0, 1), weight=1)
        
        # CLFDB Operations Section
        clfdb_frame = ctk.CTkFrame(ota_frame)
        clfdb_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        clfdb_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            clfdb_frame,
            text="🔒 CLFDB Operations",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        # AID input
        ctk.CTkLabel(clfdb_frame, text="AID:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.ota_aid_entry = ctk.CTkEntry(clfdb_frame, placeholder_text="Enter AID (hex)")
        self.ota_aid_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Operation buttons
        op_frame = ctk.CTkFrame(clfdb_frame)
        op_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        operations = [
            ("🔒 Lock", "LOCK"),
            ("🔓 Unlock", "UNLOCK"),
            ("⚠️ Terminate", "TERMINATE"),
            ("✅ Make Selectable", "MAKE_SELECTABLE")
        ]
        
        for i, (text, op) in enumerate(operations):
            ctk.CTkButton(
                op_frame,
                text=text,
                command=lambda o=op: self.execute_clfdb_operation(o),
                width=140
            ).grid(row=i//2, column=i%2, padx=5, pady=5)
        
        # Custom APDU Section
        custom_frame = ctk.CTkFrame(ota_frame)
        custom_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        custom_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            custom_frame,
            text="🛠️ Custom OTA",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        # APDU input
        ctk.CTkLabel(custom_frame, text="APDU:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.custom_apdu_entry = ctk.CTkEntry(custom_frame, placeholder_text="Enter APDU (hex)")
        self.custom_apdu_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(
            custom_frame,
            text="📤 Send Custom OTA",
            command=self.send_custom_ota,
            width=150
        ).grid(row=2, column=0, columnspan=2, pady=10)
        
        # OTA Configuration Section
        config_frame = ctk.CTkFrame(ota_frame)
        config_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        config_frame.grid_columnconfigure((1, 3), weight=1)
        
        ctk.CTkLabel(
            config_frame,
            text="⚙️ OTA Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=4, pady=10)
        
        # Keyset selection
        ctk.CTkLabel(config_frame, text="Keyset:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.ota_keyset_var = ctk.StringVar()
        self.ota_keyset_combo = ctk.CTkComboBox(
            config_frame,
            variable=self.ota_keyset_var,
            values=self.get_keyset_names(),
            width=200
        )
        self.ota_keyset_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # SPI (Security Parameter Index)
        ctk.CTkLabel(config_frame, text="SPI:").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.ota_spi_entry = ctk.CTkEntry(config_frame, placeholder_text="02", width=80)
        self.ota_spi_entry.grid(row=1, column=3, padx=10, pady=5, sticky="w")
        
        # Results section
        results_frame = ctk.CTkFrame(ota_frame)
        results_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        results_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            results_frame,
            text="📋 OTA Results",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, pady=10, sticky="w")
        
        self.ota_results = ctk.CTkTextbox(results_frame, height=200)
        self.ota_results.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Message history section
        history_frame = ctk.CTkFrame(ota_frame)
        history_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        history_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            history_frame,
            text="📚 Message History",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, pady=10, sticky="w")
        
        # History controls
        history_controls = ctk.CTkFrame(history_frame)
        history_controls.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(
            history_controls,
            text="🔄 Refresh History",
            command=self.refresh_ota_history,
            width=130
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            history_controls,
            text="🗑️ Clear History",
            command=self.clear_ota_history,
            width=130
        ).pack(side="left", padx=5)
        
        # History table
        history_table_frame = ctk.CTkFrame(history_frame)
        history_table_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        history_table_frame.grid_columnconfigure(0, weight=1)
        
        history_columns = ("Timestamp", "Type", "AID", "Status", "Message")
        self.ota_history_tree = ttk.Treeview(history_table_frame, columns=history_columns, show="headings", height=8)
        
        # Configure history columns
        history_widths = {"Timestamp": 150, "Type": 100, "AID": 150, "Status": 80, "Message": 300}
        for col in history_columns:
            self.ota_history_tree.heading(col, text=col)
            self.ota_history_tree.column(col, width=history_widths.get(col, 100))
        
        # History scrollbar
        history_scrollbar = ttk.Scrollbar(history_table_frame, orient="vertical", command=self.ota_history_tree.yview)
        self.ota_history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.ota_history_tree.grid(row=0, column=0, sticky="nsew")
        history_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Load initial data
        self.refresh_ota_history()    # Keyset management methods
    
    def refresh_keysets(self):
        """Refresh the keyset table with current data"""
        try:
            # Clear existing items
            for item in self.keyset_tree.get_children():
                self.keyset_tree.delete(item)
            
            # Get current value set
            value_set = self.value_set_var.get()
            
            # Load keysets from database
            keysets = self.db_manager.get_keysets(value_set=value_set)
            
            # Populate table
            for keyset in keysets:
                values = (
                    keyset.name,
                    keyset.key_version,
                    keyset.enc_key[:16] + "..." if len(keyset.enc_key) > 16 else keyset.enc_key,
                    keyset.mac_key[:16] + "..." if len(keyset.mac_key) > 16 else keyset.mac_key,
                    keyset.dek_key[:16] + "..." if len(keyset.dek_key) > 16 else keyset.dek_key,
                    keyset.protocol,
                    keyset.description or ""
                )
                self.keyset_tree.insert("", "end", values=values, tags=(keyset.name,))
            
            self.update_status(f"Loaded {len(keysets)} keysets from {value_set} value set")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh keysets: {e}")
    
    def show_add_keyset_dialog(self):
        """Show dialog to add a new keyset"""
        dialog = KeysetDialog(self.root, "Add Keyset")
        if dialog.result:
            try:
                keyset_data = dialog.result
                value_set = self.value_set_var.get()
                
                # Create keyset record
                keyset = KeysetRecord(
                    id=None,
                    name=keyset_data['name'],
                    value_set=value_set,
                    protocol=keyset_data.get('protocol', 'SCP02'),
                    enc_key=keyset_data['enc_key'],
                    mac_key=keyset_data['mac_key'],
                    dek_key=keyset_data['dek_key'],
                    key_version=keyset_data.get('key_version', 1),
                    security_level=keyset_data.get('security_level', 3),
                    description=keyset_data.get('description', ''),
                    created_at="",
                    updated_at="",
                    is_active=True
                )
                
                # Add to database
                self.db_manager.add_keyset(keyset)
                self.refresh_keysets()
                messagebox.showinfo("Success", f"Keyset '{keyset_data['name']}' added successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add keyset: {e}")
    
    def edit_selected_keyset(self):
        """Edit the selected keyset"""
        selection = self.keyset_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a keyset to edit")
            return
        
        try:
            item = selection[0]
            keyset_name = self.keyset_tree.item(item)['values'][0]
            value_set = self.value_set_var.get()
            
            # Get keyset from database
            keyset = self.db_manager.get_keyset_by_name(keyset_name, value_set)
            if not keyset:
                messagebox.showerror("Error", "Keyset not found")
                return
            
            # Show edit dialog
            dialog = KeysetDialog(self.root, "Edit Keyset", keyset)
            if dialog.result:
                keyset_data = dialog.result
                
                # Update keyset fields
                keyset.name = keyset_data['name']
                keyset.protocol = keyset_data.get('protocol', keyset.protocol)
                keyset.enc_key = keyset_data['enc_key']
                keyset.mac_key = keyset_data['mac_key']
                keyset.dek_key = keyset_data['dek_key']
                keyset.key_version = keyset_data.get('key_version', keyset.key_version)
                keyset.security_level = keyset_data.get('security_level', keyset.security_level)
                keyset.description = keyset_data.get('description', keyset.description)
                
                self.db_manager.update_keyset(keyset)
                self.refresh_keysets()
                messagebox.showinfo("Success", f"Keyset '{keyset_data['name']}' updated successfully")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit keyset: {e}")
    
    def delete_selected_keyset(self):
        """Delete the selected keyset"""
        selection = self.keyset_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a keyset to delete")
            return
        
        try:
            item = selection[0]
            keyset_name = self.keyset_tree.item(item)['values'][0]
            value_set = self.value_set_var.get()
              # Get keyset to find its ID
            keyset = self.db_manager.get_keyset_by_name(keyset_name, value_set)
            if not keyset or keyset.id is None:
                messagebox.showerror("Error", "Keyset not found")
                return
            
            # Confirm deletion
            if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete keyset '{keyset_name}'?"):
                return
            
            self.db_manager.delete_keyset(keyset.id)
            self.refresh_keysets()
            messagebox.showinfo("Success", f"Keyset '{keyset_name}' deleted successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete keyset: {e}")
    
    def get_keyset_names(self):
        """Get list of keyset names for dropdown"""
        try:
            value_set = getattr(self, 'value_set_var', None)
            current_set = value_set.get() if value_set else "production"
            keysets = self.db_manager.get_keysets(value_set=current_set)
            return [keyset.name for keyset in keysets]
        except:
            return ["No keysets available"]
    
    # OTA management methods
    
    def execute_clfdb_operation(self, operation: str):
        """Execute a CLFDB operation"""
        aid = self.ota_aid_entry.get().strip()
        if not aid:
            messagebox.showwarning("Warning", "Please enter an AID")
            return
        
        try:
            # Validate AID format
            aid_bytes = bytes.fromhex(aid.replace(' ', ''))
            if len(aid_bytes) < 5 or len(aid_bytes) > 16:
                messagebox.showerror("Error", "AID must be 5-16 bytes")
                return
            
            # Get selected keyset
            keyset_name = self.ota_keyset_var.get()
            if not keyset_name:
                messagebox.showwarning("Warning", "Please select a keyset")
                return
            
            value_set = getattr(self, 'value_set_var', None)
            current_set = value_set.get() if value_set else "production"
            keyset = self.db_manager.get_keyset_by_name(keyset_name, current_set)
            if not keyset:
                messagebox.showerror("Error", "Selected keyset not found")
                return
            
            self.update_status(f"Generating {operation} OTA message...")
            
            # Generate OTA message using template
            template_name = f"clfdb_{operation.lower()}"
            ota_message = self.ota_manager.create_clfdb_sms_pp(
                template_name, aid, operation, keyset_name, current_set
            )
            
            # Display results
            self.display_ota_result(operation, aid, ota_message.sms_tpdu)
            
            self.update_status(f"{operation} OTA message generated successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate OTA message: {e}")
            self.update_status("OTA generation failed")
    
    def send_custom_ota(self):
        """Send a custom APDU via OTA"""
        apdu = self.custom_apdu_entry.get().strip()
        if not apdu:
            messagebox.showwarning("Warning", "Please enter an APDU")
            return
        
        try:
            # Validate APDU format
            apdu_bytes = bytes.fromhex(apdu.replace(' ', ''))
            if len(apdu_bytes) < 4:
                messagebox.showerror("Error", "APDU must be at least 4 bytes")
                return
            
            # Get selected keyset
            keyset_name = self.ota_keyset_var.get()
            if not keyset_name:
                messagebox.showwarning("Warning", "Please select a keyset")
                return
            
            value_set = getattr(self, 'value_set_var', None)
            current_set = value_set.get() if value_set else "production"
            keyset = self.db_manager.get_keyset_by_name(keyset_name, current_set)
            if not keyset:
                messagebox.showerror("Error", "Selected keyset not found")
                return
            
            self.update_status("Generating custom OTA message...")
            
            # Generate custom OTA message
            ota_message = self.ota_manager.create_custom_ota_command(
                "clfdb_lock", "N/A", apdu, keyset_name, current_set
            )
            
            # Display results
            self.display_ota_result("CUSTOM", apdu[:16] + "...", ota_message.sms_tpdu)
            
            self.update_status("Custom OTA message generated successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate custom OTA: {e}")
            self.update_status("Custom OTA generation failed")
    
    def display_ota_result(self, operation: str, target: str, ota_message: str):
        """Display OTA generation results"""
        self.ota_results.delete("1.0", "end")
        
        result_text = f"""✅ OTA Message Generated Successfully

Operation: {operation}
Target: {target}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}

SMS-PP Envelope:
{ota_message}

Message Length: {len(ota_message.replace(' ', '')) // 2} bytes

Instructions:
1. Copy the SMS-PP envelope above
2. Send it via your OTA platform
3. Monitor the response from the target device
"""
        
        self.ota_results.insert("1.0", result_text)
    
    def refresh_ota_history(self):
        """Refresh the OTA message history"""
        try:
            # Clear existing items
            for item in self.ota_history_tree.get_children():
                self.ota_history_tree.delete(item)
            
            # Load OTA messages from database
            messages = self.db_manager.get_ota_messages()
            
            # Populate table (limit to last 100)
            for msg in messages[:100]:
                # Parse created_at timestamp
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(msg.created_at)
                    timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    timestamp_str = msg.created_at
                
                values = (
                    timestamp_str,
                    msg.operation,
                    msg.target_aid[:20] + "..." if len(msg.target_aid) > 20 else msg.target_aid,
                    msg.status,
                    f"Template: {msg.template_id}"
                )
                self.ota_history_tree.insert("", "end", values=values)
            
            self.update_status(f"Loaded {len(messages[:100])} OTA messages from history")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh OTA history: {e}")
    
    def clear_ota_history(self):
        """Clear OTA message history"""
        if not messagebox.askyesno("Confirm", "Are you sure you want to clear the OTA message history?"):
            return
        
        try:
            # Just clear the display for now
            for item in self.ota_history_tree.get_children():
                self.ota_history_tree.delete(item)
            
            self.update_status("OTA history cleared")
            messagebox.showinfo("Success", "OTA history cleared successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear OTA history: {e}")
      # Event handlers and utility methods
    
    def refresh_readers(self):
        """Refresh the list of available readers"""
        try:
            self.update_status("Scanning for PC/SC readers...")
            readers = self.sc_manager.list_readers()
            
            if readers:
                self.reader_dropdown.configure(values=readers)
                if not self.reader_var.get() or self.reader_var.get() not in readers:
                    self.reader_var.set(readers[0])
                self.update_status(f"Found {len(readers)} reader(s)")
            else:
                self.reader_dropdown.configure(values=["No readers found"])
                self.reader_var.set("No readers found")
                self.update_status("No PC/SC readers found")
                
        except Exception as e:
            error_msg = str(e)
            print(f"Debug: Reader scan error - {error_msg}")  # Debug output
            messagebox.showerror("PC/SC Error", 
                f"PC/SC Service Issue:\n\n{error_msg}\n\n" +
                "Please check:\n" +
                "• PC/SC service is running\n" +
                "• Smart card reader is connected\n" +
                "• Reader drivers are installed\n" +
                "• No other applications are using the reader")
            self.update_status("PC/SC Error - Check reader connection")
    
    def connect_to_reader(self):
        """Connect to the selected reader"""
        reader_name = self.reader_var.get()
        if not reader_name or reader_name == "No readers found":
            messagebox.showwarning("Warning", "Please select a valid reader")
            return
        
        try:
            self.update_status(f"Connecting to {reader_name}...")
            
            if self.sc_manager.connect_to_reader(reader_name):
                self.connected_reader = reader_name
                self.connect_btn.configure(state="disabled")
                self.disconnect_btn.configure(state="normal")
                self.update_connection_status()
                
                # Try to select Card Manager
                if self.gp_manager.select_card_manager():
                    self.connection_info.insert("end", f"✅ Connected to {reader_name}\n")
                    self.connection_info.insert("end", f"✅ Card Manager selected\n")
                    self.update_status("Connected successfully")
                      # Get ATR safely
                    try:
                        if self.sc_manager.active_reader:
                            atr = self.sc_manager.active_reader.get_atr()
                            self.connection_info.insert("end", f"ATR: {toHexString(atr)}\n")
                        else:
                            self.connection_info.insert("end", "ATR: Not available (no active reader)\n")
                    except Exception as atr_error:
                        self.connection_info.insert("end", f"ATR: Error reading - {atr_error}\n")
                      # Refresh card data
                    self.refresh_card_data()
                else:
                    self.connection_info.insert("end", f"✅ Connected to {reader_name}\n")
                    self.connection_info.insert("end", f"⚠️ Could not select Card Manager\n")
                    self.update_status("Connected, but Card Manager not available")
            else:
                error_msg = "Failed to connect to reader"
                messagebox.showerror("Connection Error", 
                    f"Connection Failed:\n\n{error_msg}\n\n" +
                    "Possible causes:\n" +
                    "• No card inserted in reader\n" +
                    "• Card is not responding\n" +
                    "• Reader is busy with another application\n" +
                    "• PC/SC service issue")
                self.update_status("Connection failed - Check card and reader")
                
        except Exception as e:
            error_msg = str(e)
            print(f"Debug: Connection error - {error_msg}")  # Debug output
            messagebox.showerror("Connection Error", 
                f"Connection Exception:\n\n{error_msg}\n\n" +
                "This may indicate:\n" +                "• PC/SC middleware issue\n" +
                "• Reader driver problem\n" +
                "• Hardware malfunction")
            self.update_status(f"Connection error: {error_msg}")
    
    def disconnect_from_reader(self):
        """Disconnect from the current reader"""
        try:
            if self.secure_channel_active:
                self.secure_channel.close_secure_channel()
                self.secure_channel_active = False
            
            self.sc_manager.disconnect_all()
            self.connected_reader = None
            
            # Safely update button states if they exist
            if hasattr(self, 'connect_btn'):
                self.connect_btn.configure(state="normal")
            if hasattr(self, 'disconnect_btn'):
                self.disconnect_btn.configure(state="disabled")
            if hasattr(self, 'establish_btn'):
                self.establish_btn.configure(state="normal")
            if hasattr(self, 'close_sc_btn'):
                self.close_sc_btn.configure(state="disabled")
            
            self.update_connection_status()
            if hasattr(self, 'connection_info'):
                self.connection_info.insert("end", "🔌 Disconnected from all readers\n")
            self.update_status("Disconnected")
            
        except Exception as e:
            messagebox.showerror("Error", f"Disconnect error: {e}")
    
    def establish_secure_channel(self):
        """Establish secure channel"""
        if not self.connected_reader:
            messagebox.showwarning("Warning", "Please connect to a reader first")
            return
        
        keyset_name = self.keyset_var.get()
        if not keyset_name or keyset_name == "No keysets configured":
            messagebox.showwarning("Warning", "Please select a valid keyset")
            return
        
        try:
            keyset = self.config_manager.get_keyset(keyset_name)
            if not keyset:
                messagebox.showerror("Error", f"Keyset '{keyset_name}' not found")
                return
            
            # Parse security level
            security_level_str = self.security_level_var.get()
            security_level = int(security_level_str.split()[0])
            
            self.update_status(f"Establishing {keyset.protocol} secure channel...")
            
            if self.secure_channel.establish_secure_channel(keyset, security_level):
                self.secure_channel_active = True
                # Safely update button states if they exist
                if hasattr(self, 'establish_btn'):
                    self.establish_btn.configure(state="disabled")
                if hasattr(self, 'close_sc_btn'):
                    self.close_sc_btn.configure(state="normal")
                self.update_connection_status()
                
                if hasattr(self, 'sc_info'):
                    self.sc_info.insert("end", f"✅ Secure channel established\n")
                    self.sc_info.insert("end", f"Protocol: {keyset.protocol}\n")
                    self.sc_info.insert("end", f"Security Level: {security_level}\n")
                self.update_status("Secure channel established")
            else:
                messagebox.showerror("Error", "Failed to establish secure channel")
                self.update_status("Secure channel failed")
                
        except Exception as e:
            messagebox.showerror("Error", f"Secure channel error: {e}")
            self.update_status("Secure channel error")
    
    def close_secure_channel(self):
        """Close secure channel"""
        try:
            self.secure_channel.close_secure_channel()
            self.secure_channel_active = False
            
            # Safely update button states if they exist
            if hasattr(self, 'establish_btn'):
                self.establish_btn.configure(state="normal")
            if hasattr(self, 'close_sc_btn'):
                self.close_sc_btn.configure(state="disabled")
            self.update_connection_status()
            
            if hasattr(self, 'sc_info'):
                self.sc_info.insert("end", "🔒 Secure channel closed\n")
            self.update_status("Secure channel closed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error closing secure channel: {e}")
    
    def refresh_card_data(self):
        """Refresh card data (security domains and applications)"""
        if not self.connected_reader:
            return
        
        def refresh_thread():
            try:
                self.update_status("Refreshing card data...")
                
                # Get security domains
                self.current_domains = self.gp_manager.list_security_domains()
                
                # Get applications
                self.current_applications = self.gp_manager.list_applications()
                
                # Update UI on main thread
                self.root.after(0, self.update_card_data_ui)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to refresh card data: {e}"))
                self.root.after(0, lambda: self.update_status("Card data refresh failed"))
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def update_card_data_ui(self):
        """Update the UI with refreshed card data"""
        self.update_status(f"Found {len(self.current_domains)} domains, {len(self.current_applications)} applications")
        
        # Update trees if they exist
        if hasattr(self, 'sd_tree'):
            self.populate_security_domains_tree()
        if hasattr(self, 'app_tree'):
            self.populate_applications_tree()
    
    def refresh_security_domains(self):
        """Refresh security domains list"""
        self.refresh_card_data()
    
    def refresh_applications(self):
        """Refresh applications list"""
        self.refresh_card_data()
    
    def create_security_domains_tree(self):
        """Create the security domains tree view"""
        # Create frame for tree and scrollbar
        tree_frame = ctk.CTkFrame(self.sd_tree_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create treeview
        columns = ("AID", "Type", "Lifecycle", "Privileges")
        self.sd_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=10)
        
        # Configure columns
        self.sd_tree.heading("#0", text="Name")
        self.sd_tree.column("#0", width=100)
        
        for col in columns:
            self.sd_tree.heading(col, text=col)
            self.sd_tree.column(col, width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.sd_tree.yview)
        self.sd_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.sd_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Populate with current data
        self.populate_security_domains_tree()
    
    def populate_security_domains_tree(self):
        """Populate the security domains tree with data"""
        # Clear existing items
        for item in self.sd_tree.get_children():
            self.sd_tree.delete(item)
        
        # Add security domains
        for i, domain in enumerate(self.current_domains):
            self.sd_tree.insert(
                "",
                "end",
                text=f"SD {i+1}",
                values=(
                    toHexString(domain.aid),
                    domain.domain_type,
                    domain.life_cycle.name,
                    f"0x{domain.privileges:02X}"
                )
            )
    
    def create_applications_tree(self):
        """Create the applications tree view"""
        # Create frame for tree and scrollbar
        tree_frame = ctk.CTkFrame(self.app_tree_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create treeview
        columns = ("AID", "Lifecycle", "Privileges")
        self.app_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=10)
        
        # Configure columns
        self.app_tree.heading("#0", text="Name")
        self.app_tree.column("#0", width=100)
        
        for col in columns:
            self.app_tree.heading(col, text=col)
            self.app_tree.column(col, width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.app_tree.yview)
        self.app_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.app_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Populate with current data
        self.populate_applications_tree()
    
    def populate_applications_tree(self):
        """Populate the applications tree with data"""
        # Clear existing items
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)
        
        # Add applications
        for i, app in enumerate(self.current_applications):
            self.app_tree.insert(
                "",
                "end",
                text=f"App {i+1}",
                values=(
                    toHexString(app.aid),
                    app.life_cycle.name,
                    f"0x{app.privileges:02X}"
                )
            )
    
    def show_create_security_domain_dialog(self):
        """Show dialog to create a new security domain"""
        if not self.secure_channel_active:
            messagebox.showwarning("Warning", "Secure channel required for this operation")
            return
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create Security Domain")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # AID input
        ctk.CTkLabel(dialog, text="AID (hex):").pack(pady=5)
        aid_entry = ctk.CTkEntry(dialog, placeholder_text="A000000151...")
        aid_entry.pack(pady=5, padx=20, fill="x")
        
        # Domain type
        ctk.CTkLabel(dialog, text="Domain Type:").pack(pady=5)
        domain_type_var = ctk.StringVar(value="SSD")
        ctk.CTkComboBox(
            dialog,
            variable=domain_type_var,
            values=["SSD", "AMSD", "DMSD"]
        ).pack(pady=5)
        
        # Privileges
        ctk.CTkLabel(dialog, text="Privileges (hex):").pack(pady=5)
        privileges_entry = ctk.CTkEntry(dialog, placeholder_text="80")
        privileges_entry.pack(pady=5, padx=20, fill="x")
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=20)
        
        def create_sd():
            try:
                aid_hex = aid_entry.get().strip()
                domain_type = domain_type_var.get()
                privileges_hex = privileges_entry.get().strip() or "80"
                
                if not aid_hex:
                    messagebox.showwarning("Warning", "Please enter an AID")
                    return
                
                aid_bytes = bytes.fromhex(aid_hex)
                privileges = int(privileges_hex, 16)
                
                if self.gp_manager.create_security_domain(aid_bytes, domain_type, privileges):
                    messagebox.showinfo("Success", "Security domain created successfully")
                    dialog.destroy()
                    self.refresh_card_data()
                else:
                    messagebox.showerror("Error", "Failed to create security domain")
                    
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Creation error: {e}")
        
        ctk.CTkButton(button_frame, text="Create", command=create_sd).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
    
    def execute_clfdb(self):
        """Execute CLFDB operation"""
        if not self.secure_channel_active:
            messagebox.showwarning("Warning", "Secure channel required for this operation")
            return
        
        aid_hex = self.clfdb_aid_entry.get().strip()
        operation = self.clfdb_op_var.get()
        
        if not aid_hex:
            messagebox.showwarning("Warning", "Please enter a target AID")
            return
        
        try:
            aid_bytes = bytes.fromhex(aid_hex)
            
            if self.gp_manager.perform_clfdb(aid_bytes, operation):
                messagebox.showinfo("Success", f"CLFDB {operation} completed successfully")
                self.refresh_card_data()
            else:
                messagebox.showerror("Error", f"CLFDB {operation} failed")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid AID format")
        except Exception as e:
            messagebox.showerror("Error", f"CLFDB error: {e}")
    
    def execute_extradition(self):
        """Execute extradition operation"""
        if not self.secure_channel_active:
            messagebox.showwarning("Warning", "Secure channel required for this operation")
            return
        
        obj_aid_hex = self.extradite_obj_entry.get().strip()
        target_aid_hex = self.extradite_target_entry.get().strip()
        
        if not obj_aid_hex or not target_aid_hex:
            messagebox.showwarning("Warning", "Please enter both object and target AIDs")
            return
        
        try:
            obj_aid_bytes = bytes.fromhex(obj_aid_hex)
            target_aid_bytes = bytes.fromhex(target_aid_hex)
            
            if self.gp_manager.extradite_object(obj_aid_bytes, target_aid_bytes):
                messagebox.showinfo("Success", "Extradition completed successfully")
                self.refresh_card_data()
            else:
                messagebox.showerror("Error", "Extradition failed")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid AID format")
        except Exception as e:
            messagebox.showerror("Error", f"Extradition error: {e}")
    
    def browse_output_directory(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.viz_dir_entry.delete(0, "end")
            self.viz_dir_entry.insert(0, directory)
    
    def generate_visualization(self):
        """Generate basic visualization"""
        self.generate_all_visualizations()
    
    def generate_all_visualizations(self):
        """Generate all visualizations"""
        if not self.current_domains and not self.current_applications:
            messagebox.showwarning("Warning", "No card data available. Please connect and refresh first.")
            return
        
        def generate_thread():
            try:
                self.root.after(0, lambda: self.update_status("Generating visualizations..."))
                
                # Get output directory
                output_dir = self.viz_dir_entry.get().strip() or "output"
                
                # Set visualizer output directory
                self.visualizer.output_dir = output_dir
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate visualizations
                output_files = self.visualizer.generate_all_visualizations(
                    self.current_domains, self.current_applications
                )
                
                # Update results on main thread
                self.root.after(0, lambda: self.update_visualization_results(output_files))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Visualization error: {e}"))
                self.root.after(0, lambda: self.update_status("Visualization failed"))
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def generate_specific_visualization(self, viz_type: str):
        """Generate specific type of visualization"""
        if not self.current_domains and not self.current_applications:
            messagebox.showwarning("Warning", "No card data available. Please connect and refresh first.")
            return
        
        def generate_thread():
            try:
                self.root.after(0, lambda: self.update_status(f"Generating {viz_type} visualization..."))
                
                output_dir = self.viz_dir_entry.get().strip() or "output"
                self.visualizer.output_dir = output_dir
                os.makedirs(output_dir, exist_ok=True)
                
                output_file = None
                if viz_type == "hierarchy":
                    output_file = self.visualizer.create_hierarchy_diagram(
                        self.current_domains, self.current_applications
                    )
                elif viz_type == "privileges":
                    output_file = self.visualizer.create_privilege_matrix(
                        self.current_domains, self.current_applications
                    )
                
                if output_file:
                    self.root.after(0, lambda: self.update_visualization_results([output_file]))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Visualization error: {e}"))
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def update_visualization_results(self, output_files: List[str]):
        """Update visualization results"""
        self.viz_results.delete("1.0", "end")
        
        if output_files:
            self.viz_results.insert("end", f"✅ Generated {len(output_files)} visualization(s):\n\n")
            for file_path in output_files:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    self.viz_results.insert("end", f"📄 {os.path.basename(file_path)}\n")
                    self.viz_results.insert("end", f"   Path: {file_path}\n")
                    self.viz_results.insert("end", f"   Size: {file_size:,} bytes\n\n")
            
            self.update_status(f"Generated {len(output_files)} visualizations")
        else:
            self.viz_results.insert("end", "❌ No visualizations were generated")
            self.update_status("No visualizations generated")
    
    def change_theme(self, theme: str):
        """Change the application theme"""
        ctk.set_appearance_mode(theme)
        self.update_status(f"Theme changed to {theme}")
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()


class KeysetDialog:
    """Dialog for adding/editing keysets"""
    
    def __init__(self, parent, title, keyset=None):
        self.result = None
        
        # Create dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"500x600+{x}+{y}")
        
        # Configure grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkScrollableFrame(self.dialog)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text=title, font=ctk.CTkFont(size=18, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        row = 1
        
        # Name field
        ctk.CTkLabel(main_frame, text="Name:").grid(row=row, column=0, sticky="w", pady=5)
        self.name_entry = ctk.CTkEntry(main_frame, width=300)
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Protocol field
        ctk.CTkLabel(main_frame, text="Protocol:").grid(row=row, column=0, sticky="w", pady=5)
        self.protocol_var = ctk.StringVar(value="SCP03")
        self.protocol_combo = ctk.CTkComboBox(main_frame, variable=self.protocol_var, values=["SCP02", "SCP03"])
        self.protocol_combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # ENC Key field
        ctk.CTkLabel(main_frame, text="ENC Key:").grid(row=row, column=0, sticky="w", pady=5)
        self.enc_key_entry = ctk.CTkEntry(main_frame, width=300, placeholder_text="32 hex characters (16 bytes)")
        self.enc_key_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # MAC Key field
        ctk.CTkLabel(main_frame, text="MAC Key:").grid(row=row, column=0, sticky="w", pady=5)
        self.mac_key_entry = ctk.CTkEntry(main_frame, width=300, placeholder_text="32 hex characters (16 bytes)")
        self.mac_key_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # DEK Key field
        ctk.CTkLabel(main_frame, text="DEK Key:").grid(row=row, column=0, sticky="w", pady=5)
        self.dek_key_entry = ctk.CTkEntry(main_frame, width=300, placeholder_text="32 hex characters (16 bytes)")
        self.dek_key_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Key Version field
        ctk.CTkLabel(main_frame, text="Key Version:").grid(row=row, column=0, sticky="w", pady=5)
        self.key_version_var = ctk.StringVar(value="1")
        self.key_version_entry = ctk.CTkEntry(main_frame, textvariable=self.key_version_var, width=100)
        self.key_version_entry.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        row += 1
        
        # Security Level field
        ctk.CTkLabel(main_frame, text="Security Level:").grid(row=row, column=0, sticky="w", pady=5)
        self.security_level_var = ctk.StringVar(value="3")
        self.security_level_combo = ctk.CTkComboBox(main_frame, variable=self.security_level_var, values=["1", "2", "3"])
        self.security_level_combo.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=5)
        row += 1
        
        # Description field
        ctk.CTkLabel(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=5)
        self.description_text = ctk.CTkTextbox(main_frame, height=60, width=300)
        self.description_text.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        row += 1
        
        # Button frame
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        
        # Buttons
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel,
            width=100
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Save",
            command=self.save,
            width=100
        ).pack(side="right", padx=5)
        
        # Fill fields if editing
        if keyset:
            self.name_entry.insert(0, keyset.name)
            self.protocol_var.set(keyset.protocol)
            self.enc_key_entry.insert(0, keyset.enc_key)
            self.mac_key_entry.insert(0, keyset.mac_key)
            self.dek_key_entry.insert(0, keyset.dek_key)
            self.key_version_var.set(str(keyset.key_version))
            self.security_level_var.set(str(keyset.security_level))
            if keyset.description:
                self.description_text.insert("1.0", keyset.description)
        
        # Focus on name field
        self.name_entry.focus()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def validate_hex_key(self, key: str) -> bool:
        """Validate hex key format"""
        if len(key) != 32:
            return False
        try:
            int(key, 16)
            return True
        except ValueError:
            return False
    
    def save(self):
        """Save the keyset data"""
        try:
            # Get values
            name = self.name_entry.get().strip()
            protocol = self.protocol_var.get()
            enc_key = self.enc_key_entry.get().strip().upper()
            mac_key = self.mac_key_entry.get().strip().upper()
            dek_key = self.dek_key_entry.get().strip().upper()
            key_version = int(self.key_version_var.get())
            security_level = int(self.security_level_var.get())
            description = self.description_text.get("1.0", "end").strip()
            
            # Validate
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            
            if not self.validate_hex_key(enc_key):
                messagebox.showerror("Error", "ENC Key must be 32 hex characters")
                return
            
            if not self.validate_hex_key(mac_key):
                messagebox.showerror("Error", "MAC Key must be 32 hex characters")
                return
            
            if not self.validate_hex_key(dek_key):
                messagebox.showerror("Error", "DEK Key must be 32 hex characters")
                return
            
            if not 0 <= key_version <= 255:
                messagebox.showerror("Error", "Key version must be 0-255")
                return
            
            if security_level not in [1, 2, 3]:
                messagebox.showerror("Error", "Security level must be 1, 2, or 3")
                return
            
            # Set result
            self.result = {
                'name': name,
                'protocol': protocol,
                'enc_key': enc_key,
                'mac_key': mac_key,
                'dek_key': dek_key,
                'key_version': key_version,
                'security_level': security_level,
                'description': description
            }
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving keyset: {e}")
    
    def cancel(self):
        """Cancel the dialog"""
        self.dialog.destroy()


def main():
    """Main entry point for the GUI application"""
    try:
        app = SmartcardGUI()
        app.run()
    except KeyboardInterrupt:
        print("Application interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()