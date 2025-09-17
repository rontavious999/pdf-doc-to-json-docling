"""
Field processing modules for PDF to JSON conversion.

This package contains modular components for processing form fields:
- FieldOrderingManager: Handles field ordering logic
- FieldNormalizationManager: Handles field normalization logic  
- ConsentShapingManager: Handles consent form specific processing
- HeaderFooterManager: Handles header/footer removal (eliminates duplication)
"""

from .field_ordering_manager import FieldOrderingManager, FieldInfo
from .field_normalization_manager import FieldNormalizationManager
from .consent_shaping_manager import ConsentShapingManager
from .header_footer_manager import HeaderFooterManager

__all__ = [
    'FieldOrderingManager',
    'FieldNormalizationManager', 
    'ConsentShapingManager',
    'HeaderFooterManager',
    'FieldInfo'
]