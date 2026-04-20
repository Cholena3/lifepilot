"""Tests for document expiry alerts functionality.

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.document import Document
from app.models.document_expiry import (
    DocumentExpiryAlert,
    DocumentExpiryAlertPreferences,
    ExpiryAlertType,
)
from app.models.notification import NotificationChannel
from app.schemas.document_expiry import (
    DocumentExpiryAlertPreferencesCreate,
    DocumentExpiryAlertPreferencesUpdate,
    DocumentExpiryCheckResult,
    ExpiringDocumentInfo,
)
from app.services.document_expiry import (
    ALERT_THRESHOLDS,
    DAYS_TO_ALERT_TYPE,
    DocumentExpiryService,
)


class TestExpiryAlertType:
    """Tests for ExpiryAlertType enum."""
    
    def test_alert_types_exist(self):
        """Test that all required alert types exist."""
        assert ExpiryAlertType.DAYS_30 == "days_30"
        assert ExpiryAlertType.DAYS_14 == "days_14"
        assert ExpiryAlertType.DAYS_7 == "days_7"
    
    def test_days_to_alert_type_mapping(self):
        """Test the mapping from days to alert types."""
        assert DAYS_TO_ALERT_TYPE[30] == ExpiryAlertType.DAYS_30
        assert DAYS_TO_ALERT_TYPE[14] == ExpiryAlertType.DAYS_14
        assert DAYS_TO_ALERT_TYPE[7] == ExpiryAlertType.DAYS_7
    
    def test_alert_thresholds(self):
        """Test that alert thresholds are correct."""
        assert ALERT_THRESHOLDS == [30, 14, 7]


class TestDocumentExpiryAlertPreferencesSchema:
    """Tests for document expiry alert preferences schemas."""
    
    def test_create_preferences_defaults(self):
        """Test default values for preferences creation."""
        prefs = DocumentExpiryAlertPreferencesCreate(category="Identity")
        
        assert prefs.category == "Identity"
        assert prefs.alerts_enabled is True
        assert prefs.alert_30_days is True
        assert prefs.alert_14_days is True
        assert prefs.alert_7_days is True
    
    def test_create_preferences_custom(self):
        """Test custom values for preferences creation."""
        prefs = DocumentExpiryAlertPreferencesCreate(
            category="Education",
            alerts_enabled=True,
            alert_30_days=False,
            alert_14_days=True,
            alert_7_days=True,
        )
        
        assert prefs.category == "Education"
        assert prefs.alerts_enabled is True
        assert prefs.alert_30_days is False
        assert prefs.alert_14_days is True
        assert prefs.alert_7_days is True
    
    def test_update_preferences_partial(self):
        """Test partial update of preferences."""
        update = DocumentExpiryAlertPreferencesUpdate(alert_30_days=False)
        
        assert update.alerts_enabled is None
        assert update.alert_30_days is False
        assert update.alert_14_days is None
        assert update.alert_7_days is None


class TestExpiringDocumentInfo:
    """Tests for ExpiringDocumentInfo schema."""
    
    def test_expiring_document_info(self):
        """Test ExpiringDocumentInfo creation."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=10)
        
        info = ExpiringDocumentInfo(
            document_id=uuid4(),
            user_id=uuid4(),
            title="Test Document",
            category="Identity",
            expiry_date=expiry,
            days_until_expiry=10,
            is_expired=False,
        )
        
        assert info.title == "Test Document"
        assert info.category == "Identity"
        assert info.days_until_expiry == 10
        assert info.is_expired is False
    
    def test_expired_document_info(self):
        """Test ExpiringDocumentInfo for expired document."""
        now = datetime.now(timezone.utc)
        expiry = now - timedelta(days=5)
        
        info = ExpiringDocumentInfo(
            document_id=uuid4(),
            user_id=uuid4(),
            title="Expired Document",
            category="Identity",
            expiry_date=expiry,
            days_until_expiry=-5,
            is_expired=True,
        )
        
        assert info.days_until_expiry == -5
        assert info.is_expired is True


class TestDocumentExpiryCheckResult:
    """Tests for DocumentExpiryCheckResult schema."""
    
    def test_check_result_success(self):
        """Test successful check result."""
        result = DocumentExpiryCheckResult(
            documents_checked=10,
            alerts_sent=3,
            documents_marked_expired=2,
            errors=[],
        )
        
        assert result.documents_checked == 10
        assert result.alerts_sent == 3
        assert result.documents_marked_expired == 2
        assert result.errors == []
    
    def test_check_result_with_errors(self):
        """Test check result with errors."""
        result = DocumentExpiryCheckResult(
            documents_checked=5,
            alerts_sent=1,
            documents_marked_expired=0,
            errors=["Error 1", "Error 2"],
        )
        
        assert len(result.errors) == 2


class TestDocumentExpiryServiceShouldSendAlert:
    """Tests for DocumentExpiryService.should_send_alert method."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a DocumentExpiryService instance with mocked dependencies."""
        service = DocumentExpiryService(mock_db)
        service.preferences_repo = AsyncMock()
        service.alert_repo = AsyncMock()
        service.notification_service = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_document(self):
        """Create a mock document."""
        doc = MagicMock(spec=Document)
        doc.id = uuid4()
        doc.user_id = uuid4()
        doc.title = "Test Document"
        doc.category = "Identity"
        doc.expiry_date = datetime.now(timezone.utc) + timedelta(days=30)
        doc.is_expired = False
        return doc
    
    @pytest.mark.asyncio
    async def test_should_not_send_alert_no_expiry_date(self, service, mock_document):
        """Test that no alert is sent when document has no expiry date."""
        mock_document.expiry_date = None
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_not_send_alert_already_expired(self, service, mock_document):
        """Test that no alert is sent when document is already expired."""
        mock_document.is_expired = True
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_not_send_alert_invalid_days(self, service, mock_document):
        """Test that no alert is sent for invalid days threshold."""
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 15  # Invalid threshold
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_not_send_alert_already_sent(self, service, mock_document):
        """Test that no alert is sent when alert was already sent."""
        service.alert_repo.has_alert_been_sent.return_value = True
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is False
        service.alert_repo.has_alert_been_sent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_should_send_alert_default_preferences(self, service, mock_document):
        """Test that alert is sent with default preferences (no preferences set)."""
        service.alert_repo.has_alert_been_sent.return_value = False
        service.preferences_repo.get_preferences_by_user_and_category.return_value = None
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_not_send_alert_disabled_category(self, service, mock_document):
        """Test that no alert is sent when alerts are disabled for category."""
        service.alert_repo.has_alert_been_sent.return_value = False
        
        mock_prefs = MagicMock(spec=DocumentExpiryAlertPreferences)
        mock_prefs.alerts_enabled = False
        service.preferences_repo.get_preferences_by_user_and_category.return_value = mock_prefs
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_not_send_alert_specific_day_disabled(self, service, mock_document):
        """Test that no alert is sent when specific day alert is disabled."""
        service.alert_repo.has_alert_been_sent.return_value = False
        
        mock_prefs = MagicMock(spec=DocumentExpiryAlertPreferences)
        mock_prefs.alerts_enabled = True
        mock_prefs.alert_30_days = False
        mock_prefs.alert_14_days = True
        mock_prefs.alert_7_days = True
        service.preferences_repo.get_preferences_by_user_and_category.return_value = mock_prefs
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_send_alert_all_conditions_met(self, service, mock_document):
        """Test that alert is sent when all conditions are met."""
        service.alert_repo.has_alert_been_sent.return_value = False
        
        mock_prefs = MagicMock(spec=DocumentExpiryAlertPreferences)
        mock_prefs.alerts_enabled = True
        mock_prefs.alert_30_days = True
        mock_prefs.alert_14_days = True
        mock_prefs.alert_7_days = True
        service.preferences_repo.get_preferences_by_user_and_category.return_value = mock_prefs
        
        result = await service.should_send_alert(
            mock_document.user_id, mock_document, 30
        )
        
        assert result is True


class TestDocumentExpiryServiceSendAlert:
    """Tests for DocumentExpiryService.send_expiry_alert method."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a DocumentExpiryService instance with mocked dependencies."""
        service = DocumentExpiryService(mock_db)
        service.preferences_repo = AsyncMock()
        service.alert_repo = AsyncMock()
        service.notification_service = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_document(self):
        """Create a mock document."""
        doc = MagicMock(spec=Document)
        doc.id = uuid4()
        doc.user_id = uuid4()
        doc.title = "Test Document"
        doc.category = "Identity"
        doc.expiry_date = datetime.now(timezone.utc) + timedelta(days=30)
        doc.is_expired = False
        return doc
    
    @pytest.mark.asyncio
    async def test_send_alert_success(self, service, mock_document):
        """Test successful alert sending."""
        # Setup mocks
        service.alert_repo.has_alert_been_sent.return_value = False
        service.preferences_repo.get_preferences_by_user_and_category.return_value = None
        
        mock_notification_result = MagicMock()
        mock_notification_result.success = True
        mock_notification_result.notification_id = uuid4()
        service.notification_service.send_notification.return_value = mock_notification_result
        
        mock_alert = MagicMock(spec=DocumentExpiryAlert)
        mock_alert.id = uuid4()
        service.alert_repo.create_alert.return_value = mock_alert
        
        # Execute
        result = await service.send_expiry_alert(mock_document, 30)
        
        # Verify
        assert result is not None
        assert result.id == mock_alert.id
        service.notification_service.send_notification.assert_called_once()
        service.alert_repo.create_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_alert_skipped_when_should_not_send(self, service, mock_document):
        """Test that alert is skipped when should_send_alert returns False."""
        mock_document.expiry_date = None  # No expiry date
        
        result = await service.send_expiry_alert(mock_document, 30)
        
        assert result is None
        service.notification_service.send_notification.assert_not_called()


class TestDocumentExpiryServiceReschedule:
    """Tests for DocumentExpiryService.reschedule_alerts_for_document method."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a DocumentExpiryService instance with mocked dependencies."""
        service = DocumentExpiryService(mock_db)
        service.preferences_repo = AsyncMock()
        service.alert_repo = AsyncMock()
        service.notification_service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_reschedule_deletes_existing_alerts(self, service):
        """Test that rescheduling deletes existing alerts.
        
        Validates: Requirements 8.3
        """
        document_id = uuid4()
        service.alert_repo.delete_alerts_by_document.return_value = 3
        
        result = await service.reschedule_alerts_for_document(document_id)
        
        assert result == 3
        service.alert_repo.delete_alerts_by_document.assert_called_once_with(document_id)
    
    @pytest.mark.asyncio
    async def test_reschedule_no_existing_alerts(self, service):
        """Test rescheduling when no existing alerts."""
        document_id = uuid4()
        service.alert_repo.delete_alerts_by_document.return_value = 0
        
        result = await service.reschedule_alerts_for_document(document_id)
        
        assert result == 0


class TestDocumentExpiryServiceMarkExpired:
    """Tests for DocumentExpiryService.mark_expired_documents method."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a DocumentExpiryService instance with mocked dependencies."""
        service = DocumentExpiryService(mock_db)
        service.expiry_repo = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_mark_expired_documents(self, service):
        """Test marking expired documents.
        
        Validates: Requirements 8.2
        """
        # Create mock expired documents
        mock_docs = [MagicMock(spec=Document, id=uuid4()) for _ in range(3)]
        service.expiry_repo.get_expired_documents.return_value = mock_docs
        
        # Mock mark_document_expired to return the updated document
        service.expiry_repo.mark_document_expired.side_effect = mock_docs
        
        result = await service.mark_expired_documents()
        
        assert len(result) == 3
        assert service.expiry_repo.mark_document_expired.call_count == 3
    
    @pytest.mark.asyncio
    async def test_mark_expired_no_documents(self, service):
        """Test marking when no documents are expired."""
        service.expiry_repo.get_expired_documents.return_value = []
        
        result = await service.mark_expired_documents()
        
        assert len(result) == 0
        service.expiry_repo.mark_document_expired.assert_not_called()


class TestDocumentExpiryServiceCheckAndSend:
    """Tests for DocumentExpiryService.check_and_send_expiry_alerts method."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a DocumentExpiryService instance with mocked dependencies."""
        service = DocumentExpiryService(mock_db)
        service.preferences_repo = AsyncMock()
        service.alert_repo = AsyncMock()
        service.expiry_repo = AsyncMock()
        service.notification_service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_check_and_send_full_flow(self, service):
        """Test the full check and send flow.
        
        Validates: Requirements 8.1, 8.2
        """
        # Setup mocks
        service.expiry_repo.get_expired_documents.return_value = []
        service.expiry_repo.get_documents_needing_alerts.return_value = []
        
        result = await service.check_and_send_expiry_alerts()
        
        assert isinstance(result, DocumentExpiryCheckResult)
        assert result.documents_marked_expired == 0
        # Should check for all three thresholds
        assert service.expiry_repo.get_documents_needing_alerts.call_count == 3
