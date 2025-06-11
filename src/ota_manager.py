"""
OTA (Over-The-Air) SMS-PP manager for CLFDB operations.
Handles creation and parsing of SMS-PP envelopes for smartcard lifecycle management.
"""

import logging
import struct
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, cmac
from cryptography.hazmat.backends import default_backend
from database_manager import DatabaseManager, OTAMessageTemplate, OTAMessage
import os
import json

logger = logging.getLogger(__name__)


@dataclass
class SMSPPHeader:
    """SMS-PP header structure"""
    udhi: bool  # User Data Header Indicator
    udhl: int   # User Data Header Length
    iei: int    # Information Element Identifier
    iedl: int   # Information Element Data Length
    port: int   # Destination port


@dataclass
class OTAHeader:
    """OTA header structure (TS 102.226)"""
    spi: int    # Security Parameter Indicator
    kad: int    # Key Access Domain
    tar: bytes  # Toolkit Application Reference (3 bytes)
    cntr: bytes # Counter (3 bytes)
    pcntr: int  # Padding Counter


@dataclass
class CLFDBCommand:
    """CLFDB (Card Life Cycle Database) command structure"""
    p2: int        # Lifecycle state
    aid_length: int
    aid: bytes
    cla: int = 0x80
    ins: int = 0xE6
    p1: int = 0x00
    lc: int = 0x14  # Length (20 bytes for AID structure)
    
    # Lifecycle states
    LOADED = 0x01
    INSTALLED = 0x03
    SELECTABLE = 0x07
    LOCKED = 0x83
    UNLOCKED = 0x07


class OTAManager:
    """Manages OTA SMS-PP envelope creation and CLFDB operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.backend = default_backend()
    
    def create_clfdb_sms_pp(self, template_name: str, target_aid: str, 
                           operation: str, keyset_name: str, value_set: str,
                           additional_params: Optional[Dict[str, Any]] = None) -> OTAMessage:
        """
        Create SMS-PP envelope for CLFDB operation
        
        Args:
            template_name: Name of OTA template to use
            target_aid: Target application AID
            operation: LOCK, UNLOCK, TERMINATE, MAKE_SELECTABLE
            keyset_name: Name of keyset for cryptographic operations
            value_set: Value set containing the keyset
            additional_params: Additional parameters for the operation
        """
        # Get template and keyset
        templates = self.db_manager.get_ota_templates("CLFDB")
        template = next((t for t in templates if t.name == template_name), None)
        if not template:
            raise ValueError(f"OTA template '{template_name}' not found")
        
        keyset_record = self.db_manager.get_keyset_by_name(keyset_name, value_set)
        if not keyset_record:
            raise ValueError(f"Keyset '{keyset_name}' not found in value set '{value_set}'")
        
        # Create CLFDB command
        lifecycle_state = self._get_lifecycle_state(operation)
        aid_bytes = bytes.fromhex(target_aid)
        
        # Build command APDU
        command_data = self._build_clfdb_command(aid_bytes, lifecycle_state)
        
        # Create OTA envelope
        ota_header = OTAHeader(
            spi=int(template.spi, 16),
            kad=int(template.kad, 16),
            tar=bytes.fromhex(template.tar),
            cntr=bytes.fromhex(template.cntr),
            pcntr=int(template.pcntr, 16)
        )
        
        # Encrypt and sign the command if needed
        secured_command = self._secure_ota_command(command_data, ota_header, keyset_record)
        
        # Create SMS-PP envelope
        udh, user_data = self._create_sms_pp_envelope(secured_command, ota_header)
        sms_tpdu = self._create_sms_tpdu(udh, user_data)
        
        # Create OTA message record
        message = OTAMessage(
            id=None,
            template_id=template.id,
            target_aid=target_aid,
            operation=operation,
            parameters=json.dumps(additional_params or {}),
            sms_tpdu=sms_tpdu.hex().upper(),
            udh=udh.hex().upper(),
            user_data=user_data.hex().upper(),
            created_at="",  # Will be set by database
            status="CREATED"
        )
        
        # Save to database
        message.id = self.db_manager.add_ota_message(message)
        
        logger.info(f"Created CLFDB SMS-PP message for {operation} on AID {target_aid}")
        return message
    
    def _get_lifecycle_state(self, operation: str) -> int:
        """Get the target lifecycle state for the operation"""
        lifecycle_map = {
            "LOCK": CLFDBCommand.LOCKED,
            "UNLOCK": CLFDBCommand.UNLOCKED,
            "TERMINATE": CLFDBCommand.LOADED,  # Terminate moves to LOADED
            "MAKE_SELECTABLE": CLFDBCommand.SELECTABLE
        }
        
        if operation not in lifecycle_map:
            raise ValueError(f"Unsupported CLFDB operation: {operation}")
        
        return lifecycle_map[operation]
    
    def _build_clfdb_command(self, aid: bytes, lifecycle_state: int) -> bytes:
        """Build CLFDB command APDU"""
        if len(aid) > 16:
            raise ValueError("AID too long (max 16 bytes)")
        
        # CLFDB command structure: CLA INS P1 P2 LC AID_LEN AID
        command = bytearray()
        command.append(0x80)  # CLA
        command.append(0xE6)  # INS
        command.append(0x00)  # P1
        command.append(lifecycle_state)  # P2
        command.append(0x14)  # LC (20 bytes: 1 byte length + up to 16 bytes AID + 3 bytes padding)
        command.append(len(aid))  # AID length
        command.extend(aid)  # AID
        
        # Pad to total length of 20 bytes data
        padding_needed = 19 - len(aid)  # 20 - 1 (AID length byte) - AID length
        command.extend(b'\\x00' * padding_needed)
        
        return bytes(command)
    
    def _secure_ota_command(self, command: bytes, ota_header: OTAHeader, 
                           keyset_record) -> bytes:
        """Apply OTA security (encryption and/or MAC) to the command"""
        # For demonstration, implementing basic security
        # In production, implement full TS 102.226 security
        
        spi = ota_header.spi
        secured_data = bytearray()
        
        # Add OTA header
        secured_data.append(spi)
        secured_data.append(ota_header.kad)
        secured_data.extend(ota_header.tar)
        secured_data.extend(ota_header.cntr)
        secured_data.append(ota_header.pcntr)
        
        if spi & 0x01:  # RC/CC/DS security
            # Apply cryptographic checksum/digital signature
            if spi & 0x02:  # Encryption required
                # Encrypt the command
                encrypted_command = self._encrypt_command(command, keyset_record)
                secured_data.extend(encrypted_command)
            else:
                secured_data.extend(command)
            
            # Add MAC/signature
            mac = self._calculate_ota_mac(secured_data, keyset_record)
            secured_data.extend(mac)
        else:
            # No security
            secured_data.extend(command)
        
        return bytes(secured_data)
    
    def _encrypt_command(self, command: bytes, keyset_record) -> bytes:
        """Encrypt OTA command using keyset"""
        # Use DES3/AES encryption based on protocol
        if keyset_record.protocol == "SCP03":
            # AES encryption
            key = bytes.fromhex(keyset_record.enc_key)[:16]  # Use first 16 bytes for AES-128
            iv = os.urandom(16)
            
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            # Pad command to AES block size
            padded_command = self._pad_data(command, 16)
            encrypted = encryptor.update(padded_command) + encryptor.finalize()
            
            return iv + encrypted
        else:
            # DES3 encryption for SCP02
            key = bytes.fromhex(keyset_record.enc_key)
            iv = os.urandom(8)
            
            cipher = Cipher(algorithms.TripleDES(key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            # Pad command to DES block size
            padded_command = self._pad_data(command, 8)
            encrypted = encryptor.update(padded_command) + encryptor.finalize()
            
            return iv + encrypted
    
    def _calculate_ota_mac(self, data: bytes, keyset_record) -> bytes:
        """Calculate OTA MAC using keyset"""
        if keyset_record.protocol == "SCP03":
            # AES-CMAC
            key = bytes.fromhex(keyset_record.mac_key)[:16]
            c = cmac.CMAC(algorithms.AES(key), backend=self.backend)
            c.update(data)
            return c.finalize()[:8]  # First 8 bytes
        else:
            # DES3-MAC for SCP02
            key = bytes.fromhex(keyset_record.mac_key)
            c = cmac.CMAC(algorithms.TripleDES(key), backend=self.backend)
            c.update(data)
            return c.finalize()[:8]
    
    def _pad_data(self, data: bytes, block_size: int) -> bytes:
        """Apply PKCS#7 padding"""
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    def _create_sms_pp_envelope(self, secured_command: bytes, ota_header: OTAHeader) -> Tuple[bytes, bytes]:
        """Create SMS-PP envelope with UDH and user data"""
        # SMS-PP UDH for OTA (TS 131.111)
        udh = bytearray()
        udh.append(0x70)  # IEI: SMS-PP Download
        udh.append(len(secured_command))  # IEDL
        
        # User data is the secured OTA command
        user_data = secured_command
        
        return bytes(udh), user_data
    
    def _create_sms_tpdu(self, udh: bytes, user_data: bytes) -> bytes:
        """Create complete SMS TPDU"""
        # SMS-DELIVER TPDU structure
        tpdu = bytearray()
        
        # SMS-DELIVER PDU type with UDHI=1
        tpdu.append(0x44)  # SMS-DELIVER with UDHI set
        
        # Originating address (dummy OTA server address)
        oa = "1234567890"  # Dummy number
        tpdu.append(len(oa))  # Address length
        tpdu.append(0x91)     # Type of address (international, ISDN)
        # Pack BCD digits
        for i in range(0, len(oa), 2):
            if i + 1 < len(oa):
                digit = int(oa[i+1]) << 4 | int(oa[i])
            else:
                digit = 0xF0 | int(oa[i])
            tpdu.append(digit)
        
        # Protocol Identifier (SMS-PP)
        tpdu.append(0x7F)
        
        # Data Coding Scheme
        tpdu.append(0x00)
        
        # Service Centre Time Stamp (dummy)
        tpdu.extend([0x00] * 7)
        
        # User Data Length (UDH + user data)
        udl = len(udh) + len(user_data) + 1  # +1 for UDHL
        tpdu.append(udl)
        
        # User Data Header Length
        tpdu.append(len(udh))
        
        # User Data Header
        tpdu.extend(udh)
        
        # User Data
        tpdu.extend(user_data)
        
        return bytes(tpdu)
    
    def parse_ota_response(self, response_sms: bytes) -> Dict[str, Any]:
        """Parse OTA response SMS"""
        try:
            # Basic parsing of response
            # In production, implement full TS 102.226 response parsing
            return {
                "status": "success",
                "response_data": response_sms.hex(),
                "parsed": True
            }
        except Exception as e:
            logger.error(f"Error parsing OTA response: {e}")
            return {
                "status": "error",
                "error": str(e),
                "parsed": False
            }
    
    def get_clfdb_operations(self) -> List[str]:
        """Get available CLFDB operations"""
        return ["LOCK", "UNLOCK", "TERMINATE", "MAKE_SELECTABLE"]
    
    def validate_aid(self, aid: str) -> bool:
        """Validate AID format"""
        try:
            aid_bytes = bytes.fromhex(aid)
            return 5 <= len(aid_bytes) <= 16
        except ValueError:
            return False
    
    def create_custom_ota_command(self, template_name: str, target_aid: str,
                                 custom_apdu: str, keyset_name: str, value_set: str) -> OTAMessage:
        """Create custom OTA command with user-provided APDU"""
        # Get template and keyset
        templates = self.db_manager.get_ota_templates()
        template = next((t for t in templates if t.name == template_name), None)
        if not template:
            raise ValueError(f"OTA template '{template_name}' not found")
        
        keyset_record = self.db_manager.get_keyset_by_name(keyset_name, value_set)
        if not keyset_record:
            raise ValueError(f"Keyset '{keyset_name}' not found in value set '{value_set}'")
        
        # Parse custom APDU
        try:
            command_data = bytes.fromhex(custom_apdu)
        except ValueError:
            raise ValueError("Invalid APDU hex format")
        
        # Create OTA envelope
        ota_header = OTAHeader(
            spi=int(template.spi, 16),
            kad=int(template.kad, 16),
            tar=bytes.fromhex(template.tar),
            cntr=bytes.fromhex(template.cntr),
            pcntr=int(template.pcntr, 16)
        )
        
        # Secure the command
        secured_command = self._secure_ota_command(command_data, ota_header, keyset_record)
        
        # Create SMS-PP envelope
        udh, user_data = self._create_sms_pp_envelope(secured_command, ota_header)
        sms_tpdu = self._create_sms_tpdu(udh, user_data)
        
        # Create and save message
        message = OTAMessage(
            id=None,
            template_id=template.id,
            target_aid=target_aid,
            operation="CUSTOM",
            parameters=json.dumps({"custom_apdu": custom_apdu}),
            sms_tpdu=sms_tpdu.hex().upper(),
            udh=udh.hex().upper(),
            user_data=user_data.hex().upper(),
            created_at="",
            status="CREATED"
        )
        
        message.id = self.db_manager.add_ota_message(message)
        
        logger.info(f"Created custom OTA message for AID {target_aid}")
        return message
