"""Tests for admin analytics endpoints.

Validates: Requirements 38.1, 38.2, 38.3, 38.4
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient

from app.models.user import User
from app.schemas.admin import (
    FeatureUsageResponse,
    ModuleUsageStats,
    ScraperJobStatus,
    ScraperStatusResponse,
    SystemPerformanceResponse,
    UserGrowthDataPoint,
    UserMetricsResponse,
)
from app.services.auth import create_tokens


class TestAdminUserMetrics:
    """Tests for GET /api/v1/admin/users endpoint.
    
    Validates: Requirements 38.1
    """
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "admin@test.com"
        user.is_admin = True
        return user
    
    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular (non-admin) user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "user@test.com"
        user.is_admin = False
        return user
    
    @pytest.fixture
    def admin_auth_headers(self, mock_admin_user):
        """Create valid auth headers for admin user."""
        tokens = create_tokens(mock_admin_user.id, mock_admin_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.fixture
    def regular_auth_headers(self, mock_regular_user):
        """Create valid auth headers for regular user."""
        tokens = create_tokens(mock_regular_user.id, mock_regular_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.mark.asyncio
    async def test_get_user_metrics_as_admin(
        self,
        client: AsyncClient,
        mock_admin_user,
        admin_auth_headers,
    ) -> None:
        """Admin user can access user metrics."""
        mock_response = UserMetricsResponse(
            total_users=100,
            active_users_24h=50,
            active_users_7d=75,
            active_users_30d=90,
            new_users_today=5,
            new_users_7d=20,
            new_users_30d=40,
            verified_phone_users=60,
            oauth_users=30,
            growth_trend=[
                UserGrowthDataPoint(
                    date=datetime.now(timezone.utc),
                    total_users=100,
                    new_users=5,
                )
            ],
        )
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_admin_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.admin_analytics.AdminAnalyticsService.get_user_metrics") as mock_service:
                mock_service.return_value = mock_response
                
                response = await client.get(
                    "/api/v1/admin/users",
                    headers=admin_auth_headers,
                )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_users" in data
        assert "active_users_24h" in data
        assert "active_users_7d" in data
        assert "active_users_30d" in data
        assert "new_users_today" in data
        assert "new_users_7d" in data
        assert "new_users_30d" in data
        assert "verified_phone_users" in data
        assert "oauth_users" in data
        assert "growth_trend" in data
        
        # Verify types
        assert isinstance(data["total_users"], int)
        assert isinstance(data["growth_trend"], list)
    
    @pytest.mark.asyncio
    async def test_get_user_metrics_as_regular_user_forbidden(
        self,
        client: AsyncClient,
        mock_regular_user,
        regular_auth_headers,
    ) -> None:
        """Regular user cannot access user metrics."""
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_regular_user)
            mock_repo_class.return_value = mock_repo
            
            response = await client.get(
                "/api/v1/admin/users",
                headers=regular_auth_headers,
            )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_user_metrics_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated request is rejected."""
        response = await client.get("/api/v1/admin/users")
        
        assert response.status_code == 403


class TestAdminFeatureUsage:
    """Tests for GET /api/v1/admin/features endpoint.
    
    Validates: Requirements 38.2
    """
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "admin@test.com"
        user.is_admin = True
        return user
    
    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular (non-admin) user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "user@test.com"
        user.is_admin = False
        return user
    
    @pytest.fixture
    def admin_auth_headers(self, mock_admin_user):
        """Create valid auth headers for admin user."""
        tokens = create_tokens(mock_admin_user.id, mock_admin_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.fixture
    def regular_auth_headers(self, mock_regular_user):
        """Create valid auth headers for regular user."""
        tokens = create_tokens(mock_regular_user.id, mock_regular_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_as_admin(
        self,
        client: AsyncClient,
        mock_admin_user,
        admin_auth_headers,
    ) -> None:
        """Admin user can access feature usage statistics."""
        mock_response = FeatureUsageResponse(
            modules=[
                ModuleUsageStats(
                    module_name="Documents",
                    total_records=500,
                    active_users=80,
                    records_created_7d=50,
                    records_created_30d=150,
                ),
                ModuleUsageStats(
                    module_name="Expenses",
                    total_records=1000,
                    active_users=90,
                    records_created_7d=100,
                    records_created_30d=300,
                ),
            ],
            most_active_module="Expenses",
            least_active_module="Documents",
        )
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_admin_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.admin_analytics.AdminAnalyticsService.get_feature_usage") as mock_service:
                mock_service.return_value = mock_response
                
                response = await client.get(
                    "/api/v1/admin/features",
                    headers=admin_auth_headers,
                )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "modules" in data
        assert "most_active_module" in data
        assert "least_active_module" in data
        
        # Verify modules list
        assert isinstance(data["modules"], list)
        assert len(data["modules"]) == 2
        
        # Verify module structure
        module = data["modules"][0]
        assert "module_name" in module
        assert "total_records" in module
        assert "active_users" in module
        assert "records_created_7d" in module
        assert "records_created_30d" in module
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_as_regular_user_forbidden(
        self,
        client: AsyncClient,
        mock_regular_user,
        regular_auth_headers,
    ) -> None:
        """Regular user cannot access feature usage statistics."""
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_regular_user)
            mock_repo_class.return_value = mock_repo
            
            response = await client.get(
                "/api/v1/admin/features",
                headers=regular_auth_headers,
            )
        
        assert response.status_code == 403


class TestAdminSystemPerformance:
    """Tests for GET /api/v1/admin/performance endpoint.
    
    Validates: Requirements 38.3
    """
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "admin@test.com"
        user.is_admin = True
        return user
    
    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular (non-admin) user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "user@test.com"
        user.is_admin = False
        return user
    
    @pytest.fixture
    def admin_auth_headers(self, mock_admin_user):
        """Create valid auth headers for admin user."""
        tokens = create_tokens(mock_admin_user.id, mock_admin_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.fixture
    def regular_auth_headers(self, mock_regular_user):
        """Create valid auth headers for regular user."""
        tokens = create_tokens(mock_regular_user.id, mock_regular_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.mark.asyncio
    async def test_get_system_performance_as_admin(
        self,
        client: AsyncClient,
        mock_admin_user,
        admin_auth_headers,
    ) -> None:
        """Admin user can access system performance metrics."""
        mock_response = SystemPerformanceResponse(
            avg_response_time_ms=Decimal("45.5"),
            p95_response_time_ms=Decimal("120.0"),
            p99_response_time_ms=Decimal("250.0"),
            total_requests_24h=10000,
            total_errors_24h=50,
            error_rate_24h=Decimal("0.5"),
            slowest_endpoints=[],
            highest_error_endpoints=[],
            database_connection_pool_size=10,
            redis_connected=True,
        )
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_admin_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.admin_analytics.AdminAnalyticsService.get_system_performance") as mock_service:
                mock_service.return_value = mock_response
                
                response = await client.get(
                    "/api/v1/admin/performance",
                    headers=admin_auth_headers,
                )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "avg_response_time_ms" in data
        assert "p95_response_time_ms" in data
        assert "p99_response_time_ms" in data
        assert "total_requests_24h" in data
        assert "total_errors_24h" in data
        assert "error_rate_24h" in data
        assert "slowest_endpoints" in data
        assert "highest_error_endpoints" in data
        assert "database_connection_pool_size" in data
        assert "redis_connected" in data
        
        # Verify types
        assert isinstance(data["slowest_endpoints"], list)
        assert isinstance(data["highest_error_endpoints"], list)
        assert isinstance(data["redis_connected"], bool)
    
    @pytest.mark.asyncio
    async def test_get_system_performance_as_regular_user_forbidden(
        self,
        client: AsyncClient,
        mock_regular_user,
        regular_auth_headers,
    ) -> None:
        """Regular user cannot access system performance metrics."""
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_regular_user)
            mock_repo_class.return_value = mock_repo
            
            response = await client.get(
                "/api/v1/admin/performance",
                headers=regular_auth_headers,
            )
        
        assert response.status_code == 403


class TestAdminScraperStatus:
    """Tests for GET /api/v1/admin/scrapers endpoint.
    
    Validates: Requirements 38.4
    """
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "admin@test.com"
        user.is_admin = True
        return user
    
    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular (non-admin) user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "user@test.com"
        user.is_admin = False
        return user
    
    @pytest.fixture
    def admin_auth_headers(self, mock_admin_user):
        """Create valid auth headers for admin user."""
        tokens = create_tokens(mock_admin_user.id, mock_admin_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.fixture
    def regular_auth_headers(self, mock_regular_user):
        """Create valid auth headers for regular user."""
        tokens = create_tokens(mock_regular_user.id, mock_regular_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.mark.asyncio
    async def test_get_scraper_status_as_admin(
        self,
        client: AsyncClient,
        mock_admin_user,
        admin_auth_headers,
    ) -> None:
        """Admin user can access scraper status."""
        mock_response = ScraperStatusResponse(
            scrapers=[
                ScraperJobStatus(
                    source="tcs",
                    last_run_at=datetime.now(timezone.utc),
                    last_run_success=True,
                    exams_found=10,
                    exams_created=5,
                    exams_updated=3,
                    error_message=None,
                    next_scheduled_run=None,
                ),
                ScraperJobStatus(
                    source="infosys",
                    last_run_at=datetime.now(timezone.utc),
                    last_run_success=True,
                    exams_found=8,
                    exams_created=4,
                    exams_updated=2,
                    error_message=None,
                    next_scheduled_run=None,
                ),
            ],
            total_exams_scraped=50,
            last_successful_scrape=datetime.now(timezone.utc),
            scraper_health="healthy",
        )
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_admin_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.admin_analytics.AdminAnalyticsService.get_scraper_status") as mock_service:
                mock_service.return_value = mock_response
                
                response = await client.get(
                    "/api/v1/admin/scrapers",
                    headers=admin_auth_headers,
                )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "scrapers" in data
        assert "total_exams_scraped" in data
        assert "last_successful_scrape" in data
        assert "scraper_health" in data
        
        # Verify scrapers list
        assert isinstance(data["scrapers"], list)
        assert len(data["scrapers"]) == 2
        
        # Verify scraper health is one of expected values
        assert data["scraper_health"] in ["healthy", "degraded", "unhealthy"]
        
        # Verify scraper structure
        scraper = data["scrapers"][0]
        assert "source" in scraper
        assert "last_run_at" in scraper
        assert "last_run_success" in scraper
        assert "exams_found" in scraper
    
    @pytest.mark.asyncio
    async def test_get_scraper_status_as_regular_user_forbidden(
        self,
        client: AsyncClient,
        mock_regular_user,
        regular_auth_headers,
    ) -> None:
        """Regular user cannot access scraper status."""
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_regular_user)
            mock_repo_class.return_value = mock_repo
            
            response = await client.get(
                "/api/v1/admin/scrapers",
                headers=regular_auth_headers,
            )
        
        assert response.status_code == 403


class TestAdminEndpointSecurity:
    """Tests for admin endpoint security.
    
    Validates: Requirements 38.1, 38.2, 38.3, 38.4
    """
    
    @pytest.mark.asyncio
    async def test_all_admin_endpoints_require_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """All admin endpoints should require authentication."""
        endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/features",
            "/api/v1/admin/performance",
            "/api/v1/admin/scrapers",
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 403, f"Endpoint {endpoint} should require auth"
