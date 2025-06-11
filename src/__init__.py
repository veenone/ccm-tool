"""
Smartcard Management Tool - Main Package
A comprehensive Python tool for managing smartcards through PC/SC readers.
"""

__version__ = "1.0.0"
__author__ = "CCM Tool Developer"
__email__ = "developer@example.com"

from .smartcard_manager import SmartcardManager, APDUCommand, APDUResponse, SmartcardException
from .globalplatform import GlobalPlatformManager, SecurityDomainInfo, ApplicationInfo, LifeCycleState
from .secure_channel import SecureChannelManager, KeySet, SecureChannelSession
from .config_manager import ConfigManager
from .visualization import SecurityDomainVisualizer

__all__ = [
    'SmartcardManager',
    'GlobalPlatformManager', 
    'SecureChannelManager',
    'ConfigManager',
    'SecurityDomainVisualizer',
    'APDUCommand',
    'APDUResponse',
    'SmartcardException',
    'SecurityDomainInfo',
    'ApplicationInfo',
    'LifeCycleState',
    'KeySet',
    'SecureChannelSession'
]
