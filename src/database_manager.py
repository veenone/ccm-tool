"""
Database manager for storing configurable keysets and OTA message templates.
Provides SQLite-based storage for multiple keyset value sets and SMS-PP envelope management.
"""

import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)


@dataclass
class KeysetRecord:
    """Represents a keyset record in the database"""
    id: Optional[int]
    name: str
    value_set: str  # Group/category name for organizing keysets
    protocol: str  # SCP02 or SCP03
    enc_key: str  # Hex string
    mac_key: str  # Hex string
    dek_key: str  # Hex string
    key_version: int
    security_level: int
    description: str
    created_at: str
    updated_at: str
    is_active: bool = True


@dataclass
class OTAMessageTemplate:
    """Represents an OTA SMS-PP message template"""
    id: Optional[int]
    name: str
    template_type: str  # CLFDB, INSTALL, DELETE, etc.
    spi: str  # Security Parameter Indicator
    kad: str  # Key Access Domain
    tar: str  # Toolkit Application Reference
    cntr: str  # Counter
    pcntr: str  # Padding Counter
    command_template: str  # Command template with placeholders
    description: str
    created_at: str
    updated_at: str
    is_active: bool = True


@dataclass
class OTAMessage:
    """Represents a generated OTA message"""
    id: Optional[int]
    template_id: int
    target_aid: str
    operation: str  # LOCK, UNLOCK, TERMINATE, MAKE_SELECTABLE
    parameters: str  # JSON string of additional parameters
    sms_tpdu: str  # Complete SMS-PP TPDU in hex
    udh: str  # User Data Header
    user_data: str  # User data payload
    created_at: str
    status: str = "PENDING"  # PENDING, SENT, DELIVERED, FAILED


class DatabaseManager:
    """Manages SQLite database for keysets and OTA messages"""
    
    def __init__(self, db_path: str = "data/smartcard_tool.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create keysets table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keysets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        value_set TEXT NOT NULL,
                        protocol TEXT NOT NULL CHECK (protocol IN ('SCP02', 'SCP03')),
                        enc_key TEXT NOT NULL,
                        mac_key TEXT NOT NULL,
                        dek_key TEXT NOT NULL,
                        key_version INTEGER NOT NULL,
                        security_level INTEGER NOT NULL CHECK (security_level IN (1, 2, 3)),
                        description TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        UNIQUE(name, value_set)
                    )
                """)
                
                # Create OTA message templates table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ota_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        template_type TEXT NOT NULL,
                        spi TEXT NOT NULL,
                        kad TEXT NOT NULL,
                        tar TEXT NOT NULL,
                        cntr TEXT NOT NULL,
                        pcntr TEXT NOT NULL,
                        command_template TEXT NOT NULL,
                        description TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """)
                
                # Create OTA messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ota_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_id INTEGER NOT NULL,
                        target_aid TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        parameters TEXT,
                        sms_tpdu TEXT NOT NULL,
                        udh TEXT NOT NULL,
                        user_data TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        FOREIGN KEY (template_id) REFERENCES ota_templates (id)
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_keysets_value_set ON keysets(value_set)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_keysets_protocol ON keysets(protocol)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ota_messages_status ON ota_messages(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ota_messages_target_aid ON ota_messages(target_aid)")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
                # Insert default templates if they don't exist
                self._insert_default_data(cursor)
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def _insert_default_data(self, cursor):
        """Insert default keysets and OTA templates"""
        current_time = datetime.now().isoformat()
        
        # Default keysets
        default_keysets = [
            {
                'name': 'default_scp02',
                'value_set': 'production',
                'protocol': 'SCP02',
                'enc_key': '404142434445464748494A4B4C4D4E4F',
                'mac_key': '404142434445464748494A4B4C4D4E4F',
                'dek_key': '404142434445464748494A4B4C4D4E4F',
                'key_version': 1,
                'security_level': 3,
                'description': 'Default SCP02 production keyset'
            },
            {
                'name': 'default_scp03',
                'value_set': 'production',
                'protocol': 'SCP03',
                'enc_key': '404142434445464748494A4B4C4D4E4F',
                'mac_key': '404142434445464748494A4B4C4D4E4F',
                'dek_key': '404142434445464748494A4B4C4D4E4F',
                'key_version': 1,
                'security_level': 3,
                'description': 'Default SCP03 production keyset'
            },
            {
                'name': 'test_scp03',
                'value_set': 'testing',
                'protocol': 'SCP03',
                'enc_key': '000102030405060708090A0B0C0D0E0F',
                'mac_key': '101112131415161718191A1B1C1D1E1F',
                'dek_key': '202122232425262728292A2B2C2D2E2F',
                'key_version': 2,
                'security_level': 1,
                'description': 'Test SCP03 keyset with different keys'
            }
        ]
        
        for keyset in default_keysets:
            cursor.execute("""
                INSERT OR IGNORE INTO keysets 
                (name, value_set, protocol, enc_key, mac_key, dek_key, key_version, 
                 security_level, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                keyset['name'], keyset['value_set'], keyset['protocol'],
                keyset['enc_key'], keyset['mac_key'], keyset['dek_key'],
                keyset['key_version'], keyset['security_level'], keyset['description'],
                current_time, current_time
            ))
        
        # Default OTA templates for CLFDB operations
        default_templates = [
            {
                'name': 'clfdb_lock',
                'template_type': 'CLFDB',
                'spi': '02',  # CC+DS
                'kad': '01',  # KID
                'tar': '000000',  # Default TAR
                'cntr': '000000',  # Counter placeholder
                'pcntr': '00',  # Padding counter
                'command_template': '80E600{lifecycle}14{aid_length}{aid}',
                'description': 'CLFDB LOCK operation template'
            },
            {
                'name': 'clfdb_unlock',
                'template_type': 'CLFDB',
                'spi': '02',
                'kad': '01',
                'tar': '000000',
                'cntr': '000000',
                'pcntr': '00',
                'command_template': '80E600{lifecycle}14{aid_length}{aid}',
                'description': 'CLFDB UNLOCK operation template'
            },
            {
                'name': 'clfdb_terminate',
                'template_type': 'CLFDB',
                'spi': '02',
                'kad': '01',
                'tar': '000000',
                'cntr': '000000',
                'pcntr': '00',
                'command_template': '80E600{lifecycle}14{aid_length}{aid}',
                'description': 'CLFDB TERMINATE operation template'
            },
            {
                'name': 'clfdb_make_selectable',
                'template_type': 'CLFDB',
                'spi': '02',
                'kad': '01',
                'tar': '000000',
                'cntr': '000000',
                'pcntr': '00',
                'command_template': '80E600{lifecycle}14{aid_length}{aid}',
                'description': 'CLFDB MAKE_SELECTABLE operation template'
            }
        ]
        
        for template in default_templates:
            cursor.execute("""
                INSERT OR IGNORE INTO ota_templates 
                (name, template_type, spi, kad, tar, cntr, pcntr, command_template, 
                 description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template['name'], template['template_type'], template['spi'],
                template['kad'], template['tar'], template['cntr'], template['pcntr'],
                template['command_template'], template['description'],
                current_time, current_time
            ))
    
    # Keyset Management Methods
    
    def add_keyset(self, keyset: KeysetRecord) -> int:
        """Add a new keyset to the database"""
        current_time = datetime.now().isoformat()
        keyset.created_at = current_time
        keyset.updated_at = current_time
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO keysets 
                    (name, value_set, protocol, enc_key, mac_key, dek_key, key_version, 
                     security_level, description, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    keyset.name, keyset.value_set, keyset.protocol,
                    keyset.enc_key, keyset.mac_key, keyset.dek_key,
                    keyset.key_version, keyset.security_level, keyset.description,
                    keyset.created_at, keyset.updated_at, keyset.is_active
                ))
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"Keyset already exists: {e}")
            raise ValueError(f"Keyset '{keyset.name}' already exists in value set '{keyset.value_set}'")
        except sqlite3.Error as e:
            logger.error(f"Database error adding keyset: {e}")
            raise
    
    def get_keysets(self, value_set: Optional[str] = None, 
                   protocol: Optional[str] = None) -> List[KeysetRecord]:
        """Get keysets filtered by value set and/or protocol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM keysets WHERE is_active = 1"
                params = []
                
                if value_set:
                    query += " AND value_set = ?"
                    params.append(value_set)
                
                if protocol:
                    query += " AND protocol = ?"
                    params.append(protocol)
                
                query += " ORDER BY value_set, name"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [KeysetRecord(*row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Database error getting keysets: {e}")
            return []
    
    def get_keyset_by_name(self, name: str, value_set: str) -> Optional[KeysetRecord]:
        """Get a specific keyset by name and value set"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM keysets 
                    WHERE name = ? AND value_set = ? AND is_active = 1
                """, (name, value_set))
                
                row = cursor.fetchone()
                return KeysetRecord(*row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Database error getting keyset: {e}")
            return None
    
    def update_keyset(self, keyset: KeysetRecord) -> bool:
        """Update an existing keyset"""
        keyset.updated_at = datetime.now().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE keysets SET
                        protocol = ?, enc_key = ?, mac_key = ?, dek_key = ?,
                        key_version = ?, security_level = ?, description = ?,
                        updated_at = ?, is_active = ?
                    WHERE id = ?
                """, (
                    keyset.protocol, keyset.enc_key, keyset.mac_key, keyset.dek_key,
                    keyset.key_version, keyset.security_level, keyset.description,
                    keyset.updated_at, keyset.is_active, keyset.id
                ))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Database error updating keyset: {e}")
            return False
    
    def delete_keyset(self, keyset_id: int) -> bool:
        """Soft delete a keyset (mark as inactive)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE keysets SET is_active = 0, updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), keyset_id))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Database error deleting keyset: {e}")
            return False
    
    def get_value_sets(self) -> List[str]:
        """Get all available value sets"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT value_set FROM keysets 
                    WHERE is_active = 1 ORDER BY value_set
                """)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error getting value sets: {e}")
            return []
    
    # OTA Template Management Methods
    
    def add_ota_template(self, template: OTAMessageTemplate) -> int:
        """Add a new OTA message template"""
        current_time = datetime.now().isoformat()
        template.created_at = current_time
        template.updated_at = current_time
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ota_templates 
                    (name, template_type, spi, kad, tar, cntr, pcntr, command_template,
                     description, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template.name, template.template_type, template.spi,
                    template.kad, template.tar, template.cntr, template.pcntr,
                    template.command_template, template.description,
                    template.created_at, template.updated_at, template.is_active
                ))
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"OTA template already exists: {e}")
            raise ValueError(f"OTA template '{template.name}' already exists")
        except sqlite3.Error as e:
            logger.error(f"Database error adding OTA template: {e}")
            raise
    
    def get_ota_templates(self, template_type: Optional[str] = None) -> List[OTAMessageTemplate]:
        """Get OTA templates filtered by type"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM ota_templates WHERE is_active = 1"
                params = []
                
                if template_type:
                    query += " AND template_type = ?"
                    params.append(template_type)
                
                query += " ORDER BY template_type, name"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [OTAMessageTemplate(*row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Database error getting OTA templates: {e}")
            return []
    
    def add_ota_message(self, message: OTAMessage) -> int:
        """Add a generated OTA message"""
        message.created_at = datetime.now().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ota_messages 
                    (template_id, target_aid, operation, parameters, sms_tpdu, udh,
                     user_data, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.template_id, message.target_aid, message.operation,
                    message.parameters, message.sms_tpdu, message.udh,
                    message.user_data, message.created_at, message.status
                ))
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Database error adding OTA message: {e}")
            raise
    
    def get_ota_messages(self, status: Optional[str] = None, 
                        target_aid: Optional[str] = None) -> List[OTAMessage]:
        """Get OTA messages filtered by status and/or target AID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM ota_messages WHERE 1=1"
                params = []
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                if target_aid:
                    query += " AND target_aid = ?"
                    params.append(target_aid)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [OTAMessage(*row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Database error getting OTA messages: {e}")
            return []
