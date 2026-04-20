"""Pydantic schemas for admin analytics module.

Provides schemas for admin dashboard analytics including user metrics,
feature usage statistics, system performance metrics, and scraper status.

Validates: Requirements 38.1, 38.2, 38.3, 38.4
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# User Metrics Schemas - Validates: Requirements 38.1
# ============================================================================

class UserGrowthDataPoint(BaseModel):
    """Data point for user growth trends."""
    
    date: datetime = Field(..., description="Date of the data point")
    total_users: int = Field(..., description="Total users at this date")
    new_users: int = Field(..., description="New users on this date")


class UserMetricsResponse(BaseModel):
    """Response schema for user metrics.
    
    Validates: Requirements 38.1
    """
    
    total_users: int = Field(..., description="Total registered users")
    active_users_24h: int = Field(..., description="Users active in last 24 hours")
    active_users_7d: int = Field(..., description="Users active in last 7 days")
    active_users_30d: int = Field(..., description="Users active in last 30 days")
    new_users_today: int = Field(..., description="New users registered today")
    new_users_7d: int = Field(..., description="New users in last 7 days")
    new_users_30d: int = Field(..., description="New users in last 30 days")
    verified_phone_users: int = Field(..., description="Users with verified phone")
    oauth_users: int = Field(..., description="Users registered via OAuth")
    growth_trend: List[UserGrowthDataPoint] = Field(
        default_factory=list,
        description="User growth trend data for the last 30 days"
    )


# ============================================================================
# Feature Usage Schemas - Validates: Requirements 38.2
# ============================================================================

class ModuleUsageStats(BaseModel):
    """Usage statistics for a single module."""
    
    module_name: str = Field(..., description="Name of the module")
    total_records: int = Field(..., description="Total records in this module")
    active_users: int = Field(..., description="Users who have used this module")
    records_created_7d: int = Field(..., description="Records created in last 7 days")
    records_created_30d: int = Field(..., description="Records created in last 30 days")


class FeatureUsageResponse(BaseModel):
    """Response schema for feature usage statistics.
    
    Validates: Requirements 38.2
    """
    
    modules: List[ModuleUsageStats] = Field(
        default_factory=list,
        description="Usage statistics by module"
    )
    most_active_module: Optional[str] = Field(
        None,
        description="Module with most activity"
    )
    least_active_module: Optional[str] = Field(
        None,
        description="Module with least activity"
    )


# ============================================================================
# System Performance Schemas - Validates: Requirements 38.3
# ============================================================================

class EndpointPerformance(BaseModel):
    """Performance metrics for a single endpoint."""
    
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    avg_response_time_ms: Decimal = Field(..., description="Average response time in milliseconds")
    p95_response_time_ms: Decimal = Field(..., description="95th percentile response time")
    p99_response_time_ms: Decimal = Field(..., description="99th percentile response time")
    request_count: int = Field(..., description="Total request count")
    error_count: int = Field(..., description="Total error count")
    error_rate: Decimal = Field(..., description="Error rate as percentage")


class SystemPerformanceResponse(BaseModel):
    """Response schema for system performance metrics.
    
    Validates: Requirements 38.3
    """
    
    avg_response_time_ms: Decimal = Field(..., description="Overall average response time")
    p95_response_time_ms: Decimal = Field(..., description="Overall 95th percentile response time")
    p99_response_time_ms: Decimal = Field(..., description="Overall 99th percentile response time")
    total_requests_24h: int = Field(..., description="Total requests in last 24 hours")
    total_errors_24h: int = Field(..., description="Total errors in last 24 hours")
    error_rate_24h: Decimal = Field(..., description="Error rate in last 24 hours")
    slowest_endpoints: List[EndpointPerformance] = Field(
        default_factory=list,
        description="Top 10 slowest endpoints"
    )
    highest_error_endpoints: List[EndpointPerformance] = Field(
        default_factory=list,
        description="Top 10 endpoints with highest error rates"
    )
    database_connection_pool_size: int = Field(..., description="Current DB connection pool size")
    redis_connected: bool = Field(..., description="Whether Redis is connected")


# ============================================================================
# Scraper Status Schemas - Validates: Requirements 38.4
# ============================================================================

class ScraperJobStatus(BaseModel):
    """Status of a single scraper job."""
    
    source: str = Field(..., description="Scraper source name")
    last_run_at: Optional[datetime] = Field(None, description="Last run timestamp")
    last_run_success: bool = Field(..., description="Whether last run was successful")
    exams_found: int = Field(0, description="Exams found in last run")
    exams_created: int = Field(0, description="Exams created in last run")
    exams_updated: int = Field(0, description="Exams updated in last run")
    error_message: Optional[str] = Field(None, description="Error message if last run failed")
    next_scheduled_run: Optional[datetime] = Field(None, description="Next scheduled run time")


class ScraperStatusResponse(BaseModel):
    """Response schema for scraper job status.
    
    Validates: Requirements 38.4
    """
    
    scrapers: List[ScraperJobStatus] = Field(
        default_factory=list,
        description="Status of all scraper jobs"
    )
    total_exams_scraped: int = Field(..., description="Total exams in database from scrapers")
    last_successful_scrape: Optional[datetime] = Field(
        None,
        description="Timestamp of last successful scrape across all sources"
    )
    scraper_health: str = Field(
        ...,
        description="Overall scraper health: 'healthy', 'degraded', 'unhealthy'"
    )
