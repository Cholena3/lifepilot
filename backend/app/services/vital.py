"""Vital service for vitals tracking and trend analysis.

Provides functionality for vital CRUD operations, trend calculation,
range warnings, and PDF export.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

from datetime import datetime, date, time, timedelta, timezone
from io import BytesIO
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vital import Vital, VitalTargetRange, VitalType, DEFAULT_VITAL_RANGES
from app.repositories.vital import VitalRepository
from app.repositories.health import HealthRepository
from app.schemas.vital import (
    VitalCreate,
    VitalUpdate,
    VitalResponse,
    VitalWithFamilyMemberResponse,
    VitalTargetRangeCreate,
    VitalTargetRangeUpdate,
    VitalTargetRangeResponse,
    VitalTrendResponse,
    VitalTrendDataPoint,
    VitalSummary,
    VitalsDashboardResponse,
    VitalExportRequest,
    PaginatedVitalResponse,
    PaginatedVitalTargetRangeResponse,
    WarningLevel,
    VitalTypeEnum,
)


class VitalService:
    """Service for managing vitals and trend analysis.
    
    Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the vital service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.repository = VitalRepository(db)
        self.health_repository = HealthRepository(db)
    
    # ========================================================================
    # Vital Operations
    # ========================================================================
    
    async def create_vital(
        self,
        user_id: UUID,
        data: VitalCreate,
    ) -> VitalResponse:
        """Create a new vital reading.
        
        Validates: Requirements 16.1
        
        Args:
            user_id: User's UUID
            data: Vital creation data
            
        Returns:
            Created vital response with warning level
        """
        # Validate family member belongs to user if provided
        if data.family_member_id is not None:
            family_member = await self.health_repository.get_family_member_by_id(
                data.family_member_id, user_id
            )
            if family_member is None:
                raise ValueError("Family member not found or does not belong to user")
        
        vital = await self.repository.create_vital(user_id, data)
        await self.db.commit()
        
        # Calculate warning level
        warning_level = await self._get_warning_level(
            user_id, vital.vital_type, vital.value, data.family_member_id
        )
        
        response = VitalResponse.model_validate(vital)
        response.warning_level = warning_level
        return response
    
    async def get_vital(
        self,
        user_id: UUID,
        vital_id: UUID,
    ) -> Optional[VitalResponse]:
        """Get a vital by ID.
        
        Args:
            user_id: User's UUID
            vital_id: Vital's UUID
            
        Returns:
            Vital response if found, None otherwise
        """
        vital = await self.repository.get_vital_by_id(vital_id, user_id)
        if vital is None:
            return None
        
        warning_level = await self._get_warning_level(
            user_id, vital.vital_type, vital.value, vital.family_member_id
        )
        
        response = VitalResponse.model_validate(vital)
        response.warning_level = warning_level
        return response
    
    async def list_vitals(
        self,
        user_id: UUID,
        vital_type: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedVitalResponse:
        """List vitals for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            vital_type: Optional vital type filter
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated vital response
        """
        offset = (page - 1) * page_size
        
        # Convert dates to datetime
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc) if start_date else None
        end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc) if end_date else None
        
        vitals = await self.repository.get_vitals_by_user(
            user_id,
            vital_type=vital_type,
            family_member_id=family_member_id,
            start_date=start_dt,
            end_date=end_dt,
            limit=page_size,
            offset=offset,
        )
        total = await self.repository.count_vitals(
            user_id,
            vital_type=vital_type,
            family_member_id=family_member_id,
            start_date=start_dt,
            end_date=end_dt,
        )
        
        # Add warning levels to each vital
        items = []
        for vital in vitals:
            warning_level = await self._get_warning_level(
                user_id, vital.vital_type, vital.value, vital.family_member_id
            )
            response = VitalResponse.model_validate(vital)
            response.warning_level = warning_level
            items.append(response)
        
        return PaginatedVitalResponse.create(items, total, page, page_size)
    
    async def update_vital(
        self,
        user_id: UUID,
        vital_id: UUID,
        data: VitalUpdate,
    ) -> Optional[VitalResponse]:
        """Update a vital reading.
        
        Args:
            user_id: User's UUID
            vital_id: Vital's UUID
            data: Vital update data
            
        Returns:
            Updated vital response if found, None otherwise
        """
        vital = await self.repository.get_vital_by_id(vital_id, user_id)
        if vital is None:
            return None
        
        updated = await self.repository.update_vital(vital, data)
        await self.db.commit()
        
        warning_level = await self._get_warning_level(
            user_id, updated.vital_type, updated.value, updated.family_member_id
        )
        
        response = VitalResponse.model_validate(updated)
        response.warning_level = warning_level
        return response
    
    async def delete_vital(
        self,
        user_id: UUID,
        vital_id: UUID,
    ) -> bool:
        """Delete a vital reading.
        
        Args:
            user_id: User's UUID
            vital_id: Vital's UUID
            
        Returns:
            True if deleted, False if not found
        """
        vital = await self.repository.get_vital_by_id(vital_id, user_id)
        if vital is None:
            return False
        
        await self.repository.delete_vital(vital)
        await self.db.commit()
        return True
    
    # ========================================================================
    # Target Range Operations
    # ========================================================================
    
    async def set_target_range(
        self,
        user_id: UUID,
        data: VitalTargetRangeCreate,
    ) -> VitalTargetRangeResponse:
        """Set a custom target range for a vital type.
        
        Validates: Requirements 16.4
        
        Args:
            user_id: User's UUID
            data: Target range data
            
        Returns:
            Created or updated target range response
        """
        # Validate family member belongs to user if provided
        if data.family_member_id is not None:
            family_member = await self.health_repository.get_family_member_by_id(
                data.family_member_id, user_id
            )
            if family_member is None:
                raise ValueError("Family member not found or does not belong to user")
        
        target_range = await self.repository.upsert_target_range(user_id, data)
        await self.db.commit()
        
        return VitalTargetRangeResponse.model_validate(target_range)
    
    async def get_target_range(
        self,
        user_id: UUID,
        vital_type: str,
        family_member_id: Optional[UUID] = None,
    ) -> Optional[VitalTargetRangeResponse]:
        """Get target range for a vital type.
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            family_member_id: Optional family member filter
            
        Returns:
            Target range response if found, None otherwise
        """
        target_range = await self.repository.get_target_range(
            user_id, vital_type, family_member_id
        )
        if target_range is None:
            return None
        return VitalTargetRangeResponse.model_validate(target_range)
    
    async def list_target_ranges(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedVitalTargetRangeResponse:
        """List all target ranges for a user.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated target range response
        """
        offset = (page - 1) * page_size
        
        ranges = await self.repository.get_target_ranges_by_user(
            user_id, family_member_id, limit=page_size, offset=offset
        )
        total = await self.repository.count_target_ranges(user_id, family_member_id)
        
        items = [VitalTargetRangeResponse.model_validate(r) for r in ranges]
        return PaginatedVitalTargetRangeResponse.create(items, total, page, page_size)
    
    async def delete_target_range(
        self,
        user_id: UUID,
        range_id: UUID,
    ) -> bool:
        """Delete a custom target range.
        
        Args:
            user_id: User's UUID
            range_id: Target range's UUID
            
        Returns:
            True if deleted, False if not found
        """
        target_range = await self.repository.get_target_range_by_id(range_id, user_id)
        if target_range is None:
            return False
        
        await self.repository.delete_target_range(target_range)
        await self.db.commit()
        return True
    
    # ========================================================================
    # Trend Analysis
    # ========================================================================
    
    async def get_vital_trends(
        self,
        user_id: UUID,
        vital_type: str,
        start_date: date,
        end_date: date,
        family_member_id: Optional[UUID] = None,
    ) -> VitalTrendResponse:
        """Get vital trends over a date range.
        
        Validates: Requirements 16.2, 16.3
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            start_date: Start of period
            end_date: End of period
            family_member_id: Optional family member filter
            
        Returns:
            Vital trend response with data points and statistics
        """
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)
        
        # Get vitals for the period
        vitals = await self.repository.get_vitals_by_user(
            user_id,
            vital_type=vital_type,
            family_member_id=family_member_id,
            start_date=start_dt,
            end_date=end_dt,
            limit=1000,  # Get all readings for trend
            offset=0,
        )
        
        # Get statistics
        stats = await self.repository.get_vital_statistics(
            user_id, vital_type, family_member_id, start_dt, end_dt
        )
        
        # Get target range
        target_min, target_max = await self._get_target_range_values(
            user_id, vital_type, family_member_id
        )
        
        # Get unit from default ranges or first vital
        unit = DEFAULT_VITAL_RANGES.get(vital_type, {}).get("unit", "")
        if vitals and not unit:
            unit = vitals[0].unit
        
        # Build data points with warning levels
        data_points = []
        for vital in reversed(vitals):  # Chronological order
            warning_level = self._calculate_warning_level(
                vital.value, target_min, target_max
            )
            data_points.append(VitalTrendDataPoint(
                recorded_at=vital.recorded_at,
                value=vital.value,
                warning_level=warning_level,
            ))
        
        return VitalTrendResponse(
            vital_type=vital_type,
            unit=unit,
            data_points=data_points,
            min_value=stats["min_value"],
            max_value=stats["max_value"],
            avg_value=stats["avg_value"],
            target_min=target_min,
            target_max=target_max,
            period_start=start_date,
            period_end=end_date,
            total_readings=stats["count"],
        )
    
    async def get_vitals_dashboard(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
    ) -> VitalsDashboardResponse:
        """Get vitals dashboard overview.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter
            
        Returns:
            Dashboard response with summaries and recent readings
        """
        summaries = []
        out_of_range_count = 0
        
        # Get summary for each vital type
        for vital_type in VitalTypeEnum.ALL:
            latest = await self.repository.get_latest_vital(
                user_id, vital_type, family_member_id
            )
            
            # Get statistics for last 30 days
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=30)
            stats = await self.repository.get_vital_statistics(
                user_id, vital_type, family_member_id, start_dt, end_dt
            )
            
            # Get target range
            target_min, target_max = await self._get_target_range_values(
                user_id, vital_type, family_member_id
            )
            
            # Get unit
            unit = DEFAULT_VITAL_RANGES.get(vital_type, {}).get("unit", "")
            if latest and not unit:
                unit = latest.unit
            
            # Calculate warning level for latest
            latest_warning = None
            if latest:
                latest_warning = self._calculate_warning_level(
                    latest.value, target_min, target_max
                )
                if latest_warning != WarningLevel.NORMAL:
                    out_of_range_count += 1
            
            summaries.append(VitalSummary(
                vital_type=vital_type,
                unit=unit,
                latest_value=latest.value if latest else None,
                latest_recorded_at=latest.recorded_at if latest else None,
                latest_warning_level=latest_warning,
                avg_value=stats["avg_value"],
                min_value=stats["min_value"],
                max_value=stats["max_value"],
                reading_count=stats["count"],
                target_min=target_min,
                target_max=target_max,
            ))
        
        # Get recent readings
        recent_vitals = await self.repository.get_vitals_for_all_members(
            user_id, limit=10
        )
        
        recent_readings = []
        for vital in recent_vitals:
            warning_level = await self._get_warning_level(
                user_id, vital.vital_type, vital.value, vital.family_member_id
            )
            response = VitalWithFamilyMemberResponse(
                id=vital.id,
                user_id=vital.user_id,
                family_member_id=vital.family_member_id,
                vital_type=vital.vital_type,
                value=vital.value,
                unit=vital.unit,
                notes=vital.notes,
                recorded_at=vital.recorded_at,
                warning_level=warning_level,
                created_at=vital.created_at,
                updated_at=vital.updated_at,
                family_member_name=vital.family_member.name if vital.family_member else None,
            )
            recent_readings.append(response)
        
        return VitalsDashboardResponse(
            summaries=summaries,
            recent_readings=recent_readings,
            out_of_range_count=out_of_range_count,
        )
    
    # ========================================================================
    # PDF Export
    # ========================================================================
    
    async def export_vitals_report(
        self,
        user_id: UUID,
        request: VitalExportRequest,
    ) -> bytes:
        """Export vitals report as PDF.
        
        Validates: Requirements 16.5
        
        Args:
            user_id: User's UUID
            request: Export request parameters
            
        Returns:
            PDF file as bytes
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        )
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.linecharts import HorizontalLineChart
        
        # Validate family member if provided
        family_member_name = None
        if request.family_member_id is not None:
            family_member = await self.health_repository.get_family_member_by_id(
                request.family_member_id, user_id
            )
            if family_member is None:
                raise ValueError("Family member not found or does not belong to user")
            family_member_name = family_member.name
        
        # Determine which vital types to include
        vital_types = request.vital_types or VitalTypeEnum.ALL
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
        )
        normal_style = styles['Normal']
        
        # Build document content
        story = []
        
        # Title
        title = "Vitals Report"
        if family_member_name:
            title += f" - {family_member_name}"
        story.append(Paragraph(title, title_style))
        
        # Date range
        date_range = f"Period: {request.start_date.strftime('%B %d, %Y')} - {request.end_date.strftime('%B %d, %Y')}"
        story.append(Paragraph(date_range, normal_style))
        story.append(Spacer(1, 20))
        
        # Convert dates to datetime
        start_dt = datetime.combine(request.start_date, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(request.end_date, time.max).replace(tzinfo=timezone.utc)
        
        # Process each vital type
        for vital_type in vital_types:
            # Get vitals for this type
            vitals = await self.repository.get_vitals_by_user(
                user_id,
                vital_type=vital_type,
                family_member_id=request.family_member_id,
                start_date=start_dt,
                end_date=end_dt,
                limit=1000,
                offset=0,
            )
            
            if not vitals:
                continue
            
            # Get statistics
            stats = await self.repository.get_vital_statistics(
                user_id, vital_type, request.family_member_id, start_dt, end_dt
            )
            
            # Get target range
            target_min, target_max = await self._get_target_range_values(
                user_id, vital_type, request.family_member_id
            )
            
            # Get unit
            unit = DEFAULT_VITAL_RANGES.get(vital_type, {}).get("unit", "")
            if vitals and not unit:
                unit = vitals[0].unit
            
            # Section heading
            vital_name = vital_type.replace("_", " ").title()
            story.append(Paragraph(f"{vital_name} ({unit})", heading_style))
            
            # Statistics table
            stats_data = [
                ["Statistic", "Value"],
                ["Total Readings", str(stats["count"])],
                ["Average", f"{stats['avg_value']:.1f}" if stats["avg_value"] else "N/A"],
                ["Minimum", f"{stats['min_value']:.1f}" if stats["min_value"] else "N/A"],
                ["Maximum", f"{stats['max_value']:.1f}" if stats["max_value"] else "N/A"],
            ]
            
            if target_min is not None or target_max is not None:
                range_str = f"{target_min or 'N/A'} - {target_max or 'N/A'}"
                stats_data.append(["Target Range", range_str])
            
            stats_table = Table(stats_data, colWidths=[2*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 15))
            
            # Readings table (last 20)
            readings_data = [["Date/Time", "Value", "Status"]]
            for vital in vitals[:20]:
                warning = self._calculate_warning_level(vital.value, target_min, target_max)
                status = "Normal" if warning == WarningLevel.NORMAL else warning.replace("_", " ").title()
                readings_data.append([
                    vital.recorded_at.strftime("%Y-%m-%d %H:%M"),
                    f"{vital.value:.1f}",
                    status,
                ])
            
            readings_table = Table(readings_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            readings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(readings_table)
            story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _get_warning_level(
        self,
        user_id: UUID,
        vital_type: str,
        value: float,
        family_member_id: Optional[UUID] = None,
    ) -> str:
        """Get warning level for a vital reading.
        
        Validates: Requirements 16.3
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            value: Vital value
            family_member_id: Optional family member filter
            
        Returns:
            Warning level string
        """
        target_min, target_max = await self._get_target_range_values(
            user_id, vital_type, family_member_id
        )
        return self._calculate_warning_level(value, target_min, target_max)
    
    async def _get_target_range_values(
        self,
        user_id: UUID,
        vital_type: str,
        family_member_id: Optional[UUID] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Get target range values for a vital type.
        
        Validates: Requirements 16.4
        
        First checks for custom range, then falls back to defaults.
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            family_member_id: Optional family member filter
            
        Returns:
            Tuple of (min_value, max_value)
        """
        # Check for custom range
        custom_range = await self.repository.get_target_range(
            user_id, vital_type, family_member_id
        )
        
        if custom_range:
            return custom_range.min_value, custom_range.max_value
        
        # Fall back to defaults
        defaults = DEFAULT_VITAL_RANGES.get(vital_type, {})
        return defaults.get("min"), defaults.get("max")
    
    def _calculate_warning_level(
        self,
        value: float,
        target_min: Optional[float],
        target_max: Optional[float],
    ) -> str:
        """Calculate warning level based on value and target range.
        
        Validates: Requirements 16.3
        
        Args:
            value: Vital value
            target_min: Minimum acceptable value
            target_max: Maximum acceptable value
            
        Returns:
            Warning level string
        """
        if target_min is None and target_max is None:
            return WarningLevel.NORMAL
        
        # Check for critical levels (20% beyond normal range)
        if target_min is not None:
            critical_low = target_min * 0.8
            if value < critical_low:
                return WarningLevel.CRITICAL_LOW
            if value < target_min:
                return WarningLevel.LOW
        
        if target_max is not None:
            critical_high = target_max * 1.2
            if value > critical_high:
                return WarningLevel.CRITICAL_HIGH
            if value > target_max:
                return WarningLevel.HIGH
        
        return WarningLevel.NORMAL
    
    async def get_vital_types(self) -> List[dict]:
        """Get list of vital types with their default ranges.
        
        Returns:
            List of vital type info dicts
        """
        result = []
        for vital_type in VitalTypeEnum.ALL:
            defaults = DEFAULT_VITAL_RANGES.get(vital_type, {})
            result.append({
                "type": vital_type,
                "name": vital_type.replace("_", " ").title(),
                "default_unit": defaults.get("unit", ""),
                "default_min": defaults.get("min"),
                "default_max": defaults.get("max"),
            })
        return result
