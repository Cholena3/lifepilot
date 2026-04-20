"""Property-based tests for emergency health information module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Property 33: Emergency Info QR Code Validity**
**Validates: Requirements 17.2, 17.3**
"""

import secrets
from typing import List, Optional
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.models.emergency_info import EmergencyInfo, EmergencyInfoField, BloodType
from app.schemas.emergency_info import (
    EmergencyInfoCreate,
    EmergencyInfoUpdate,
    EmergencyContact,
    VisibilityUpdate,
    PublicEmergencyInfoResponse,
)
from app.services.emergency_info import EmergencyInfoService


# ============================================================================
# Hypothesis Strategies for Emergency Info Data
# ============================================================================

@st.composite
def valid_blood_types(draw):
    """Generate valid blood types."""
    return draw(st.sampled_from(BloodType.ALL))


@st.composite
def valid_field_names(draw):
    """Generate valid emergency info field names."""
    return draw(st.sampled_from(EmergencyInfoField.ALL))


@st.composite
def valid_visible_fields_list(draw):
    """Generate a valid list of visible fields (subset of all fields)."""
    all_fields = EmergencyInfoField.ALL
    # Generate a subset of fields
    selected = draw(st.lists(
        st.sampled_from(all_fields),
        min_size=0,
        max_size=len(all_fields),
        unique=True,
    ))
    return selected


@st.composite
def valid_emergency_contact(draw):
    """Generate a valid emergency contact."""
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
    phone = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('N',))))
    relationship = draw(st.one_of(
        st.none(),
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))
    ))
    assume(name.strip())  # Ensure non-empty after strip
    assume(phone.strip())
    return EmergencyContact(name=name.strip(), phone=phone.strip(), relationship=relationship)


@st.composite
def valid_allergy_list(draw):
    """Generate a valid list of allergies."""
    return draw(st.lists(
        st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))).filter(lambda x: x.strip()),
        min_size=0,
        max_size=10,
    ))


@st.composite
def valid_medication_list(draw):
    """Generate a valid list of medications."""
    return draw(st.lists(
        st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))).filter(lambda x: x.strip()),
        min_size=0,
        max_size=10,
    ))


# ============================================================================
# Property 33: Emergency Info QR Code Validity
# ============================================================================

class TestEmergencyInfoQRCodeProperty:
    """Property 33: Emergency Info QR Code Validity.
    
    **Validates: Requirements 17.2, 17.3**
    
    For any emergency info record:
    - A unique public token SHALL be generated for each record
    - The QR code SHALL encode a valid URL containing the public token
    - Public access SHALL only return fields configured as visible
    - Fields not in visible_fields SHALL NOT appear in public response
    - Token regeneration SHALL produce a different token
    """
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50, deadline=None)
    def test_public_tokens_are_unique(self, count: int):
        """Each emergency info record SHALL have a unique public token.
        
        **Validates: Requirements 17.2**
        
        This test verifies that:
        1. Generated tokens are unique across multiple generations
        2. Tokens have sufficient entropy for security
        """
        tokens = set()
        for _ in range(count):
            token = EmergencyInfo.generate_public_token()
            assert token not in tokens, f"Duplicate token generated: {token}"
            tokens.add(token)
        
        # All tokens should be unique
        assert len(tokens) == count, "Not all generated tokens are unique"
    
    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=20, deadline=None)
    def test_public_token_has_sufficient_length(self, _: int):
        """Public tokens SHALL have sufficient length for security.
        
        **Validates: Requirements 17.2**
        
        This test verifies that:
        1. Tokens are at least 32 characters long
        2. Tokens are URL-safe (no special characters that need encoding)
        """
        token = EmergencyInfo.generate_public_token()
        
        # Token should be at least 32 characters (256 bits of entropy when base64 encoded)
        assert len(token) >= 32, f"Token too short: {len(token)} characters"
        
        # Token should be URL-safe (only alphanumeric, hyphen, underscore)
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', token), f"Token contains non-URL-safe characters: {token}"
    
    @given(visible_fields=valid_visible_fields_list())
    @settings(max_examples=50, deadline=None)
    def test_public_response_only_contains_visible_fields(
        self,
        visible_fields: List[str],
    ):
        """Public emergency info SHALL only contain fields marked as visible.
        
        **Validates: Requirements 17.3**
        
        This test verifies that:
        1. Only fields in visible_fields appear in public response
        2. Fields not in visible_fields are None in public response
        """
        # Create a mock emergency info with all fields populated
        service = EmergencyInfoService.__new__(EmergencyInfoService)
        
        # Create a mock EmergencyInfo object using a simple namespace
        class MockEmergencyInfo:
            pass
        
        mock_info = MockEmergencyInfo()
        mock_info.blood_type = "A+"
        mock_info.allergies = ["Penicillin", "Peanuts"]
        mock_info.medical_conditions = ["Diabetes", "Hypertension"]
        mock_info.emergency_contacts = [{"name": "John Doe", "phone": "1234567890", "relationship": "Spouse"}]
        mock_info.current_medications = ["Metformin", "Lisinopril"]
        mock_info.visible_fields = visible_fields
        
        # Get public response
        response = service._to_public_response(mock_info)
        
        # Verify only visible fields are populated
        if EmergencyInfoField.BLOOD_TYPE in visible_fields:
            assert response.blood_type == "A+", "Blood type should be visible"
        else:
            assert response.blood_type is None, "Blood type should not be visible"
        
        if EmergencyInfoField.ALLERGIES in visible_fields:
            assert response.allergies == ["Penicillin", "Peanuts"], "Allergies should be visible"
        else:
            assert response.allergies is None, "Allergies should not be visible"
        
        if EmergencyInfoField.MEDICAL_CONDITIONS in visible_fields:
            assert response.medical_conditions == ["Diabetes", "Hypertension"], "Medical conditions should be visible"
        else:
            assert response.medical_conditions is None, "Medical conditions should not be visible"
        
        if EmergencyInfoField.EMERGENCY_CONTACTS in visible_fields:
            assert response.emergency_contacts is not None, "Emergency contacts should be visible"
            assert len(response.emergency_contacts) == 1
        else:
            assert response.emergency_contacts is None, "Emergency contacts should not be visible"
        
        if EmergencyInfoField.CURRENT_MEDICATIONS in visible_fields:
            assert response.current_medications == ["Metformin", "Lisinopril"], "Current medications should be visible"
        else:
            assert response.current_medications is None, "Current medications should not be visible"
    
    @settings(max_examples=20, deadline=None)
    @given(st.data())
    def test_empty_visible_fields_returns_empty_response(self, data):
        """When visible_fields is empty, public response SHALL have all fields as None.
        
        **Validates: Requirements 17.3**
        
        This test verifies that:
        1. Empty visible_fields list results in no data being exposed
        2. All fields in public response are None
        """
        service = EmergencyInfoService.__new__(EmergencyInfoService)
        
        class MockEmergencyInfo:
            blood_type = "O-"
            allergies = ["Latex"]
            medical_conditions = ["Asthma"]
            emergency_contacts = [{"name": "Jane", "phone": "555-1234", "relationship": "Parent"}]
            current_medications = ["Albuterol"]
            visible_fields = []  # Empty - nothing visible
        
        mock_info = MockEmergencyInfo()
        response = service._to_public_response(mock_info)
        
        # All fields should be None
        assert response.blood_type is None, "Blood type should be None with empty visible_fields"
        assert response.allergies is None, "Allergies should be None with empty visible_fields"
        assert response.medical_conditions is None, "Medical conditions should be None with empty visible_fields"
        assert response.emergency_contacts is None, "Emergency contacts should be None with empty visible_fields"
        assert response.current_medications is None, "Current medications should be None with empty visible_fields"
    
    @settings(max_examples=20, deadline=None)
    @given(st.data())
    def test_all_visible_fields_returns_complete_response(self, data):
        """When all fields are visible, public response SHALL contain all data.
        
        **Validates: Requirements 17.3**
        
        This test verifies that:
        1. All fields in visible_fields list are included in response
        2. Data is correctly passed through
        """
        service = EmergencyInfoService.__new__(EmergencyInfoService)
        
        class MockEmergencyInfo:
            blood_type = "B+"
            allergies = ["Shellfish", "Dust"]
            medical_conditions = ["Epilepsy"]
            emergency_contacts = [{"name": "Bob", "phone": "999-8888", "relationship": "Sibling"}]
            current_medications = ["Keppra"]
            visible_fields = EmergencyInfoField.ALL.copy()  # All fields visible
        
        mock_info = MockEmergencyInfo()
        response = service._to_public_response(mock_info)
        
        # All fields should be populated
        assert response.blood_type == "B+", "Blood type should be visible"
        assert response.allergies == ["Shellfish", "Dust"], "Allergies should be visible"
        assert response.medical_conditions == ["Epilepsy"], "Medical conditions should be visible"
        assert response.emergency_contacts is not None, "Emergency contacts should be visible"
        assert response.current_medications == ["Keppra"], "Current medications should be visible"
    
    @given(blood_type=valid_blood_types())
    @settings(max_examples=20, deadline=None)
    def test_blood_type_validation(self, blood_type: str):
        """Blood type SHALL be one of the valid blood type values.
        
        **Validates: Requirements 17.1**
        
        This test verifies that:
        1. All valid blood types are accepted
        2. Blood type is correctly stored and retrieved
        """
        # Valid blood types should be accepted
        assert blood_type in BloodType.ALL, f"Blood type {blood_type} should be valid"
        
        # Create schema should accept valid blood type
        create_data = EmergencyInfoCreate(blood_type=blood_type)
        assert create_data.blood_type == blood_type
    
    @given(invalid_blood_type=st.text(min_size=1, max_size=10).filter(lambda x: x not in BloodType.ALL))
    @settings(max_examples=20, deadline=None)
    def test_invalid_blood_type_rejected(self, invalid_blood_type: str):
        """Invalid blood types SHALL be rejected.
        
        **Validates: Requirements 17.1**
        
        This test verifies that:
        1. Invalid blood types raise validation error
        2. Only predefined blood types are accepted
        """
        with pytest.raises(ValueError):
            EmergencyInfoCreate(blood_type=invalid_blood_type)
    
    @given(visible_fields=valid_visible_fields_list())
    @settings(max_examples=30, deadline=None)
    def test_visibility_update_validation(self, visible_fields: List[str]):
        """Visibility update SHALL only accept valid field names.
        
        **Validates: Requirements 17.5**
        
        This test verifies that:
        1. Valid field names are accepted
        2. The visibility configuration is correctly stored
        """
        # Valid field names should be accepted
        update = VisibilityUpdate(visible_fields=visible_fields)
        assert update.visible_fields == visible_fields
    
    @given(
        invalid_field=st.text(min_size=1, max_size=50).filter(
            lambda x: x not in EmergencyInfoField.ALL
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_invalid_visible_field_rejected(self, invalid_field: str):
        """Invalid field names in visible_fields SHALL be rejected.
        
        **Validates: Requirements 17.5**
        
        This test verifies that:
        1. Invalid field names raise validation error
        2. Only predefined field names are accepted
        """
        with pytest.raises(ValueError):
            VisibilityUpdate(visible_fields=[invalid_field])
    
    def test_qr_code_generation_produces_valid_png(self):
        """QR code generation SHALL produce a valid PNG image.
        
        **Validates: Requirements 17.2**
        
        This test verifies that:
        1. QR code is generated as PNG bytes
        2. The PNG has valid header bytes
        """
        service = EmergencyInfoService.__new__(EmergencyInfoService)
        
        test_url = "https://example.com/emergency/test-token-12345"
        qr_bytes = service._generate_qr_code_image(test_url)
        
        # Should return bytes
        assert isinstance(qr_bytes, bytes), "QR code should be bytes"
        
        # Should have PNG header (magic bytes)
        png_header = b'\x89PNG\r\n\x1a\n'
        assert qr_bytes[:8] == png_header, "QR code should be valid PNG"
        
        # Should have reasonable size (not empty, not too large)
        assert len(qr_bytes) > 100, "QR code should have content"
        assert len(qr_bytes) < 100000, "QR code should not be excessively large"
    
    @given(
        token=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=20, deadline=None)
    def test_qr_code_encodes_correct_url(self, token: str):
        """QR code SHALL encode the correct public URL.
        
        **Validates: Requirements 17.2**
        
        This test verifies that:
        1. QR code is generated for the correct URL format
        2. Different tokens produce different QR codes
        """
        service = EmergencyInfoService.__new__(EmergencyInfoService)
        
        base_url = "https://example.com"
        public_url = f"{base_url}/emergency/{token}"
        
        # Generate QR code
        qr_bytes = service._generate_qr_code_image(public_url)
        
        # Should produce valid PNG
        assert qr_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Should produce valid PNG"
        
        # Different URLs should produce different QR codes
        other_url = f"{base_url}/emergency/different-token"
        other_qr_bytes = service._generate_qr_code_image(other_url)
        
        if token != "different-token":
            assert qr_bytes != other_qr_bytes, "Different URLs should produce different QR codes"
