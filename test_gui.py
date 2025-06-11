#!/usr/bin/env python3
"""
Simple GUI test script to verify CustomTkinter works correctly.
"""

import customtkinter as ctk

def main():
    # Set appearance mode and color theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Create the main window
    root = ctk.CTk()
    root.title("Smartcard Management Tool - Test")
    root.geometry("600x400")
    
    # Create a label
    label = ctk.CTkLabel(root, 
                        text="🎉 GUI Test Successful!\n\nThe CustomTkinter framework is working correctly.\nYou can now run the full GUI application:\n\nuv run python gui_app.py", 
                        font=ctk.CTkFont(size=16))
    label.pack(pady=40)
    
    # Create a button to close
    button = ctk.CTkButton(root, text="Close Test", command=root.destroy)
    button.pack(pady=20)
    
    # Start the GUI
    root.mainloop()
    print("✅ GUI test completed successfully!")

if __name__ == "__main__":
    main()
