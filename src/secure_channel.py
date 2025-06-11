"""
Secure Channel Protocol implementation for SCP02 and SCP03.
Handles secure channel establishment and secure APDU communication.
"""

import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, cmac
from cryptography.hazmat.backends import default_backend
import os
import struct
from .smartcard_manager import SmartcardManager, APDUCommand, APDUResponse, SmartcardException
from smartcard.util import toHexString, toBytes

logger = logging.getLogger(__name__)


@dataclass
class KeySet:
    """Represents a set of cryptographic keys"""
    enc_key: bytes
    mac_key: bytes
    dek_key: bytes  # Data Encryption Key
    key_version: int
    protocol: str  # SCP02 or SCP03
    
    @classmethod
    def from_hex(cls, enc_hex: str, mac_hex: str, dek_hex: str, key_version: int, protocol: str) -> 'KeySet':
        """Create KeySet from hex strings"""
        return cls(
            enc_key=bytes.fromhex(enc_hex),
            mac_key=bytes.fromhex(mac_hex),
            dek_key=bytes.fromhex(dek_hex),
            key_version=key_version,
            protocol=protocol
        )


@dataclass
class SecureChannelSession:
    """Represents an active secure channel session"""
    protocol: str
    security_level: int
    session_keys: Dict[str, bytes]
    sequence_counter: int
    mac_chaining_value: bytes
    
    def increment_sequence(self):
        """Increment sequence counter for SCP03"""
        self.sequence_counter = (self.sequence_counter + 1) & 0xFFFFFF


class SecureChannelManager:
    """Manages secure channel protocols (SCP02/SCP03)"""
    
    def __init__(self, smartcard_manager: SmartcardManager):
        self.sc_manager = smartcard_manager
        self.session: Optional[SecureChannelSession] = None
        self.backend = default_backend()
    
    def establish_secure_channel(self, keyset: KeySet, security_level: int = 3) -> bool:
        """
        Establish secure channel with the card
        security_level: 1=MAC, 2=MAC+ENC, 3=MAC+ENC+RMAC
        """
        try:
            if keyset.protocol == "SCP02":
                return self._establish_scp02(keyset, security_level)
            elif keyset.protocol == "SCP03":
                return self._establish_scp03(keyset, security_level)
            else:
                raise SmartcardException(f"Unsupported protocol: {keyset.protocol}")
        except Exception as e:
            logger.error(f"Error establishing secure channel: {e}")
            return False
    
    def _establish_scp02(self, keyset: KeySet, security_level: int) -> bool:
        """Establish SCP02 secure channel"""
        logger.info("Establishing SCP02 secure channel")
        
        # Step 1: INITIALIZE UPDATE
        host_challenge = os.urandom(8)
        
        command = APDUCommand(
            cla=0x80,
            ins=0x50,
            p1=keyset.key_version,
            p2=0x00,
            data=host_challenge,
            le=0x00
        )
        
        response = self.sc_manager.send_apdu(command)
        if not response.is_success:
            logger.error(f"INITIALIZE UPDATE failed: SW={response.sw:04X}")
            return False
        
        if len(response.data) < 28:
            logger.error("Invalid INITIALIZE UPDATE response length")
            return False
        
        # Parse response
        key_diversification_data = response.data[0:10]
        key_version = response.data[10]
        scp_id = response.data[11]
        card_challenge = response.data[12:20]
        card_cryptogram = response.data[20:28]
        
        # Derive session keys
        session_keys = self._derive_scp02_keys(
            keyset, key_diversification_data, host_challenge, card_challenge
        )
        
        # Verify card cryptogram
        if not self._verify_scp02_cryptogram(session_keys, host_challenge, card_challenge, card_cryptogram):
            logger.error("Card cryptogram verification failed")
            return False
        
        # Step 2: EXTERNAL AUTHENTICATE
        host_cryptogram = self._calculate_scp02_host_cryptogram(
            session_keys, host_challenge, card_challenge
        )
        
        command = APDUCommand(
            cla=0x84,  # Secure messaging
            ins=0x82,
            p1=security_level,
            p2=0x00,
            data=host_cryptogram
        )
        
        # Apply MAC for secure messaging
        command = self._apply_scp02_mac(command, session_keys)
        
        response = self.sc_manager.send_apdu(command)
        if not response.is_success:
            logger.error(f"EXTERNAL AUTHENTICATE failed: SW={response.sw:04X}")
            return False
        
        # Create session
        self.session = SecureChannelSession(
            protocol="SCP02",
            security_level=security_level,
            session_keys=session_keys,
            sequence_counter=0,
            mac_chaining_value=b'\x00' * 8
        )
        
        logger.info("SCP02 secure channel established successfully")
        return True
    
    def _establish_scp03(self, keyset: KeySet, security_level: int) -> bool:
        """Establish SCP03 secure channel"""
        logger.info("Establishing SCP03 secure channel")
        
        # Step 1: INITIALIZE UPDATE
        host_challenge = os.urandom(8)
        
        command = APDUCommand(
            cla=0x80,
            ins=0x50,
            p1=keyset.key_version,
            p2=0x00,
            data=host_challenge,
            le=0x00
        )
        
        response = self.sc_manager.send_apdu(command)
        if not response.is_success:
            logger.error(f"INITIALIZE UPDATE failed: SW={response.sw:04X}")
            return False
        
        if len(response.data) < 29:
            logger.error("Invalid INITIALIZE UPDATE response length")
            return False
        
        # Parse response
        key_diversification_data = response.data[0:10]
        key_version = response.data[10]
        scp_id = response.data[11]
        sequence_counter = struct.unpack('>I', b'\x00' + response.data[12:15])[0]
        card_challenge = response.data[15:23]
        card_cryptogram = response.data[23:31]
        
        # Derive session keys
        session_keys = self._derive_scp03_keys(
            keyset, host_challenge, card_challenge, key_diversification_data
        )
        
        # Verify card cryptogram
        if not self._verify_scp03_cryptogram(
            session_keys, host_challenge, card_challenge, card_cryptogram, sequence_counter
        ):
            logger.error("Card cryptogram verification failed")
            return False
        
        # Step 2: EXTERNAL AUTHENTICATE
        host_cryptogram = self._calculate_scp03_host_cryptogram(
            session_keys, host_challenge, card_challenge, sequence_counter
        )
        
        command = APDUCommand(
            cla=0x84,  # Secure messaging
            ins=0x82,
            p1=security_level,
            p2=0x00,
            data=host_cryptogram
        )
        
        # Apply MAC for secure messaging
        command = self._apply_scp03_mac(command, session_keys, sequence_counter)
        
        response = self.sc_manager.send_apdu(command)
        if not response.is_success:
            logger.error(f"EXTERNAL AUTHENTICATE failed: SW={response.sw:04X}")
            return False
        
        # Create session
        self.session = SecureChannelSession(
            protocol="SCP03",
            security_level=security_level,
            session_keys=session_keys,
            sequence_counter=sequence_counter,
            mac_chaining_value=b'\x00' * 16
        )
        
        logger.info("SCP03 secure channel established successfully")
        return True
    
    def _derive_scp02_keys(self, keyset: KeySet, kdd: bytes, host_challenge: bytes, card_challenge: bytes) -> Dict[str, bytes]:
        """Derive SCP02 session keys"""
        # This is a simplified implementation
        # Real SCP02 key derivation is more complex
        
        derivation_data = card_challenge + host_challenge
        
        # Derive ENC session key
        enc_key = self._encrypt_des3(keyset.enc_key, derivation_data + b'\x01\x82')[:16]
        
        # Derive MAC session key  
        mac_key = self._encrypt_des3(keyset.mac_key, derivation_data + b'\x01\x01')[:16]
        
        # Derive KEK (Key Encryption Key)
        kek_key = self._encrypt_des3(keyset.dek_key, derivation_data + b'\x01\x81')[:16]
        
        return {
            'enc': enc_key,
            'mac': mac_key,
            'kek': kek_key
        }
    
    def _derive_scp03_keys(self, keyset: KeySet, host_challenge: bytes, card_challenge: bytes, kdd: bytes) -> Dict[str, bytes]:
        """Derive SCP03 session keys using KDF"""
        context = host_challenge + card_challenge
        
        # Derive session keys using CMAC-based KDF
        enc_key = self._kdf_scp03(keyset.enc_key, context, b'\x00\x00\x00\x04', 16)
        mac_key = self._kdf_scp03(keyset.mac_key, context, b'\x00\x00\x00\x06', 16)
        rmac_key = self._kdf_scp03(keyset.mac_key, context, b'\x00\x00\x00\x07', 16)
        
        return {
            'enc': enc_key,
            'mac': mac_key,
            'rmac': rmac_key
        }
    
    def _kdf_scp03(self, key: bytes, context: bytes, label: bytes, length: int) -> bytes:
        """SCP03 Key Derivation Function"""
        # KDF as per SCP03 specification
        input_data = label + b'\x00' + context + struct.pack('>H', length * 8)
        
        c = cmac.CMAC(algorithms.AES(key), backend=self.backend)
        c.update(input_data)
        return c.finalize()[:length]
    
    def _encrypt_des3(self, key: bytes, data: bytes) -> bytes:
        """3DES encryption helper"""
        # Ensure key is 24 bytes for 3DES
        if len(key) == 16:
            key = key + key[:8]
        
        cipher = Cipher(algorithms.TripleDES(key), modes.ECB(), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # Pad data to 8-byte boundary
        padded_data = data + b'\x00' * (8 - len(data) % 8)
        
        return encryptor.update(padded_data) + encryptor.finalize()
    
    def _verify_scp02_cryptogram(self, session_keys: Dict[str, bytes], host_challenge: bytes, 
                                card_challenge: bytes, card_cryptogram: bytes) -> bool:
        """Verify SCP02 card cryptogram"""
        # Simplified cryptogram verification
        expected_data = host_challenge + card_challenge + b'\x80\x00\x00\x00\x00\x00\x00\x00'
        expected_cryptogram = self._encrypt_des3(session_keys['enc'], expected_data)[:8]
        
        return expected_cryptogram == card_cryptogram
    
    def _verify_scp03_cryptogram(self, session_keys: Dict[str, bytes], host_challenge: bytes,
                                card_challenge: bytes, card_cryptogram: bytes, sequence_counter: int) -> bool:
        """Verify SCP03 card cryptogram"""
        # Build cryptogram data
        cryptogram_data = (host_challenge + 
                          struct.pack('>I', sequence_counter)[1:] + 
                          card_challenge + 
                          b'\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # Calculate expected cryptogram using CMAC
        c = cmac.CMAC(algorithms.AES(session_keys['enc']), backend=self.backend)
        c.update(cryptogram_data)
        expected_cryptogram = c.finalize()[:8]
        
        return expected_cryptogram == card_cryptogram
    
    def _calculate_scp02_host_cryptogram(self, session_keys: Dict[str, bytes], 
                                       host_challenge: bytes, card_challenge: bytes) -> bytes:
        """Calculate SCP02 host cryptogram"""
        cryptogram_data = card_challenge + host_challenge + b'\x80\x00\x00\x00\x00\x00\x00\x00'
        return self._encrypt_des3(session_keys['enc'], cryptogram_data)[:8]
    
    def _calculate_scp03_host_cryptogram(self, session_keys: Dict[str, bytes], 
                                       host_challenge: bytes, card_challenge: bytes, 
                                       sequence_counter: int) -> bytes:
        """Calculate SCP03 host cryptogram"""
        cryptogram_data = (card_challenge + 
                          struct.pack('>I', sequence_counter)[1:] + 
                          host_challenge + 
                          b'\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        
        c = cmac.CMAC(algorithms.AES(session_keys['enc']), backend=self.backend)
        c.update(cryptogram_data)
        return c.finalize()[:8]
    
    def _apply_scp02_mac(self, command: APDUCommand, session_keys: Dict[str, bytes]) -> APDUCommand:
        """Apply SCP02 MAC to APDU command"""
        # Simplified MAC calculation
        # Real implementation would use proper MAC chaining
        
        apdu_data = bytes([command.cla, command.ins, command.p1, command.p2, len(command.data)]) + command.data
        mac_data = apdu_data + b'\x80\x00\x00\x00\x00\x00\x00\x00'
        
        mac = self._encrypt_des3(session_keys['mac'], mac_data)[:8]
        
        # Append MAC to command data
        new_data = command.data + mac
        
        return APDUCommand(
            cla=command.cla,
            ins=command.ins,
            p1=command.p1,
            p2=command.p2,
            data=new_data,
            le=command.le
        )
    
    def _apply_scp03_mac(self, command: APDUCommand, session_keys: Dict[str, bytes], sequence_counter: int) -> APDUCommand:
        """Apply SCP03 MAC to APDU command"""
        # Build MAC data
        mac_data = (struct.pack('>I', sequence_counter)[1:] +
                   bytes([command.cla, command.ins, command.p1, command.p2]) +
                   bytes([len(command.data)]) + command.data)
        
        # Calculate CMAC
        c = cmac.CMAC(algorithms.AES(session_keys['mac']), backend=self.backend)
        c.update(mac_data)
        mac = c.finalize()[:8]
        
        # Append MAC to command data
        new_data = command.data + mac
        
        return APDUCommand(
            cla=command.cla,
            ins=command.ins,
            p1=command.p1,
            p2=command.p2,
            data=new_data,
            le=command.le
        )
    
    def send_secure_apdu(self, command: APDUCommand) -> APDUResponse:
        """Send APDU through secure channel"""
        if not self.session:
            raise SmartcardException("No active secure channel")
        
        # Apply security based on protocol and security level
        if self.session.protocol == "SCP02":
            secure_command = self._apply_scp02_mac(command, self.session.session_keys)
        elif self.session.protocol == "SCP03":
            self.session.increment_sequence()
            secure_command = self._apply_scp03_mac(
                command, self.session.session_keys, self.session.sequence_counter
            )
        else:
            raise SmartcardException(f"Unsupported protocol: {self.session.protocol}")
        
        # Encrypt command data if required by security level
        if self.session.security_level >= 2:
            secure_command = self._encrypt_command_data(secure_command)
        
        # Send the secure command
        response = self.sc_manager.send_apdu(secure_command)
        
        # Decrypt response data if required
        if self.session.security_level >= 2 and response.data:
            response.data = self._decrypt_response_data(response.data)
        
        return response
    
    def _encrypt_command_data(self, command: APDUCommand) -> APDUCommand:
        """Encrypt command data for secure messaging"""
        if not command.data:
            return command
        
        # This is a simplified implementation
        # Real implementation would use proper padding and encryption
        
        if self.session.protocol == "SCP02":
            encrypted_data = self._encrypt_des3(self.session.session_keys['enc'], command.data)
        elif self.session.protocol == "SCP03":
            # AES encryption for SCP03
            cipher = Cipher(algorithms.AES(self.session.session_keys['enc']), 
                          modes.CBC(b'\x00' * 16), backend=self.backend)
            encryptor = cipher.encryptor()
            
            # Pad data to 16-byte boundary
            padded_data = command.data + b'\x80' + b'\x00' * (15 - len(command.data) % 16)
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        return APDUCommand(
            cla=command.cla,
            ins=command.ins,
            p1=command.p1,
            p2=command.p2,
            data=encrypted_data,
            le=command.le
        )
    
    def _decrypt_response_data(self, data: bytes) -> bytes:
        """Decrypt response data from secure messaging"""
        # Simplified decryption implementation
        if self.session.protocol == "SCP02":
            # 3DES decryption
            cipher = Cipher(algorithms.TripleDES(self.session.session_keys['enc']), 
                          modes.ECB(), backend=self.backend)
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(data) + decryptor.finalize()
        elif self.session.protocol == "SCP03":
            # AES decryption
            cipher = Cipher(algorithms.AES(self.session.session_keys['enc']), 
                          modes.CBC(b'\x00' * 16), backend=self.backend)
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(data) + decryptor.finalize()
            
            # Remove padding
            if decrypted and decrypted[-1] == 0x80:
                decrypted = decrypted[:-1]
            elif decrypted:
                # Remove PKCS#7 padding
                pad_length = decrypted[-1]
                decrypted = decrypted[:-pad_length]
        
        return decrypted
    
    def close_secure_channel(self):
        """Close the secure channel"""
        self.session = None
        logger.info("Secure channel closed")
    
    def is_secure_channel_active(self) -> bool:
        """Check if secure channel is active"""
        return self.session is not None
