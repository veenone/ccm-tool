"""
Test suite for the Smartcard Management Tool.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from smartcard_manager import SmartcardManager, APDUCommand, APDUResponse, SmartcardException
from globalplatform import GlobalPlatformManager, SecurityDomainInfo, ApplicationInfo, LifeCycleState
from secure_channel import SecureChannelManager, KeySet
from config_manager import ConfigManager


class TestAPDUCommand(unittest.TestCase):
    """Test APDU command functionality"""
    
    def test_apdu_command_creation(self):
        """Test APDU command creation"""
        cmd = APDUCommand(0x80, 0xF2, 0x80, 0x00, b'\x00', 0x00)
        self.assertEqual(cmd.cla, 0x80)
        self.assertEqual(cmd.ins, 0xF2)
        self.assertEqual(cmd.p1, 0x80)
        self.assertEqual(cmd.p2, 0x00)
        self.assertEqual(cmd.data, b'\x00')
        self.assertEqual(cmd.le, 0x00)
    
    def test_apdu_to_bytes(self):
        """Test APDU command to bytes conversion"""
        cmd = APDUCommand(0x80, 0xF2, 0x80, 0x00, b'\x04\x01\x02\x03', 0x00)
        bytes_data = cmd.to_bytes()
        expected = [0x80, 0xF2, 0x80, 0x00, 0x04, 0x01, 0x02, 0x03, 0x00]
        self.assertEqual(bytes_data, expected)


class TestAPDUResponse(unittest.TestCase):
    """Test APDU response functionality"""
    
    def test_success_response(self):
        """Test successful APDU response"""
        response = APDUResponse([0x01, 0x02, 0x03, 0x90, 0x00])
        self.assertTrue(response.is_success)
        self.assertEqual(response.data, b'\x01\x02\x03')
        self.assertEqual(response.sw1, 0x90)
        self.assertEqual(response.sw2, 0x00)
        self.assertEqual(response.sw, 0x9000)
    
    def test_error_response(self):
        """Test error APDU response"""
        response = APDUResponse([0x6A, 0x82])
        self.assertFalse(response.is_success)
        self.assertEqual(response.data, b'')
        self.assertEqual(response.sw, 0x6A82)
    
    def test_warning_response(self):
        """Test warning APDU response"""
        response = APDUResponse([0x01, 0x02, 0x63, 0x00])
        self.assertTrue(response.is_warning)
        self.assertFalse(response.is_success)


class TestKeySet(unittest.TestCase):
    """Test KeySet functionality"""
    
    def test_keyset_from_hex(self):
        """Test KeySet creation from hex strings"""
        keyset = KeySet.from_hex(
            enc_hex="404142434445464748494A4B4C4D4E4F",
            mac_hex="404142434445464748494A4B4C4D4E4F",
            dek_hex="404142434445464748494A4B4C4D4E4F",
            key_version=1,
            protocol="SCP03"
        )
        
        self.assertEqual(keyset.key_version, 1)
        self.assertEqual(keyset.protocol, "SCP03")
        self.assertEqual(len(keyset.enc_key), 16)
        self.assertEqual(len(keyset.mac_key), 16)
        self.assertEqual(len(keyset.dek_key), 16)


class TestConfigManager(unittest.TestCase):
    """Test configuration manager"""
    
    def setUp(self):
        """Set up test configuration"""
        self.config_dir = os.path.join(os.path.dirname(__file__), 'test_config')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Create test keysets file
        keysets_content = """
keysets:
  test_keyset:
    protocol: "SCP03"
    enc_key: "404142434445464748494A4B4C4D4E4F"
    mac_key: "404142434445464748494A4B4C4D4E4F"
    dek_key: "404142434445464748494A4B4C4D4E4F"
    key_version: 1
"""
        
        with open(os.path.join(self.config_dir, 'keysets.yaml'), 'w') as f:
            f.write(keysets_content)
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)
    
    def test_load_keysets(self):
        """Test loading keysets from configuration"""
        config_manager = ConfigManager(self.config_dir)
        keysets = config_manager.list_keysets()
        self.assertIn('test_keyset', keysets)
        
        keyset = config_manager.get_keyset('test_keyset')
        self.assertIsNotNone(keyset)
        self.assertEqual(keyset.protocol, 'SCP03')
        self.assertEqual(keyset.key_version, 1)
    
    def test_validate_keyset(self):
        """Test keyset validation"""
        config_manager = ConfigManager(self.config_dir)
        
        valid_keyset = {
            'protocol': 'SCP03',
            'enc_key': '404142434445464748494A4B4C4D4E4F',
            'mac_key': '404142434445464748494A4B4C4D4E4F',
            'dek_key': '404142434445464748494A4B4C4D4E4F',
            'key_version': 1
        }
        
        self.assertTrue(config_manager.validate_keyset(valid_keyset))
        
        # Test invalid keyset
        invalid_keyset = {
            'protocol': 'INVALID',
            'enc_key': 'SHORTKEY',
            'key_version': -1
        }
        
        self.assertFalse(config_manager.validate_keyset(invalid_keyset))


class TestSmartcardManager(unittest.TestCase):
    """Test smartcard manager with mocked PC/SC"""
    
    @patch('src.smartcard_manager.readers')
    def test_list_readers(self, mock_readers):
        """Test listing PC/SC readers"""
        mock_readers.return_value = ['Reader 1', 'Reader 2']
        
        sc_manager = SmartcardManager()
        readers = sc_manager.list_readers()
        
        self.assertEqual(len(readers), 2)
        self.assertIn('Reader 1', readers)
        self.assertIn('Reader 2', readers)
    
    def test_select_application(self):
        """Test application selection"""
        sc_manager = SmartcardManager()
        
        # Mock active reader
        mock_reader = Mock()
        mock_response = Mock()
        mock_response.is_success = True
        mock_reader.send_apdu.return_value = mock_response
        sc_manager.active_reader = mock_reader
        
        aid = bytes.fromhex('A000000151000000')
        response = sc_manager.select_application(aid)
        
        self.assertTrue(response.is_success)
        mock_reader.send_apdu.assert_called_once()


class TestGlobalPlatformManager(unittest.TestCase):
    """Test GlobalPlatform manager"""
    
    def setUp(self):
        """Set up test GlobalPlatform manager"""
        self.mock_sc_manager = Mock()
        self.gp_manager = GlobalPlatformManager(self.mock_sc_manager)
    
    def test_parse_status_response(self):
        """Test parsing GET STATUS response"""
        # Mock response data (simplified)
        response_data = bytes([
            0x08,  # AID length
            0xA0, 0x00, 0x00, 0x01, 0x51, 0x00, 0x00, 0x00,  # AID
            0x0F,  # Life cycle
            0x80   # Privileges
        ])
        
        objects = self.gp_manager._parse_status_response(response_data)
        
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]['life_cycle'], 0x0F)
        self.assertEqual(objects[0]['privileges'], 0x80)
        self.assertEqual(objects[0]['type'], 'ISD')


class TestSecureChannelManager(unittest.TestCase):
    """Test secure channel functionality"""
    
    def setUp(self):
        """Set up test secure channel manager"""
        self.mock_sc_manager = Mock()
        self.sc_manager = SecureChannelManager(self.mock_sc_manager)
    
    def test_kdf_scp03(self):
        """Test SCP03 Key Derivation Function"""
        key = bytes.fromhex('404142434445464748494A4B4C4D4E4F')
        context = bytes.fromhex('0102030405060708')
        label = bytes.fromhex('00000004')
        
        derived_key = self.sc_manager._kdf_scp03(key, context, label, 16)
        
        self.assertEqual(len(derived_key), 16)
        self.assertIsInstance(derived_key, bytes)
    
    def test_close_secure_channel(self):
        """Test closing secure channel"""
        # Set up a mock session
        self.sc_manager.session = Mock()
        
        self.sc_manager.close_secure_channel()
        
        self.assertIsNone(self.sc_manager.session)


if __name__ == '__main__':
    # Create test suite
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestAPDUCommand))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestAPDUResponse))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestKeySet))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestConfigManager))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestSmartcardManager))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestGlobalPlatformManager))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestSecureChannelManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
