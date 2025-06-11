"""
Core smartcard management module using PC/SC interface.
Provides low-level smartcard communication and basic operations.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.Exceptions import CardRequestTimeoutException, CardConnectionException
from smartcard.util import toHexString, toBytes
import time

logger = logging.getLogger(__name__)


class SmartcardException(Exception):
    """Custom exception for smartcard operations"""
    pass


class APDUCommand:
    """Represents an APDU command"""
    
    def __init__(self, cla: int, ins: int, p1: int, p2: int, data: bytes = b'', le: int = 0):
        self.cla = cla
        self.ins = ins
        self.p1 = p1
        self.p2 = p2
        self.data = data
        self.le = le
    
    def to_bytes(self) -> List[int]:
        """Convert APDU to byte list for transmission"""
        apdu = [self.cla, self.ins, self.p1, self.p2]
        
        if self.data:
            apdu.append(len(self.data))
            apdu.extend(list(self.data))
        
        if self.le > 0:
            apdu.append(self.le)
        
        return apdu
    
    def __str__(self) -> str:
        return f"APDU({self.cla:02X} {self.ins:02X} {self.p1:02X} {self.p2:02X} {toHexString(self.data)} {self.le:02X})"


class APDUResponse:
    """Represents an APDU response"""
    
    def __init__(self, data: List[int]):
        if len(data) < 2:
            raise SmartcardException("Invalid APDU response length")
        
        self.data = bytes(data[:-2])
        self.sw1 = data[-2]
        self.sw2 = data[-1]
        self.sw = (self.sw1 << 8) | self.sw2
    
    @property
    def is_success(self) -> bool:
        """Check if the response indicates success"""
        return self.sw == 0x9000
    
    @property
    def is_warning(self) -> bool:
        """Check if the response is a warning"""
        return 0x6200 <= self.sw <= 0x62FF or 0x6300 <= self.sw <= 0x63FF
    
    def __str__(self) -> str:
        return f"Response({toHexString(self.data)} {self.sw1:02X}{self.sw2:02X})"


class SmartcardReader:
    """Manages connection to a single smartcard reader"""
    
    def __init__(self, reader_name: str):
        self.reader_name = reader_name
        self.connection: Optional[CardConnection] = None
        self.connected = False
        
    def connect(self, timeout: int = 5000) -> bool:
        """Connect to the smartcard in the reader"""
        try:
            cardtype = AnyCardType()
            cardrequest = CardRequest(
                readers=[self.reader_name],
                cardType=cardtype,
                timeout=timeout
            )
            
            cardservice = cardrequest.waitforcard()
            self.connection = cardservice.connection
            self.connection.connect()
            self.connected = True
            
            logger.info(f"Connected to card in reader: {self.reader_name}")
            logger.info(f"Card ATR: {toHexString(self.connection.getATR())}")
            
            return True
            
        except CardRequestTimeoutException:
            logger.error(f"Timeout waiting for card in reader: {self.reader_name}")
            return False
        except CardConnectionException as e:
            logger.error(f"Failed to connect to card: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the smartcard"""
        if self.connection and self.connected:
            try:
                self.connection.disconnect()
                self.connected = False
                logger.info(f"Disconnected from reader: {self.reader_name}")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    def send_apdu(self, command: APDUCommand) -> APDUResponse:
        """Send APDU command to the card"""
        if not self.connected or not self.connection:
            raise SmartcardException("Not connected to card")
        
        try:
            apdu_bytes = command.to_bytes()
            logger.debug(f"Sending APDU: {toHexString(apdu_bytes)}")
            
            response, sw1, sw2 = self.connection.transmit(apdu_bytes)
            response.extend([sw1, sw2])
            
            apdu_response = APDUResponse(response)
            logger.debug(f"Received: {apdu_response}")
            
            return apdu_response
            
        except Exception as e:
            logger.error(f"Error sending APDU: {e}")
            raise SmartcardException(f"APDU transmission failed: {e}")
    
    def get_atr(self) -> bytes:
        """Get the Answer to Reset from the card"""
        if not self.connected or not self.connection:
            raise SmartcardException("Not connected to card")
        
        return bytes(self.connection.getATR())


class SmartcardManager:
    """High-level smartcard management interface"""
    
    def __init__(self):
        self.readers: Dict[str, SmartcardReader] = {}
        self.active_reader: Optional[SmartcardReader] = None
        
    def list_readers(self) -> List[str]:
        """List all available PC/SC readers"""
        try:
            reader_list = readers()
            reader_names = [str(reader) for reader in reader_list]
            logger.info(f"Found {len(reader_names)} readers: {reader_names}")
            return reader_names
        except Exception as e:
            logger.error(f"Error listing readers: {e}")
            return []
    
    def connect_to_reader(self, reader_name: str, timeout: int = 5000) -> bool:
        """Connect to a specific reader"""
        if reader_name not in self.readers:
            self.readers[reader_name] = SmartcardReader(reader_name)
        
        reader = self.readers[reader_name]
        if reader.connect(timeout):
            self.active_reader = reader
            return True
        
        return False
    
    def disconnect_all(self):
        """Disconnect from all readers"""
        for reader in self.readers.values():
            reader.disconnect()
        self.active_reader = None
    
    def send_apdu(self, command: APDUCommand) -> APDUResponse:
        """Send APDU to the active reader"""
        if not self.active_reader:
            raise SmartcardException("No active reader connection")
        
        return self.active_reader.send_apdu(command)
    
    def select_application(self, aid: bytes) -> APDUResponse:
        """Select an application by AID"""
        command = APDUCommand(
            cla=0x00,
            ins=0xA4,
            p1=0x04,
            p2=0x00,
            data=aid,
            le=0x00
        )
        
        response = self.send_apdu(command)
        if response.is_success:
            logger.info(f"Successfully selected application: {toHexString(aid)}")
        else:
            logger.warning(f"Failed to select application: {toHexString(aid)}, SW: {response.sw:04X}")
        
        return response
    
    def get_card_data(self, tag: int, max_length: int = 255) -> Optional[bytes]:
        """Get card data using GET DATA command"""
        command = APDUCommand(
            cla=0x80,
            ins=0xCA,
            p1=(tag >> 8) & 0xFF,
            p2=tag & 0xFF,
            le=max_length
        )
        
        response = self.send_apdu(command)
        if response.is_success:
            return response.data
        
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect_all()
