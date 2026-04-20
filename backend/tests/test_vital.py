"""Tests for vitals tracking module.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.vital import Vital, VitalTargetRange, VitalType, DEFAULT_VITAL_RANGES
from app.schemas.vital import (
    VitalCreate,
    VitalUpdate,
    VitalResponse,
    VitalTargetRangeCreate,
    VitalTrendResponse,
    VitalTypeEnum,
    WarningLevel,
)
from app.services.vital import VitalService


class TestVitalSchemas:
    """Test vital schemas validation."""
    
    def test_vital_create_valid(self):
        """Test creating a valid vital."""
        data = VitalCreate(
            vital_type=VitalTypeEnum.HEART_RATE,
            value=72.0,
            unit="bpm",
        )
        assert data.vital_type == VitalTypeEnum.HEART_RATE
        assert data.value == 72.0
        assert data.unit == "bpm"
    
    def test_vital_create_invalid_type(self):
        """Test creating a vital with invalid type."""
        with pytest.raises(ValueError, match="Vital type must be one of"):
            VitalCreate(
                vital_type="invalid_type",
                value=72.0,
                unit="bpm",
            )
    
    def test_vital_create_all_types(self):
        """Test creating vitals with all valid types."""
        for vital_type in VitalTypeEnum.ALL:
            data = VitalCreate(
                vital_type=vital_type,
                value=100.0,
                unit="test",
            )
            assert data.vital_type == vital_type
    
    def test_vital_create_with_family_member(self):
        """Test creating a vital for a family member."""
        family_member_id = uuid4()
        data = VitalCreate(
            vital_type=VitalTypeEnum.WEIGHT,
            value=70.5,
            unit="kg",
            family_member_id=family_member_id,
        )
        assert data.family_member_id == family_member_id
    
    def test_vital_create_with_recorded_at(self):
        """Test creating a vital with custom recorded_at."""
        recorded_at = datetime.now(timezone.utc) - timedelta(hours=2)
        data = VitalCreate(
            vital_type=VitalTypeEnum.TEMPERATURE,
            value=36.8,
            unit="°C",
            recorded_at=recorded_at,
        )
        assert data.recorded_at == recorded_at
    
    def test_target_range_create_valid(self):
        """Test creating a valid target range."""
        data = VitalTargetRangeCreate(
            vital_type=VitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC,
            min_value=90.0,
            max_value=130.0,
        )
        assert data.vital_type == VitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC
        assert data.min_value == 90.0
        assert data.max_value == 130.0
    
    def test_target_range_create_min_only(self):
        """Test creating a target range with only min value."""
        data = VitalTargetRangeCreate(
            vital_type=VitalTypeEnum.OXYGEN_SATURATION,
            min_value=95.0,
        )
        assert data.min_value == 95.0
        assert data.max_value is None
    
    def test_target_range_create_max_only(self):
        """Test creating a target range with only max value."""
        data = VitalTargetRangeCreate(
            vital_type=VitalTypeEnum.WEIGHT,
            max_value=80.0,
        )
        assert data.min_value is None
        assert data.max_value == 80.0


class TestVitalModel:
    """Test vital model."""
    
    def test_vital_type_enum_values(self):
        """Test VitalType enum has expected values."""
        assert VitalType.BLOOD_PRESSURE_SYSTOLIC.value == "blood_pressure_systolic"
        assert VitalType.BLOOD_PRESSURE_DIASTOLIC.value == "blood_pressure_diastolic"
        assert VitalType.HEART_RATE.value == "heart_rate"
        assert VitalType.WEIGHT.value == "weight"
        assert VitalType.TEMPERATURE.value == "temperature"
        assert VitalType.BLOOD_SUGAR.value == "blood_sugar"
        assert VitalType.OXYGEN_SATURATION.value == "oxygen_saturation"
        assert VitalType.RESPIRATORY_RATE.value == "respiratory_rate"
    
    def test_default_vital_ranges(self):
        """Test default vital ranges are defined."""
        assert VitalType.BLOOD_PRESSURE_SYSTOLIC.value in DEFAULT_VITAL_RANGES
        assert VitalType.HEART_RATE.value in DEFAULT_VITAL_RANGES
        
        # Check blood pressure systolic defaults
        bp_systolic = DEFAULT_VITAL_RANGES[VitalType.BLOOD_PRESSURE_SYSTOLIC.value]
        assert bp_systolic["min"] == 90.0
        assert bp_systolic["max"] == 120.0
        assert bp_systolic["unit"] == "mmHg"
        
        # Check heart rate defaults
        hr = DEFAULT_VITAL_RANGES[VitalType.HEART_RATE.value]
        assert hr["min"] == 60.0
        assert hr["max"] == 100.0
        assert hr["unit"] == "bpm"


class TestWarningLevelCalculation:
    """Test warning level calculation logic."""
    
    def test_normal_reading(self):
        """Test normal reading returns normal warning level."""
        # Heart rate 72 is within normal range (60-100)
        service = VitalService.__new__(VitalService)
        level = service._calculate_warning_level(72.0, 60.0, 100.0)
        assert level == WarningLevel.NORMAL
    
    def test_low_reading(self):
        """Test low reading returns low warning level."""
        service = VitalService.__new__(VitalService)
        level = service._calculate_warning_level(55.0, 60.0, 100.0)
        assert level == WarningLevel.LOW
    
    def test_high_reading(self):
        """Test high reading returns high warning level."""
        service = VitalService.__new__(VitalService)
        level = service._calculate_warning_level(110.0, 60.0, 100.0)
        assert level == WarningLevel.HIGH
    
    def test_critical_low_reading(self):
        """Test critical low reading returns critical_low warning level."""
        service = VitalService.__new__(VitalService)
        # 20% below min (60 * 0.8 = 48)
        level = service._calculate_warning_level(40.0, 60.0, 100.0)
        assert level == WarningLevel.CRITICAL_LOW
    
    def test_critical_high_reading(self):
        """Test critical high reading returns critical_high warning level."""
        service = VitalService.__new__(VitalService)
        # 20% above max (100 * 1.2 = 120)
        level = service._calculate_warning_level(130.0, 60.0, 100.0)
        assert level == WarningLevel.CRITICAL_HIGH
    
    def test_no_range_returns_normal(self):
        """Test no range defined returns normal."""
        service = VitalService.__new__(VitalService)
        level = service._calculate_warning_level(999.0, None, None)
        assert level == WarningLevel.NORMAL
    
    def test_only_min_range(self):
        """Test only min range defined."""
        service = VitalService.__new__(VitalService)
        # Value above min is normal
        level = service._calculate_warning_level(100.0, 95.0, None)
        assert level == WarningLevel.NORMAL
        
        # Value below min is low
        level = service._calculate_warning_level(90.0, 95.0, None)
        assert level == WarningLevel.LOW
    
    def test_only_max_range(self):
        """Test only max range defined."""
        service = VitalService.__new__(VitalService)
        # Value below max is normal
        level = service._calculate_warning_level(70.0, None, 80.0)
        assert level == WarningLevel.NORMAL
        
        # Value above max is high
        level = service._calculate_warning_level(85.0, None, 80.0)
        assert level == WarningLevel.HIGH


class TestVitalTypeEnum:
    """Test VitalTypeEnum class."""
    
    def test_all_types_list(self):
        """Test ALL list contains all vital types."""
        assert len(VitalTypeEnum.ALL) == 8
        assert VitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC in VitalTypeEnum.ALL
        assert VitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC in VitalTypeEnum.ALL
        assert VitalTypeEnum.HEART_RATE in VitalTypeEnum.ALL
        assert VitalTypeEnum.WEIGHT in VitalTypeEnum.ALL
        assert VitalTypeEnum.TEMPERATURE in VitalTypeEnum.ALL
        assert VitalTypeEnum.BLOOD_SUGAR in VitalTypeEnum.ALL
        assert VitalTypeEnum.OXYGEN_SATURATION in VitalTypeEnum.ALL
        assert VitalTypeEnum.RESPIRATORY_RATE in VitalTypeEnum.ALL
