# Smartcard Management Tool - Complete Implementation

## 📋 Project Overview

This is a comprehensive Python-based smartcard management tool that provides all the requested functionality for managing smartcard content through PC/SC readers with full GlobalPlatform support.

## ✅ Implemented Features

### 1. PC/SC Reader Management ✓
- **Reader Detection**: Automatically discover all available PC/SC readers
- **Connection Management**: Connect/disconnect from readers with timeout handling
- **Protocol Support**: T=0 and T=1 protocol support
- **Cross-Platform**: Windows, Linux, and macOS compatibility

### 2. Application & Security Domain Discovery ✓
- **Complete Enumeration**: List all applications and security domains
- **Detailed Information**: AID, lifecycle state, privileges, and type detection
- **Status Parsing**: Parse GET STATUS responses according to GP specification
- **Hierarchical Structure**: Understand relationships between objects

### 3. Secure Channel Management ✓
- **SCP02 Implementation**: Full SCP02 protocol support
- **SCP03 Implementation**: Full SCP03 protocol support with AES
- **Configurable Security Levels**: 1=MAC, 2=MAC+ENC, 3=MAC+ENC+RMAC
- **Key Derivation**: Proper session key derivation for both protocols
- **Cryptogram Verification**: Card and host cryptogram validation

### 4. Configurable Keysets ✓
- **YAML Configuration**: Flexible keyset definition in YAML files
- **Multiple Protocols**: Support for both SCP02 and SCP03 keysets
- **Key Management**: Add, remove, and validate keysets
- **Template System**: Pre-configured keyset templates

### 5. Security Domain Creation ✓
- **All Types Supported**: Create SSD, AMSD, and DMSD security domains
- **Configurable Privileges**: Set appropriate privilege levels
- **INSTALL Command**: Proper GP INSTALL command implementation
- **Template-Based Creation**: Use templates for common configurations

### 6. CLFDB Operations ✓
- **Lifecycle Management**: Lock, unlock, and terminate operations
- **SET STATUS Command**: Proper SET STATUS command implementation
- **State Validation**: Verify lifecycle state changes
- **Error Handling**: Comprehensive error reporting

### 7. Extradition Support ✓
- **Object Transfer**: Move applications between security domains
- **Association Management**: Update object associations
- **Privilege Verification**: Ensure proper extradition privileges
- **Status Updates**: Update object status after extradition

### 8. Comprehensive Visualization ✓
- **Hierarchy Diagrams**: Visual security domain and application relationships
- **Network Graphs**: Interactive network representation
- **Privilege Matrix**: Visual privilege analysis with heatmaps
- **Lifecycle Timeline**: Distribution analysis across lifecycle states
- **Export Formats**: High-resolution PNG output

## 🏗️ Architecture

### Core Components

1. **`smartcard_manager.py`** - Low-level PC/SC interface
   - APDU command/response handling
   - Reader connection management
   - Protocol abstraction

2. **`globalplatform.py`** - GlobalPlatform operations
   - GET STATUS command parsing
   - Security domain management
   - Application enumeration
   - INSTALL and SET STATUS commands

3. **`secure_channel.py`** - Secure channel protocols
   - SCP02/SCP03 implementation
   - Key derivation functions
   - Cryptographic operations
   - Session management

4. **`config_manager.py`** - Configuration management
   - YAML configuration parsing
   - Keyset management
   - Template system
   - Settings validation

5. **`visualization.py`** - Visual reporting
   - Multiple chart types
   - Data analysis
   - Export functionality
   - Custom styling

### User Interfaces

1. **Command Line Interface (`ccm_tool.py`)**
   - Complete CLI with all operations
   - Color-coded output
   - Progress indicators
   - Error handling

2. **Python API**
   - Full programmatic access
   - Modular design
   - Exception handling
   - Context managers

## 📁 Project Structure

```
smartcard-management-tool/
├── ccm_tool.py              # Main CLI application
├── README.md                # Comprehensive documentation
├── requirements.txt         # Python dependencies
├── setup.py                 # Package installation
├── install.py               # Installation script
├── install.bat              # Windows installer
├── test_structure.py        # Structure verification
├── .gitignore              # Git ignore rules
│
├── src/                     # Core modules
│   ├── __init__.py         # Package initialization
│   ├── smartcard_manager.py # PC/SC interface
│   ├── globalplatform.py   # GlobalPlatform operations
│   ├── secure_channel.py   # SCP02/SCP03 implementation
│   ├── config_manager.py   # Configuration management
│   └── visualization.py    # Visualization engine
│
├── config/                  # Configuration files
│   ├── keysets.yaml        # Keyset definitions
│   └── settings.yaml       # Application settings
│
├── examples/               # Example scripts
│   ├── basic_example.py    # Basic operations
│   ├── advanced_example.py # Advanced features
│   └── visualization_demo.py # Visualization demo
│
├── tests/                  # Test suite
│   └── test_main.py       # Comprehensive tests
│
├── logs/                   # Log files
├── output/                 # Visualization output
└── docs/                   # Documentation
```

## 🚀 Usage Examples

### Basic Operations
```bash
# List readers and connect
python ccm_tool.py list-readers
python ccm_tool.py connect "Your Reader Name"

# Basic card information
python ccm_tool.py card-info
python ccm_tool.py status
```

### Security Domain Management
```bash
# List current state
python ccm_tool.py list-security-domains
python ccm_tool.py list-applications

# Establish secure channel
python ccm_tool.py establish-secure-channel default_scp03

# Create security domain
python ccm_tool.py create-security-domain A000000151DEAD01 --domain-type SSD

# CLFDB operations
python ccm_tool.py clfdb A000000151DEAD01 --operation lock
```

### Visualization
```bash
# Generate all visualizations
python ccm_tool.py visualize

# Custom output directory
python ccm_tool.py visualize --output-dir custom_output
```

### Python API
```python
from src import SmartcardManager, GlobalPlatformManager, SecureChannelManager

# Initialize and connect
sc_manager = SmartcardManager()
gp_manager = GlobalPlatformManager(sc_manager)
secure_channel = SecureChannelManager(sc_manager)

# Connect and authenticate
readers = sc_manager.list_readers()
sc_manager.connect_to_reader(readers[0])
gp_manager.select_card_manager()

# Establish secure channel
keyset = config_manager.get_keyset('default_scp03')
secure_channel.establish_secure_channel(keyset)

# Perform operations
domains = gp_manager.list_security_domains()
apps = gp_manager.list_applications()
```

## 🔧 Configuration

### Keyset Configuration (`config/keysets.yaml`)
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

## 🧪 Testing

### Run Tests
```bash
# Structure test (no dependencies)
python test_structure.py

# Full test suite
python tests/test_main.py

# Example scripts
python examples/basic_example.py
python examples/visualization_demo.py
```

## 📊 Visualization Outputs

The tool generates comprehensive visualizations:

1. **Hierarchy Diagram** - Shows security domain relationships
2. **Network Graph** - Interactive network representation  
3. **Privilege Matrix** - Heatmap of privilege distribution
4. **Lifecycle Timeline** - State distribution analysis

All outputs are high-resolution PNG files with detailed legends and color coding.

## 🔐 Security Features

- **Secure Key Storage**: YAML-based keyset configuration
- **Protocol Compliance**: Full GP specification adherence
- **Error Handling**: Comprehensive error reporting
- **Logging**: Detailed operation logging
- **Validation**: Input validation and sanity checks

## 🚀 Getting Started

1. **Installation**:
   ```bash
   # Windows
   install.bat
   
   # Cross-platform
   python install.py
   ```

2. **Basic Usage**:
   ```bash
   python ccm_tool.py list-readers
   python ccm_tool.py connect "Reader Name"
   python ccm_tool.py list-security-domains
   ```

3. **Examples**:
   ```bash
   python examples/basic_example.py
   ```

## 🎯 Key Benefits

- **Complete Implementation**: All requested features implemented
- **Production Ready**: Robust error handling and validation
- **Extensible**: Modular architecture for easy extension
- **User Friendly**: Comprehensive CLI and Python API
- **Well Documented**: Extensive documentation and examples
- **Cross Platform**: Works on Windows, Linux, and macOS
- **Standards Compliant**: Full GlobalPlatform compliance

## 📈 Advanced Features

- **Batch Operations**: Process multiple cards/operations
- **Configuration Templates**: Pre-configured setups
- **Visual Analytics**: Comprehensive reporting
- **Error Recovery**: Robust error handling
- **Debug Support**: Detailed logging and diagnostics

This implementation provides a complete, professional-grade smartcard management solution that meets all your requirements and provides a solid foundation for further development.
