"""
GlobalPlatform implementation for managing security domains and applications.
Supports GP 2.1.1 and later specifications.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import struct
from .smartcard_manager import SmartcardManager, APDUCommand, APDUResponse, SmartcardException
from smartcard.util import toHexString, toBytes

logger = logging.getLogger(__name__)


class LifeCycleState(Enum):
    """GlobalPlatform Life Cycle States"""
    OP_READY = 0x01
    INITIALIZED = 0x03
    SECURED = 0x0F
    CARD_LOCKED = 0x7F
    TERMINATED = 0xFF
    INSTALLED = 0x03
    SELECTABLE = 0x07
    PERSONALIZED = 0x0F
    BLOCKED = 0x83
    LOCKED = 0x87


class PrivilegeType(Enum):
    """GlobalPlatform Privilege Types"""
    SECURITY_DOMAIN = 0x80
    DAP_VERIFICATION = 0x40
    DELEGATED_MANAGEMENT = 0x20
    CARD_LOCK = 0x10
    CARD_TERMINATE = 0x08
    CARD_RESET = 0x04
    CVM_MANAGEMENT = 0x02
    MANDATED_DAP_VERIFICATION = 0x01


@dataclass
class ApplicationInfo:
    """Information about an installed application"""
    aid: bytes
    life_cycle: LifeCycleState
    privileges: int
    executable_load_file_aid: Optional[bytes] = None
    executable_module_aid: Optional[bytes] = None
    
    def __str__(self) -> str:
        return f"App(AID={toHexString(self.aid)}, LC={self.life_cycle.name}, Priv={self.privileges:02X})"


@dataclass
class SecurityDomainInfo:
    """Information about a security domain"""
    aid: bytes
    life_cycle: LifeCycleState
    privileges: int
    domain_type: str  # ISD, SSD, AMSD, DMSD
    associated_applications: List[bytes]
    
    def __str__(self) -> str:
        return f"SD(AID={toHexString(self.aid)}, Type={self.domain_type}, LC={self.life_cycle.name}, Priv={self.privileges:02X})"


class TLVParser:
    """Simple TLV (Tag-Length-Value) parser for GlobalPlatform responses"""
    
    @staticmethod
    def parse(data: bytes) -> Dict[int, bytes]:
        """Parse TLV data and return tag->value mapping"""
        result = {}
        offset = 0
        
        while offset < len(data):
            if offset + 1 >= len(data):
                break
                
            # Parse tag (assuming single byte tags for simplicity)
            tag = data[offset]
            offset += 1
            
            # Parse length
            length = data[offset]
            offset += 1
            
            # Parse value
            if offset + length > len(data):
                break
                
            value = data[offset:offset + length]
            offset += length
            
            result[tag] = value
        
        return result


class GlobalPlatformManager:
    """GlobalPlatform card management operations"""
    
    def __init__(self, smartcard_manager: SmartcardManager):
        self.sc_manager = smartcard_manager
        self.selected_sd_aid: Optional[bytes] = None
        self.card_manager_aid = bytes.fromhex("A000000151000000")  # Default GP Card Manager AID
        
    def select_card_manager(self) -> bool:
        """Select the Card Manager (ISD)"""
        try:
            response = self.sc_manager.select_application(self.card_manager_aid)
            if response.is_success:
                self.selected_sd_aid = self.card_manager_aid
                logger.info("Successfully selected Card Manager")
                return True
            else:
                logger.error(f"Failed to select Card Manager: SW={response.sw:04X}")
                return False
        except Exception as e:
            logger.error(f"Error selecting Card Manager: {e}")
            return False
    
    def get_status(self, p1: int = 0x80, aid_filter: Optional[bytes] = None) -> List[Dict[str, Any]]:
        """
        Get status of applications and security domains
        P1: 0x80 = ISD only, 0x40 = Applications and SDs, 0x20 = Executable Load Files
        """
        objects = []
        
        try:
            # Build GET STATUS command
            data = b''
            if aid_filter:
                data = bytes([len(aid_filter)]) + aid_filter
            
            command = APDUCommand(
                cla=0x80,
                ins=0xF2,
                p1=p1,
                p2=0x00,
                data=data,
                le=0x00
            )
            
            response = self.sc_manager.send_apdu(command)
            
            if response.is_success or response.sw == 0x6310:  # More data available
                objects.extend(self._parse_status_response(response.data))
                
                # Handle continuation if more data available
                while response.sw == 0x6310:
                    command = APDUCommand(
                        cla=0x80,
                        ins=0xF2,
                        p1=p1,
                        p2=0x01,  # Get next occurrence
                        le=0x00
                    )
                    response = self.sc_manager.send_apdu(command)
                    if response.is_success or response.sw == 0x6310:
                        objects.extend(self._parse_status_response(response.data))
                    else:
                        break
            
            logger.info(f"Retrieved {len(objects)} objects from GET STATUS")
            return objects
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return []
    
    def _parse_status_response(self, data: bytes) -> List[Dict[str, Any]]:
        """Parse GET STATUS response data"""
        objects = []
        offset = 0
        
        while offset < len(data):
            if offset + 2 > len(data):
                break
            
            # Parse object info
            aid_length = data[offset]
            offset += 1
            
            if offset + aid_length > len(data):
                break
            
            aid = data[offset:offset + aid_length]
            offset += aid_length
            
            if offset + 1 > len(data):
                break
            
            life_cycle = data[offset]
            offset += 1
            
            if offset + 1 > len(data):
                break
            
            privileges = data[offset]
            offset += 1
            
            # Determine object type based on privileges
            obj_type = "Application"
            if privileges & 0x80:  # Security Domain privilege
                if aid == self.card_manager_aid:
                    obj_type = "ISD"
                elif privileges & 0x20:  # Delegated Management
                    obj_type = "DMSD"
                else:
                    obj_type = "SSD"
            
            obj_info = {
                'aid': aid,
                'life_cycle': life_cycle,
                'privileges': privileges,
                'type': obj_type
            }
            
            objects.append(obj_info)
        
        return objects
    
    def list_applications(self) -> List[ApplicationInfo]:
        """List all installed applications"""
        status_data = self.get_status(p1=0x40)  # Applications and Security Domains
        applications = []
        
        for obj in status_data:
            if obj['type'] == 'Application':
                app_info = ApplicationInfo(
                    aid=obj['aid'],
                    life_cycle=LifeCycleState(obj['life_cycle']),
                    privileges=obj['privileges']
                )
                applications.append(app_info)
        
        logger.info(f"Found {len(applications)} applications")
        return applications
    
    def list_security_domains(self) -> List[SecurityDomainInfo]:
        """List all security domains"""
        status_data = self.get_status(p1=0x80)  # Security Domains only
        security_domains = []
        
        for obj in status_data:
            if obj['type'] in ['ISD', 'SSD', 'DMSD']:
                sd_info = SecurityDomainInfo(
                    aid=obj['aid'],
                    life_cycle=LifeCycleState(obj['life_cycle']),
                    privileges=obj['privileges'],
                    domain_type=obj['type'],
                    associated_applications=[]
                )
                security_domains.append(sd_info)
        
        logger.info(f"Found {len(security_domains)} security domains")
        return security_domains
    
    def create_security_domain(self, aid: bytes, domain_type: str, privileges: int = 0x80) -> bool:
        """
        Create a new security domain
        domain_type: 'SSD', 'AMSD', 'DMSD'
        """
        try:
            # INSTALL [for personalization and make selectable] command
            # This is a simplified implementation
            install_data = self._build_install_data(aid, domain_type, privileges)
            
            command = APDUCommand(
                cla=0x80,
                ins=0xE6,
                p1=0x0C,  # Install for personalization and make selectable
                p2=0x00,
                data=install_data
            )
            
            response = self.sc_manager.send_apdu(command)
            
            if response.is_success:
                logger.info(f"Successfully created {domain_type} with AID: {toHexString(aid)}")
                return True
            else:
                logger.error(f"Failed to create security domain: SW={response.sw:04X}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating security domain: {e}")
            return False
    
    def _build_install_data(self, aid: bytes, domain_type: str, privileges: int) -> bytes:
        """Build INSTALL command data"""
        # This is a simplified implementation
        # In practice, this would be more complex with proper TLV construction
        
        # Executable Load File AID (empty for SD creation)
        data = bytes([0])
        
        # Executable Module AID (empty for SD creation)
        data += bytes([0])
        
        # Application AID
        data += bytes([len(aid)]) + aid
        
        # Privileges
        data += bytes([1, privileges])  # Length + privileges
        
        # Install parameters (empty)
        data += bytes([0])
        
        # Install token (empty)
        data += bytes([0])
        
        return data
    
    def perform_clfdb(self, target_aid: bytes, operation: str) -> bool:
        """
        Perform Card Life Cycle Database operation
        operation: 'lock', 'unlock', 'terminate'
        """
        try:
            # SET STATUS command for life cycle changes
            p1_map = {
                'lock': 0x80,
                'unlock': 0x80,  
                'terminate': 0x80
            }
            
            data_map = {
                'lock': b'\x87',      # LOCKED
                'unlock': b'\x07',    # SELECTABLE
                'terminate': b'\xFF'   # TERMINATED
            }
            
            if operation not in p1_map:
                raise SmartcardException(f"Unknown CLFDB operation: {operation}")
            
            command_data = bytes([len(target_aid)]) + target_aid + data_map[operation]
            
            command = APDUCommand(
                cla=0x80,
                ins=0xF0,
                p1=p1_map[operation],
                p2=0x00,
                data=command_data
            )
            
            response = self.sc_manager.send_apdu(command)
            
            if response.is_success:
                logger.info(f"Successfully performed CLFDB {operation} on {toHexString(target_aid)}")
                return True
            else:
                logger.error(f"CLFDB {operation} failed: SW={response.sw:04X}")
                return False
                
        except Exception as e:
            logger.error(f"Error performing CLFDB: {e}")
            return False
    
    def extradite_object(self, object_aid: bytes, target_sd_aid: bytes) -> bool:
        """
        Extradite an application or security domain to another security domain
        """
        try:
            # This is a simplified extradition using SET STATUS command
            # Real implementation would require proper association management
            
            command_data = bytes([len(object_aid)]) + object_aid + bytes([len(target_sd_aid)]) + target_sd_aid
            
            command = APDUCommand(
                cla=0x80,
                ins=0xF0,
                p1=0x60,  # Set association
                p2=0x00,
                data=command_data
            )
            
            response = self.sc_manager.send_apdu(command)
            
            if response.is_success:
                logger.info(f"Successfully extradited {toHexString(object_aid)} to {toHexString(target_sd_aid)}")
                return True
            else:
                logger.error(f"Extradition failed: SW={response.sw:04X}")
                return False
                
        except Exception as e:
            logger.error(f"Error performing extradition: {e}")
            return False
    
    def get_card_info(self) -> Dict[str, Any]:
        """Get general card information"""
        info = {}
        
        try:
            # Get Card Production Life Cycle Data
            cplc_data = self.sc_manager.get_card_data(0x9F7F)
            if cplc_data:
                info['cplc'] = toHexString(cplc_data)
            
            # Get Card Recognition Data
            card_data = self.sc_manager.get_card_data(0x0066)
            if card_data:
                info['card_recognition'] = toHexString(card_data)
            
            # Get Key Information Template
            key_info = self.sc_manager.get_card_data(0x00E0)
            if key_info:
                info['key_info'] = toHexString(key_info)
                
        except Exception as e:
            logger.error(f"Error getting card info: {e}")
        
        return info
