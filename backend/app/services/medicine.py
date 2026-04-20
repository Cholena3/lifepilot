"""Medicine service for medicine tracking and dose management.

Provides functionality for medicine CRUD operations, dose tracking,
adherence statistics, and reminder scheduling.

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medicine import Medicine, MedicineDose, DoseStatus, MedicineFrequency
from app.repositories.medicine import MedicineRepository
from app.schemas.medicine import (
    MedicineCreate,
    MedicineUpdate,
    MedicineResponse,
    DoseLogCreate,
    DoseResponse,
    AdherenceStats,
    OverallAdherenceStats,
    MedicineReminderResponse,
    RefillAlertResponse,
    PaginatedMedicineResponse,
    PaginatedDoseResponse,
)


class MedicineService:
    """Service for managing medicines and dose tracking.
    
    Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the medicine service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.repository = MedicineRepository(db)
    
    # ========================================================================
    # Medicine Operations
    # ========================================================================
    
    async def create_medicine(
        self,
        user_id: UUID,
        data: MedicineCreate,
    ) -> MedicineResponse:
        """Create a new medicine.
        
        Validates: Requirements 15.1
        
        Args:
            user_id: User's UUID
            data: Medicine creation data
            
        Returns:
            Created medicine response
        """
        medicine = await self.repository.create_medicine(user_id, data)
        await self.db.commit()
        
        # Schedule initial doses if reminder times are provided
        if data.reminder_times:
            await self._schedule_doses_for_medicine(medicine)
            await self.db.commit()
        
        return MedicineResponse.model_validate(medicine)
    
    async def get_medicine(
        self,
        user_id: UUID,
        medicine_id: UUID,
    ) -> Optional[MedicineResponse]:
        """Get a medicine by ID.
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            
        Returns:
            Medicine response if found, None otherwise
        """
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        return MedicineResponse.model_validate(medicine)
    
    async def list_medicines(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedMedicineResponse:
        """List all medicines for a user.
        
        Args:
            user_id: User's UUID
            is_active: Optional filter for active/inactive medicines
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated medicine response
        """
        offset = (page - 1) * page_size
        
        medicines = await self.repository.get_medicines_by_user(
            user_id, is_active=is_active, limit=page_size, offset=offset
        )
        total = await self.repository.count_medicines(user_id, is_active=is_active)
        
        items = [MedicineResponse.model_validate(m) for m in medicines]
        return PaginatedMedicineResponse.create(items, total, page, page_size)
    
    async def update_medicine(
        self,
        user_id: UUID,
        medicine_id: UUID,
        data: MedicineUpdate,
    ) -> Optional[MedicineResponse]:
        """Update a medicine.
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            data: Medicine update data
            
        Returns:
            Updated medicine response if found, None otherwise
        """
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        
        updated = await self.repository.update_medicine(medicine, data)
        await self.db.commit()
        return MedicineResponse.model_validate(updated)
    
    async def delete_medicine(
        self,
        user_id: UUID,
        medicine_id: UUID,
    ) -> bool:
        """Delete a medicine.
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            
        Returns:
            True if deleted, False if not found
        """
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return False
        
        await self.repository.delete_medicine(medicine)
        await self.db.commit()
        return True
    
    # ========================================================================
    # Dose Operations
    # ========================================================================
    
    async def log_dose(
        self,
        user_id: UUID,
        medicine_id: UUID,
        dose_id: UUID,
        data: DoseLogCreate,
    ) -> Optional[DoseResponse]:
        """Log a dose as taken or missed.
        
        Validates: Requirements 15.3, 15.4
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            dose_id: Dose's UUID
            data: Dose log data
            
        Returns:
            Updated dose response if found, None otherwise
        """
        # Verify medicine belongs to user
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        
        # Get the dose
        dose = await self.repository.get_dose_by_id(dose_id, user_id)
        if dose is None or dose.medicine_id != medicine_id:
            return None
        
        # Update dose status
        if data.taken:
            status = DoseStatus.TAKEN.value
            taken_time = data.taken_time or datetime.now(timezone.utc)
            
            # Decrement remaining quantity
            if medicine.remaining_quantity is not None:
                await self.repository.decrement_remaining_quantity(medicine)
        else:
            status = DoseStatus.MISSED.value
            taken_time = None
        
        updated = await self.repository.update_dose_status(
            dose, status, taken_time, data.notes
        )
        await self.db.commit()
        
        return DoseResponse.model_validate(updated)
    
    async def skip_dose(
        self,
        user_id: UUID,
        medicine_id: UUID,
        dose_id: UUID,
        notes: Optional[str] = None,
    ) -> Optional[DoseResponse]:
        """Skip a scheduled dose.
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            dose_id: Dose's UUID
            notes: Optional reason for skipping
            
        Returns:
            Updated dose response if found, None otherwise
        """
        # Verify medicine belongs to user
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        
        # Get the dose
        dose = await self.repository.get_dose_by_id(dose_id, user_id)
        if dose is None or dose.medicine_id != medicine_id:
            return None
        
        updated = await self.repository.update_dose_status(
            dose, DoseStatus.SKIPPED.value, notes=notes
        )
        await self.db.commit()
        
        return DoseResponse.model_validate(updated)
    
    async def get_doses(
        self,
        user_id: UUID,
        medicine_id: UUID,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Optional[PaginatedDoseResponse]:
        """Get doses for a medicine.
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            status: Optional status filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated dose response if medicine found, None otherwise
        """
        # Verify medicine belongs to user
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        
        offset = (page - 1) * page_size
        
        doses = await self.repository.get_doses_by_medicine(
            medicine_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )
        total = await self.repository.count_doses(
            medicine_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        
        items = [DoseResponse.model_validate(d) for d in doses]
        return PaginatedDoseResponse.create(items, total, page, page_size)
    
    async def get_upcoming_reminders(
        self,
        user_id: UUID,
        hours_ahead: int = 24,
    ) -> List[MedicineReminderResponse]:
        """Get upcoming medicine reminders for a user.
        
        Validates: Requirements 15.2
        
        Args:
            user_id: User's UUID
            hours_ahead: How many hours ahead to look
            
        Returns:
            List of upcoming reminders
        """
        doses = await self.repository.get_upcoming_doses(user_id, hours_ahead)
        
        return [
            MedicineReminderResponse(
                dose_id=dose.id,
                medicine_id=dose.medicine_id,
                medicine_name=dose.medicine.name,
                dosage=dose.medicine.dosage,
                scheduled_time=dose.scheduled_time,
                instructions=dose.medicine.instructions,
            )
            for dose in doses
        ]
    
    # ========================================================================
    # Adherence Statistics
    # ========================================================================
    
    async def get_adherence_stats(
        self,
        user_id: UUID,
        medicine_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[AdherenceStats]:
        """Get adherence statistics for a medicine.
        
        Validates: Requirements 15.6
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            start_date: Optional start of period
            end_date: Optional end of period
            
        Returns:
            Adherence statistics if medicine found, None otherwise
        """
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        
        # Convert dates to datetime for query
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc) if start_date else None
        end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc) if end_date else None
        
        stats = await self.repository.get_adherence_stats(medicine_id, start_dt, end_dt)
        current_streak, longest_streak = await self.repository.calculate_streak(medicine_id)
        
        return AdherenceStats(
            medicine_id=medicine_id,
            medicine_name=medicine.name,
            total_scheduled=stats["total_scheduled"],
            total_taken=stats["total_taken"],
            total_missed=stats["total_missed"],
            total_skipped=stats["total_skipped"],
            adherence_percentage=stats["adherence_percentage"],
            streak_current=current_streak,
            streak_longest=longest_streak,
            period_start=start_date,
            period_end=end_date,
        )
    
    async def get_overall_adherence_stats(
        self,
        user_id: UUID,
    ) -> OverallAdherenceStats:
        """Get overall adherence statistics across all medicines.
        
        Validates: Requirements 15.6
        
        Args:
            user_id: User's UUID
            
        Returns:
            Overall adherence statistics
        """
        medicines = await self.repository.get_medicines_by_user(user_id)
        active_medicines = [m for m in medicines if m.is_active]
        
        medicine_stats = []
        total_taken = 0
        total_resolved = 0
        
        for medicine in medicines:
            stats = await self.repository.get_adherence_stats(medicine.id)
            current_streak, longest_streak = await self.repository.calculate_streak(medicine.id)
            
            medicine_stats.append(AdherenceStats(
                medicine_id=medicine.id,
                medicine_name=medicine.name,
                total_scheduled=stats["total_scheduled"],
                total_taken=stats["total_taken"],
                total_missed=stats["total_missed"],
                total_skipped=stats["total_skipped"],
                adherence_percentage=stats["adherence_percentage"],
                streak_current=current_streak,
                streak_longest=longest_streak,
            ))
            
            total_taken += stats["total_taken"]
            total_resolved += stats["total_taken"] + stats["total_missed"] + stats["total_skipped"]
        
        overall_adherence = (total_taken / total_resolved * 100) if total_resolved > 0 else 0.0
        
        # Get medicines needing refill
        refill_medicines = await self.repository.get_medicines_needing_refill(user_id)
        
        return OverallAdherenceStats(
            total_medicines=len(medicines),
            active_medicines=len(active_medicines),
            overall_adherence_percentage=round(overall_adherence, 2),
            medicines_needing_refill=len(refill_medicines),
            medicines=medicine_stats,
        )
    
    # ========================================================================
    # Refill Alerts
    # ========================================================================
    
    async def get_refill_alerts(
        self,
        user_id: UUID,
    ) -> List[RefillAlertResponse]:
        """Get medicines that need refill.
        
        Validates: Requirements 15.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of refill alerts
        """
        medicines = await self.repository.get_medicines_needing_refill(user_id)
        
        alerts = []
        for medicine in medicines:
            # Estimate days until empty based on frequency
            days_until_empty = self._estimate_days_until_empty(medicine)
            
            alerts.append(RefillAlertResponse(
                medicine_id=medicine.id,
                medicine_name=medicine.name,
                remaining_quantity=medicine.remaining_quantity or 0,
                refill_threshold=medicine.refill_threshold,
                days_until_empty=days_until_empty,
            ))
        
        return alerts
    
    def _estimate_days_until_empty(self, medicine: Medicine) -> Optional[int]:
        """Estimate days until medicine runs out based on frequency.
        
        Args:
            medicine: Medicine model instance
            
        Returns:
            Estimated days until empty, or None if cannot calculate
        """
        if medicine.remaining_quantity is None:
            return None
        
        doses_per_day = self._get_doses_per_day(medicine.frequency)
        if doses_per_day == 0:
            return None
        
        return int(medicine.remaining_quantity / doses_per_day)
    
    def _get_doses_per_day(self, frequency: str) -> float:
        """Get number of doses per day based on frequency.
        
        Args:
            frequency: Medicine frequency
            
        Returns:
            Number of doses per day
        """
        frequency_map = {
            MedicineFrequency.ONCE_DAILY.value: 1.0,
            MedicineFrequency.TWICE_DAILY.value: 2.0,
            MedicineFrequency.THREE_TIMES_DAILY.value: 3.0,
            MedicineFrequency.FOUR_TIMES_DAILY.value: 4.0,
            MedicineFrequency.EVERY_OTHER_DAY.value: 0.5,
            MedicineFrequency.WEEKLY.value: 1/7,
            MedicineFrequency.AS_NEEDED.value: 0,
            MedicineFrequency.CUSTOM.value: 1.0,  # Default assumption
        }
        return frequency_map.get(frequency, 1.0)
    
    # ========================================================================
    # Dose Scheduling
    # ========================================================================
    
    async def _schedule_doses_for_medicine(
        self,
        medicine: Medicine,
        days_ahead: int = 7,
    ) -> List[MedicineDose]:
        """Schedule doses for a medicine for the next N days.
        
        Args:
            medicine: Medicine model instance
            days_ahead: Number of days to schedule ahead
            
        Returns:
            List of created doses
        """
        if not medicine.reminder_times:
            return []
        
        doses = []
        today = date.today()
        start = max(today, medicine.start_date)
        end = medicine.end_date or (today + timedelta(days=days_ahead))
        
        current_date = start
        while current_date <= end and current_date <= today + timedelta(days=days_ahead):
            for time_str in medicine.reminder_times:
                hour, minute = map(int, time_str.split(":"))
                scheduled_time = datetime.combine(
                    current_date,
                    time(hour, minute),
                    tzinfo=timezone.utc,
                )
                
                # Only schedule future doses
                if scheduled_time > datetime.now(timezone.utc):
                    dose = await self.repository.create_dose(
                        medicine.id, scheduled_time
                    )
                    doses.append(dose)
            
            current_date += timedelta(days=1)
        
        return doses
    
    async def schedule_doses(
        self,
        user_id: UUID,
        medicine_id: UUID,
        days_ahead: int = 7,
    ) -> Optional[int]:
        """Schedule doses for a medicine.
        
        Args:
            user_id: User's UUID
            medicine_id: Medicine's UUID
            days_ahead: Number of days to schedule ahead
            
        Returns:
            Number of doses scheduled, or None if medicine not found
        """
        medicine = await self.repository.get_medicine_by_id(medicine_id, user_id)
        if medicine is None:
            return None
        
        doses = await self._schedule_doses_for_medicine(medicine, days_ahead)
        await self.db.commit()
        
        return len(doses)
