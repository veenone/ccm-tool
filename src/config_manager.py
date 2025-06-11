"""
Configuration management for keysets, settings, and security domain templates.
Enhanced with SQLite database storage for configurable keyset value sets.
"""

import logging
import yaml
import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from .secure_channel import KeySet
from .database_manager import DatabaseManager, KeysetRecord

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration"""
    name: str
    version: str
    debug: bool


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    format: str
    file: str


@dataclass
class PCSCConfig:
    """PC/SC configuration"""
    timeout: int
    protocols: List[str]


@dataclass
class GlobalPlatformConfig:
    """GlobalPlatform configuration"""
    default_manager_aid: str
    max_apdu_size: int


@dataclass
class VisualizationConfig:
    """Visualization configuration"""
    output_format: str
    output_directory: str
    show_privileges: bool
    show_lifecycle: bool


class ConfigManager:
    """Manages configuration files and settings with SQLite database integration"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.db_manager = DatabaseManager()  # Initialize database manager
        self.keysets: Dict[str, KeySet] = {}
        self.security_domain_templates: Dict[str, Dict[str, Any]] = {}
        self.app_config: Optional[AppConfig] = None
        self.logging_config: Optional[LoggingConfig] = None
        self.pcsc_config: Optional[PCSCConfig] = None
        self.gp_config: Optional[GlobalPlatformConfig] = None
        self.viz_config: Optional[VisualizationConfig] = None
        
        self.load_all_configs()
    
    def load_all_configs(self):
        """Load all configuration files and database keysets"""
        try:
            self.load_keysets_from_database()  # Load from database first
            self.load_keysets_from_yaml()      # Then load from YAML (for backward compatibility)
            self.load_settings()
            logger.info("All configurations loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
    
    def load_keysets_from_database(self):
        """Load keyset configurations from SQLite database"""
        try:
            keyset_records = self.db_manager.get_keysets()
            for record in keyset_records:
                keyset = KeySet.from_hex(
                    enc_hex=record.enc_key,
                    mac_hex=record.mac_key,
                    dek_hex=record.dek_key,
                    key_version=record.key_version,
                    protocol=record.protocol
                )
                # Use format: {value_set}:{name} for unique identification
                keyset_key = f"{record.value_set}:{record.name}"
                self.keysets[keyset_key] = keyset
                logger.debug(f"Loaded keyset '{keyset_key}' from database")
        except Exception as e:
            logger.error(f"Error loading keysets from database: {e}")
    
    def load_keysets_from_yaml(self):
        """Load keyset configurations from YAML file (backward compatibility)"""
        keysets_file = os.path.join(self.config_dir, "keysets.yaml")
        
        if not os.path.exists(keysets_file):
            logger.warning(f"Keysets file not found: {keysets_file}")
            return
        
        try:
            with open(keysets_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Load keysets (only if not already loaded from database)
            if 'keysets' in config:
                for name, keyset_data in config['keysets'].items():
                    yaml_key = f"yaml:{name}"  # Prefix with 'yaml:' to distinguish
                    if yaml_key not in self.keysets:
                        try:
                            keyset = KeySet.from_hex(
                                enc_hex=keyset_data['enc_key'],
                                mac_hex=keyset_data['mac_key'],
                                dek_hex=keyset_data['dek_key'],
                                key_version=keyset_data['key_version'],
                                protocol=keyset_data['protocol']
                            )
                            self.keysets[yaml_key] = keyset
                            logger.debug(f"Loaded keyset '{name}' from YAML")
                        except Exception as e:
                            logger.error(f"Error loading keyset '{name}' from YAML: {e}")
        except Exception as e:
            logger.error(f"Error loading keysets from YAML: {e}")
    
    def get_keyset(self, name: str, value_set: str = "production") -> Optional[KeySet]:
        """Get a keyset by name and value set"""
        # Try database format first
        db_key = f"{value_set}:{name}"
        if db_key in self.keysets:
            return self.keysets[db_key]
        
        # Fall back to YAML format
        yaml_key = f"yaml:{name}"
        if yaml_key in self.keysets:
            return self.keysets[yaml_key]
        
        # Try simple name for backward compatibility
        if name in self.keysets:
            return self.keysets[name]
        
        return None
    
    def get_available_keysets(self, value_set: Optional[str] = None) -> Dict[str, List[str]]:
        """Get available keysets grouped by value set"""
        result = {}
        
        # Get from database
        keyset_records = self.db_manager.get_keysets(value_set=value_set)
        for record in keyset_records:
            if record.value_set not in result:
                result[record.value_set] = []
            result[record.value_set].append(record.name)
        
        # Add YAML keysets under 'yaml' value set
        yaml_keysets = [k.replace("yaml:", "") for k in self.keysets.keys() if k.startswith("yaml:")]
        if yaml_keysets:
            result["yaml"] = yaml_keysets
        
        return result
    
    def add_keyset(self, name: str, value_set: str, protocol: str, 
                   enc_key: str, mac_key: str, dek_key: str, 
                   key_version: int, security_level: int, 
                   description: str = "") -> bool:
        """Add a new keyset to the database"""
        try:
            keyset_record = KeysetRecord(
                id=None,
                name=name,
                value_set=value_set,
                protocol=protocol,
                enc_key=enc_key.upper(),
                mac_key=mac_key.upper(),
                dek_key=dek_key.upper(),
                key_version=key_version,
                security_level=security_level,
                description=description,
                created_at="",
                updated_at="",
                is_active=True
            )
            
            # Add to database
            self.db_manager.add_keyset(keyset_record)
            
            # Add to memory cache
            keyset = KeySet.from_hex(enc_key, mac_key, dek_key, key_version, protocol)
            keyset_key = f"{value_set}:{name}"
            self.keysets[keyset_key] = keyset
            
            logger.info(f"Added keyset '{name}' to value set '{value_set}'")
            return True
        except Exception as e:
            logger.error(f"Error adding keyset: {e}")
            return False
    
    def update_keyset(self, keyset_id: int, **kwargs) -> bool:
        """Update an existing keyset in the database"""
        try:
            # Get current keyset
            keysets = self.db_manager.get_keysets()
            keyset_record = next((k for k in keysets if k.id == keyset_id), None)
            if not keyset_record:
                return False
            
            # Update fields
            for field, value in kwargs.items():
                if hasattr(keyset_record, field):
                    setattr(keyset_record, field, value)
            
            # Update in database
            result = self.db_manager.update_keyset(keyset_record)
            
            if result:
                # Reload keysets to refresh cache
                self.load_keysets_from_database()
                logger.info(f"Updated keyset ID {keyset_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error updating keyset: {e}")
            return False
    
    def delete_keyset(self, keyset_id: int) -> bool:
        """Delete a keyset from the database"""
        try:
            result = self.db_manager.delete_keyset(keyset_id)
            if result:
                # Reload keysets to refresh cache
                self.load_keysets_from_database()
                logger.info(f"Deleted keyset ID {keyset_id}")
            return result
        except Exception as e:
            logger.error(f"Error deleting keyset: {e}")
            return False
    
    def get_value_sets(self) -> List[str]:
        """Get all available value sets"""
        return self.db_manager.get_value_sets()
    
    def export_keysets_to_yaml(self, value_set: str, output_file: str) -> bool:
        """Export keysets from a value set to YAML file"""
        try:
            keyset_records = self.db_manager.get_keysets(value_set=value_set)
            
            export_data = {
                'keysets': {},
                'metadata': {
                    'value_set': value_set,
                    'exported_at': logger.handlers[0].formatter.formatTime(logger.makeRecord("", 0, "", 0, "", (), None)),
                    'count': len(keyset_records)
                }
            }
            
            for record in keyset_records:
                export_data['keysets'][record.name] = {
                    'protocol': record.protocol,
                    'enc_key': record.enc_key,
                    'mac_key': record.mac_key,
                    'dek_key': record.dek_key,
                    'key_version': record.key_version,
                    'security_level': record.security_level,
                    'description': record.description
                }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, indent=2)
            
            logger.info(f"Exported {len(keyset_records)} keysets from '{value_set}' to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting keysets: {e}")
            return False
    
    def import_keysets_from_yaml(self, yaml_file: str, target_value_set: str) -> Tuple[int, int]:
        """Import keysets from YAML file to a value set"""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if 'keysets' not in data:
                raise ValueError("Invalid YAML format: 'keysets' section not found")
            
            imported = 0
            skipped = 0
            
            for name, keyset_data in data['keysets'].items():
                try:
                    self.add_keyset(
                        name=name,
                        value_set=target_value_set,
                        protocol=keyset_data['protocol'],
                        enc_key=keyset_data['enc_key'],
                        mac_key=keyset_data['mac_key'],
                        dek_key=keyset_data['dek_key'],
                        key_version=keyset_data['key_version'],
                        security_level=keyset_data.get('security_level', 3),                        description=keyset_data.get('description', f"Imported from {yaml_file}")
                    )
                    imported += 1
                except Exception as e:
                    logger.warning(f"Skipped keyset '{name}': {e}")
                    skipped += 1
            
            logger.info(f"Imported {imported} keysets, skipped {skipped}")
            return imported, skipped
        except Exception as e:
            logger.error(f"Error importing keysets: {e}")
            return 0, 0
    
    def load_keysets_from_yaml(self):
        """Load keyset configurations from YAML file"""
        keysets_file = os.path.join(self.config_dir, "keysets.yaml")
        
        if not os.path.exists(keysets_file):
            logger.warning(f"Keysets file not found: {keysets_file}")
            return
        
        try:
            with open(keysets_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Load keysets
            if 'keysets' in config:
                for name, keyset_data in config['keysets'].items():
                    try:
                        if self.validate_keyset(keyset_data):
                            keyset = self.create_keyset_from_dict(keyset_data)
                            if keyset:
                                # Use yaml: prefix to distinguish from database keysets
                                yaml_key = f"yaml:{name}"
                                self.keysets[yaml_key] = keyset
                                logger.debug(f"Loaded keyset: {name}")
                    except Exception as e:
                        logger.error(f"Error loading keyset {name}: {e}")
            
            # Load security domain templates
            if 'security_domains' in config:
                self.security_domain_templates = config['security_domains']
                logger.debug(f"Loaded {len(self.security_domain_templates)} security domain templates")
            
        except Exception as e:
            logger.error(f"Error loading keysets file: {e}")
    
    def load_settings(self):
        """Load application settings from YAML file"""
        settings_file = os.path.join(self.config_dir, "settings.yaml")
        
        if not os.path.exists(settings_file):
            logger.warning(f"Settings file not found: {settings_file}")
            self._create_default_settings()
            return
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Load app config
            if 'app' in config:
                self.app_config = AppConfig(**config['app'])
            
            # Load logging config
            if 'logging' in config:
                self.logging_config = LoggingConfig(**config['logging'])
            
            # Load PC/SC config
            if 'pcsc' in config:
                self.pcsc_config = PCSCConfig(**config['pcsc'])
            
            # Load GlobalPlatform config
            if 'globalplatform' in config:
                self.gp_config = GlobalPlatformConfig(**config['globalplatform'])
            
            # Load visualization config
            if 'visualization' in config:
                self.viz_config = VisualizationConfig(**config['visualization'])
            
            logger.info("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading settings file: {e}")
            self._create_default_settings()
    
    def _create_default_settings(self):
        """Create default settings if no config file exists"""
        self.app_config = AppConfig(
            name="Smartcard Management Tool",
            version="1.0.0",
            debug=False
        )
        
        self.logging_config = LoggingConfig(
            level="INFO",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file="logs/ccm_tool.log"
        )
        
        self.pcsc_config = PCSCConfig(
            timeout=5000,
            protocols=["T0", "T1"]
        )
        
        self.gp_config = GlobalPlatformConfig(
            default_manager_aid="A000000151000000",
            max_apdu_size=255
        )
        
        self.viz_config = VisualizationConfig(
            output_format="png",
            output_directory="output",
            show_privileges=True,
            show_lifecycle=True
        )
    
    def get_keyset(self, name: str) -> Optional[KeySet]:
        """Get a keyset by name"""
        return self.keysets.get(name)
    
    def list_keysets(self) -> List[str]:
        """List all available keyset names"""
        return list(self.keysets.keys())
    
    def add_keyset(self, name: str, keyset: KeySet):
        """Add a new keyset"""
        self.keysets[name] = keyset
        logger.info(f"Added keyset: {name}")
    
    def remove_keyset(self, name: str) -> bool:
        """Remove a keyset"""
        if name in self.keysets:
            del self.keysets[name]
            logger.info(f"Removed keyset: {name}")
            return True
        return False
    
    def get_security_domain_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a security domain template by name"""
        return self.security_domain_templates.get(name)
    
    def list_security_domain_templates(self) -> List[str]:
        """List all available security domain template names"""
        return list(self.security_domain_templates.keys())
    
    def add_security_domain_template(self, name: str, template: Dict[str, Any]):
        """Add a new security domain template"""
        self.security_domain_templates[name] = template
        logger.info(f"Added security domain template: {name}")
    
    def save_keysets(self):
        """Save keysets to file"""
        keysets_file = os.path.join(self.config_dir, "keysets.yaml")
        
        try:
            config = {
                'keysets': {},
                'security_domains': self.security_domain_templates
            }
            
            for name, keyset in self.keysets.items():
                config['keysets'][name] = {
                    'protocol': keyset.protocol,
                    'enc_key': keyset.enc_key.hex().upper(),
                    'mac_key': keyset.mac_key.hex().upper(),
                    'dek_key': keyset.dek_key.hex().upper(),
                    'key_version': keyset.key_version,
                    'security_level': 3  # Default security level
                }
            
            with open(keysets_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Keysets saved to: {keysets_file}")
            
        except Exception as e:
            logger.error(f"Error saving keysets: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        settings_file = os.path.join(self.config_dir, "settings.yaml")
        
        try:
            config = {}
            
            if self.app_config:
                config['app'] = {
                    'name': self.app_config.name,
                    'version': self.app_config.version,
                    'debug': self.app_config.debug
                }
            
            if self.logging_config:
                config['logging'] = {
                    'level': self.logging_config.level,
                    'format': self.logging_config.format,
                    'file': self.logging_config.file
                }
            
            if self.pcsc_config:
                config['pcsc'] = {
                    'timeout': self.pcsc_config.timeout,
                    'protocols': self.pcsc_config.protocols
                }
            
            if self.gp_config:
                config['globalplatform'] = {
                    'default_manager_aid': self.gp_config.default_manager_aid,
                    'max_apdu_size': self.gp_config.max_apdu_size
                }
            
            if self.viz_config:
                config['visualization'] = {
                    'output_format': self.viz_config.output_format,
                    'output_directory': self.viz_config.output_directory,
                    'show_privileges': self.viz_config.show_privileges,
                    'show_lifecycle': self.viz_config.show_lifecycle
                }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Settings saved to: {settings_file}")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def validate_keyset(self, keyset_data: Dict[str, Any]) -> bool:
        """Validate keyset data structure"""
        required_fields = ['protocol', 'enc_key', 'mac_key', 'dek_key', 'key_version']
        
        for field in required_fields:
            if field not in keyset_data:
                logger.error(f"Missing required field in keyset: {field}")
                return False
        
        # Validate protocol
        if keyset_data['protocol'] not in ['SCP02', 'SCP03']:
            logger.error(f"Invalid protocol: {keyset_data['protocol']}")
            return False
        
        # Validate key lengths (should be 32 hex characters = 16 bytes)
        for key_field in ['enc_key', 'mac_key', 'dek_key']:
            key_hex = keyset_data[key_field]
            if len(key_hex) != 32 or not all(c in '0123456789ABCDEFabcdef' for c in key_hex):
                logger.error(f"Invalid key format for {key_field}: {key_hex}")
                return False
        
        # Validate key version
        if not isinstance(keyset_data['key_version'], int) or keyset_data['key_version'] < 0 or keyset_data['key_version'] > 255:
            logger.error(f"Invalid key version: {keyset_data['key_version']}")
            return False
        
        return True
    
    def create_keyset_from_dict(self, keyset_data: Dict[str, Any]) -> Optional[KeySet]:
        """Create KeySet object from dictionary data"""
        if not self.validate_keyset(keyset_data):
            return None
        
        try:
            return KeySet.from_hex(
                enc_hex=keyset_data['enc_key'],
                mac_hex=keyset_data['mac_key'],
                dek_hex=keyset_data['dek_key'],
                key_version=keyset_data['key_version'],
                protocol=keyset_data['protocol']
            )
        except Exception as e:
            logger.error(f"Error creating keyset: {e}")
            return None
    
    def get_default_manager_aid(self) -> bytes:
        """Get default Card Manager AID as bytes"""
        if self.gp_config and self.gp_config.default_manager_aid:
            return bytes.fromhex(self.gp_config.default_manager_aid)
        else:
            return bytes.fromhex("A000000151000000")  # Default GP CM AID
    
    def get_pcsc_timeout(self) -> int:
        """Get PC/SC timeout value"""
        if self.pcsc_config:
            return self.pcsc_config.timeout
        else:
            return 5000  # Default 5 seconds
    
    def get_visualization_output_dir(self) -> str:
        """Get visualization output directory"""
        if self.viz_config:
            return self.viz_config.output_directory
        else:
            return "output"  # Default directory
