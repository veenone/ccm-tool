# Smartcard Management Tool

A comprehensive Python-based tool for managing smartcard content through PC/SC readers with full GlobalPlatform support. This tool provides a complete solution for smartcard development, testing, and administration.

## 🚀 Features

### Core Functionality
- **PC/SC Reader Management** - Detect and connect to any PC/SC compatible reader
- **GlobalPlatform Support** - Full GP 2.1.1+ specification compliance
- **Secure Channel Protocols** - SCP02 and SCP03 implementation with configurable security levels
- **Multi-Protocol Support** - Works with T=0 and T=1 protocols

### Security Domain Management
- **Discovery & Enumeration** - List all security domains and applications on card
- **Creation & Configuration** - Create SSD, AMSD, and DMSD security domains
- **Lifecycle Management** - Complete CLFDB operations (lock, unlock, terminate)
- **Extradition Support** - Transfer applications between security domains

### Advanced Features
- **Configurable Keysets** - Flexible keyset management with YAML configuration
- **Visualization Engine** - Generate comprehensive visual reports and diagrams
- **Command-Line Interface** - Full-featured CLI with color output and progress indicators
- **Extensible Architecture** - Modular design for easy customization and extension

### Visualization Capabilities
- **Hierarchy Diagrams** - Security domain and application relationships
- **Network Graphs** - Interactive network representation
- **Privilege Matrix** - Visual privilege analysis
- **Lifecycle Timeline** - State distribution and analysis

## 📋 Requirements

- **Python 3.9+** (updated for modern dependencies)
- **PC/SC Middleware**:
  - Windows: WinSCard (pre-installed)
  - Linux: pcsc-lite (`sudo apt-get install pcscd pcsc-tools`)
  - macOS: PC/SC framework (pre-installed)
- **Compatible Smartcard Reader** (PC/SC compliant)
- **GlobalPlatform Compatible Smartcard**

## ⚡ Quick Installation (UV - Recommended)

### Windows
```batch
# Run the automated UV setup
.\setup_uv.bat
```

### Linux/macOS
```bash
# Run the automated UV setup  
./setup_uv.sh
```

### Manual UV Setup
```bash
# Install UV first (if not already installed)
# Windows (PowerShell): 
curl -LsSf https://astral.sh/uv/install.ps1 | powershell
# Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone project and setup
git clone <repository-url>
cd smartcard-management-tool
uv sync
```

## 🎨 GUI Application (NEW!)

Launch the modern CustomTkinter-based GUI:

```bash
# Start the GUI application
uv run python gui_app.py
```

**GUI Features:**
- 🎨 Modern dark/light theme interface
- 📊 Real-time connection monitoring
- 🔍 Interactive smartcard exploration
- ⚙️ Visual security domain management
- 📈 Built-in visualization generator
- 🔒 Secure channel configuration
- 📱 Responsive sidebar navigation

## 💻 Command Line Interface

### Using UV (Recommended)
```bash
# List available PC/SC readers
uv run python ccm_tool.py list-readers

# Connect to a specific reader
uv run python ccm_tool.py connect "Your Reader Name"

# Get card information
uv run python ccm_tool.py card-info

# Check current status
uv run python ccm_tool.py status
```

#### Keyset Management
```bash
# List configured keysets
python ccm_tool.py list-keysets

# Establish secure channel
python ccm_tool.py establish-secure-channel default_scp03 --security-level 3

# Close secure channel
python ccm_tool.py close-secure-channel
```

#### Security Domain Operations
```bash
# List all security domains
python ccm_tool.py list-security-domains

# List all applications
python ccm_tool.py list-applications

# Create a new security domain
python ccm_tool.py create-security-domain A000000151DEAD01 --domain-type SSD

# Perform CLFDB operations
python ccm_tool.py clfdb A000000151DEAD01 --operation lock
python ccm_tool.py clfdb A000000151DEAD01 --operation unlock

# Extradite an application
python ccm_tool.py extradite A0000001515555AA A000000151200000
```

#### Visualization
```bash
# Generate all visualizations
python ccm_tool.py visualize

# Generate visualizations in custom directory
python ccm_tool.py visualize --output-dir custom_output
```

### Python API

The tool can also be used as a Python library:

```python
from src import SmartcardManager, GlobalPlatformManager, SecureChannelManager, ConfigManager

# Initialize components
config_manager = ConfigManager()
sc_manager = SmartcardManager()
gp_manager = GlobalPlatformManager(sc_manager)
secure_channel = SecureChannelManager(sc_manager)

# Connect to reader
readers = sc_manager.list_readers()
sc_manager.connect_to_reader(readers[0])

# Select Card Manager
gp_manager.select_card_manager()

# Establish secure channel
keyset = config_manager.get_keyset('default_scp03')
secure_channel.establish_secure_channel(keyset)

# List security domains
domains = gp_manager.list_security_domains()
for domain in domains:
    print(f"Domain: {domain}")

# Cleanup
secure_channel.close_secure_channel()
sc_manager.disconnect_all()
```

## 📁 Configuration

The tool uses YAML configuration files located in the `config/` directory:

### Keysets Configuration (`config/keysets.yaml`)
```yaml
keysets:
  default_scp03:
    protocol: "SCP03"
    enc_key: "404142434445464748494A4B4C4D4E4F"
    mac_key: "404142434445464748494A4B4C4D4E4F"
    dek_key: "404142434445464748494A4B4C4D4E4F"
    key_version: 1
    security_level: 3

security_domains:
  issuer_sd:
    type: "ISD"
    aid: "A000000151000000"
    privileges: "A0"
```

### Application Settings (`config/settings.yaml`)
```yaml
app:
  name: "Smartcard Management Tool"
  version: "1.0.0"
  debug: false

pcsc:
  timeout: 5000
  protocols: ["T0", "T1"]

visualization:
  output_format: "png"
  output_directory: "output"
```

## 🔧 Examples

The `examples/` directory contains several demonstration scripts:

- **`basic_example.py`** - Basic smartcard operations
- **`advanced_example.py`** - Secure channel and security domain management
- **`visualization_demo.py`** - Comprehensive visualization examples

Run any example:
```bash
python examples/basic_example.py
python examples/advanced_example.py
python examples/visualization_demo.py
```

## 🧪 Testing

Run the test suite to verify your installation:
```bash
python tests/test_main.py
```

The tests cover:
- APDU command/response handling
- Configuration management
- KeySet operations
- Mock smartcard operations
- Visualization functions

## 📊 Visualization Output

The tool generates several types of visualizations:

1. **Hierarchy Diagram** - Shows the relationship between security domains and applications
2. **Network Graph** - Interactive network representation of card structure
3. **Privilege Matrix** - Visual analysis of privilege distribution
4. **Lifecycle Timeline** - Distribution of objects across lifecycle states

All visualizations are saved as high-resolution PNG files in the output directory.

## 🔐 Security Considerations

- **Key Management**: Store production keys securely and never commit them to version control
- **Secure Channels**: Always use appropriate security levels for production environments
- **Access Control**: Limit access to the tool and configuration files
- **Logging**: Monitor log files for security-relevant events

## 🛠️ Troubleshooting

### Common Issues

**"No PC/SC readers found"**
- Ensure your smartcard reader is properly connected
- Verify PC/SC middleware is installed and running
- Check if the reader is recognized by the system

**"Failed to establish secure channel"**
- Verify keyset configuration is correct
- Check if the card supports the specified SCP protocol
- Ensure proper card lifecycle state

**"Import errors"**
- Run `python install.py` to verify installation
- Check if all dependencies are installed
- Verify Python version compatibility

### Debug Mode

Enable debug logging by setting `debug: true` in `config/settings.yaml` or by setting the log level to DEBUG.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- GlobalPlatform specifications and documentation
- PC/SC Working Group standards
- Python smartcard community
- Open source cryptography libraries

## 📞 Support

For support, please:
1. Check the troubleshooting section
2. Review the examples directory
3. Open an issue on the project repository
4. Consult the GlobalPlatform specifications

---

**Note**: This tool is designed for development and testing purposes. Use appropriate security measures when working with production smartcards.
