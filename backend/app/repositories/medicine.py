"""Medicine repository for database operations.

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medicine import Medicine, MedicineDose, DoseStatus
from app.schemas.medicine import MedicineCreate, MedicineUpdate


class MedicineRepository:
    """Repository for Medicine module database operations.
    
    Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # ========================================================================
    # Medicine Operations
    # ========================================================================
    
    async def create_medicine(
        self,
        user_id: UUID,
        data: MedicineCreate,
    ) -> Medicine:
        """Create a new medicine.
        
        Validates: Requirements 15.1
        
        Args:
            user_id: User's UUID
            data: Medicine creation data
            
        Returns:
            Created Medicine model instance
        """
        medicine = Medicine(
            user_id=user_id,
            health_record_id=data.health_record_id,
            name=data.name,
            dosage=data.dosage,
            frequency=data.frequency,
            instructions=data.instructions,
            reminder_times=data.reminder_times,
            start_date=data.start_date,
            end_date=data.end_date,
            total_quantity=data.total_quantity,
            remaining_quantity=data.remaining_quantity,
            refill_threshold=data.refill_threshold,
            is_active=True,
        )
        self.db.add(medicine)
        await self.db.flush()
        await self.db.refresh(medicine)
        return medicine
    
    async def get_medicine_by_id(
        self,
        medicine_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Medicine]:
        """Get a medicine by ID.
        
        Args:
            medicine_id: Medicine's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            Medicine if found, None otherwise
        """
        stmt = select(Medicine).where(Medicine.id == medicine_id)
        if user_id is not None:
            stmt = stmt.where(Medicine.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_medicines_by_user(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Medicine]:
        """Get all medicines for a user.
        
        Args:
            user_id: User's UUID
            is_active: Optional filter for active/inactive medicines
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Medicine model instances
        """
        stmt = select(Medicine).where(Medicine.user_id == user_id)
        
        if is_active is not None:
            stmt = stmt.where(Medicine.is_active == is_active)
        
        stmt = stmt.order_by(Medicine.name).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_medicines(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count total medicines for a user.
        
        Args:
            user_id: User's UUID
            is_active: Optional filter for active/inactive medicines
            
        Returns:
            Total count of medicines
        """
        stmt = select(func.count(Medicine.id)).where(Medicine.user_id == user_id)
        
        if is_active is not None:
            stmt = stmt.where(Medicine.is_active == is_active)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_medicine(
        self,
        medicine: Medicine,
        data: MedicineUpdate,
    ) -> Medicine:
        """Update a medicine.
        
        Args:
            medicine: Existing Medicine model instance
            data: Medicine update data
            
        Returns:
            Updated Medicine model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(medicine, field, value)
        
        await self.db.flush()
        await self.db.refresh(medicine)
        return medicine
    
    async def delete_medicine(self, medicine: Medicine) -> None:
        """Delete a medicine.
        
        Args:
            medicine: Medicine model instance to delete
        """
        await self.db.delete(medicine)
        await self.db.flush()
    
    async def get_medicines_needing_refill(
        self,
        user_id: UUID,
    ) -> List[Medicine]:
        """Get medicines that need refill (remaining <= threshold).
        
        Validates: Requirements 15.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of medicines needing refill
        """
        stmt = (
            select(Medicine)
            .where(
                Medicine.user_id == user_id,
                Medicine.is_active == True,
                Medicine.remaining_quantity.isnot(None),
                Medicine.remaining_quantity <= Medicine.refill_threshold,
            )
            .order_by(Medicine.remaining_quantity)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def decrement_remaining_quantity(
        self,
        medicine: Medicine,
        amount: int = 1,
    ) -> Medicine:
        """Decrement the remaining quantity of a medicine.
        
        Args:
            medicine: Medicine model instance
            amount: Amount to decrement (default 1)
            
        Returns:
            Updated Medicine model instance
        """
        if medicine.remaining_quantity is not None:
            medicine.remaining_quantity = max(0, medicine.remaining_quantity - amount)
            await self.db.flush()
            await self.db.refresh(medicine)
        return medicine
    
    # ========================================================================
    # Dose Operations
    # ========================================================================
    
    async def create_dose(
        self,
        medicine_id: UUID,
        scheduled_time: datetime,
    ) -> MedicineDose:
        """Create a new scheduled dose.
        
        Validates: Requirements 15.2
        
        Args:
            medicine_id: Medicine's UUID
            scheduled_time: When the dose is scheduled
            
        Returns:
            Created MedicineDose model instance
        """
        dose = MedicineDose(
            medicine_id=medicine_id,
            scheduled_time=scheduled_time,
            status=DoseStatus.SCHEDULED.value,
        )
        self.db.add(dose)
        await self.db.flush()
        await self.db.refresh(dose)
        return dose
    
    async def get_dose_by_id(
        self,
        dose_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[MedicineDose]:
        """Get a dose by ID.
        
        Args:
            dose_id: Dose's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            MedicineDose if found, None otherwise
        """
        stmt = (
            select(MedicineDose)
            .join(Medicine)
            .where(MedicineDose.id == dose_id)
        )
        if user_id is not None:
            stmt = stmt.where(Medicine.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_doses_by_medicine(
        self,
        medicine_id: UUID,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MedicineDose]:
        """Get doses for a medicine with optional filtering.
        
        Args:
            medicine_id: Medicine's UUID
            status: Optional status filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of MedicineDose model instances
        """
        stmt = select(MedicineDose).where(MedicineDose.medicine_id == medicine_id)
        
        if status is not None:
            stmt = stmt.where(MedicineDose.status == status)
        
        if start_date is not None:
            stmt = stmt.where(MedicineDose.scheduled_time >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(MedicineDose.scheduled_time <= end_date)
        
        stmt = stmt.order_by(MedicineDose.scheduled_time.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_doses(
        self,
        medicine_id: UUID,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count total doses for a medicine.
        
        Args:
            medicine_id: Medicine's UUID
            status: Optional status filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Total count of doses
        """
        stmt = select(func.count(MedicineDose.id)).where(
            MedicineDose.medicine_id == medicine_id
        )
        
        if status is not None:
            stmt = stmt.where(MedicineDose.status == status)
        
        if start_date is not None:
            stmt = stmt.where(MedicineDose.scheduled_time >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(MedicineDose.scheduled_time <= end_date)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_dose_status(
        self,
        dose: MedicineDose,
        status: str,
        taken_time: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> MedicineDose:
        """Update a dose status.
        
        Validates: Requirements 15.3, 15.4
        
        Args:
            dose: MedicineDose model instance
            status: New status
            taken_time: When the dose was taken (for taken status)
            notes: Optional notes
            
        Returns:
            Updated MedicineDose model instance
        """
        dose.status = status
        if taken_time is not None:
            dose.taken_time = taken_time
        if notes is not None:
            dose.notes = notes
        
        await self.db.flush()
        await self.db.refresh(dose)
        return dose
    
    async def mark_dose_reminder_sent(
        self,
        dose: MedicineDose,
        is_followup: bool = False,
    ) -> MedicineDose:
        """Mark that a reminder was sent for a dose.
        
        Args:
            dose: MedicineDose model instance
            is_followup: Whether this is a follow-up reminder
            
        Returns:
            Updated MedicineDose model instance
        """
        if is_followup:
            dose.followup_reminder_sent = True
        else:
            dose.reminder_sent = True
        
        await self.db.flush()
        await self.db.refresh(dose)
        return dose
    
    async def get_pending_dose_reminders(
        self,
        before_time: datetime,
    ) -> List[MedicineDose]:
        """Get doses that need reminders sent.
        
        Validates: Requirements 15.2
        
        Args:
            before_time: Get doses scheduled before this time
            
        Returns:
            List of doses needing reminders
        """
        stmt = (
            select(MedicineDose)
            .join(Medicine)
            .where(
                MedicineDose.status == DoseStatus.SCHEDULED.value,
                MedicineDose.scheduled_time <= before_time,
                MedicineDose.reminder_sent == False,
                Medicine.is_active == True,
            )
            .options(selectinload(MedicineDose.medicine))
            .order_by(MedicineDose.scheduled_time)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_missed_doses_needing_followup(
        self,
        grace_period_minutes: int = 30,
    ) -> List[MedicineDose]:
        """Get missed doses that need follow-up reminders.
        
        Validates: Requirements 15.4
        
        Args:
            grace_period_minutes: Minutes after scheduled time to consider missed
            
        Returns:
            List of missed doses needing follow-up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=grace_period_minutes)
        
        stmt = (
            select(MedicineDose)
            .join(Medicine)
            .where(
                MedicineDose.status == DoseStatus.SCHEDULED.value,
                MedicineDose.scheduled_time <= cutoff_time,
                MedicineDose.reminder_sent == True,
                MedicineDose.followup_reminder_sent == False,
                Medicine.is_active == True,
            )
            .options(selectinload(MedicineDose.medicine))
            .order_by(MedicineDose.scheduled_time)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_upcoming_doses(
        self,
        user_id: UUID,
        hours_ahead: int = 24,
    ) -> List[MedicineDose]:
        """Get upcoming doses for a user.
        
        Args:
            user_id: User's UUID
            hours_ahead: How many hours ahead to look
            
        Returns:
            List of upcoming doses
        """
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=hours_ahead)
        
        stmt = (
            select(MedicineDose)
            .join(Medicine)
            .where(
                Medicine.user_id == user_id,
                Medicine.is_active == True,
                MedicineDose.status == DoseStatus.SCHEDULED.value,
                MedicineDose.scheduled_time >= now,
                MedicineDose.scheduled_time <= end_time,
            )
            .options(selectinload(MedicineDose.medicine))
            .order_by(MedicineDose.scheduled_time)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    # ========================================================================
    # Adherence Statistics
    # ========================================================================
    
    async def get_adherence_stats(
        self,
        medicine_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get adherence statistics for a medicine.
        
        Validates: Requirements 15.6
        
        Args:
            medicine_id: Medicine's UUID
            start_date: Optional start of period
            end_date: Optional end of period
            
        Returns:
            Dict with adherence statistics
        """
        # Build base query
        conditions = [MedicineDose.medicine_id == medicine_id]
        
        if start_date is not None:
            conditions.append(MedicineDose.scheduled_time >= start_date)
        if end_date is not None:
            conditions.append(MedicineDose.scheduled_time <= end_date)
        
        # Count by status
        stmt = select(
            func.count(MedicineDose.id).label("total"),
            func.sum(
                case((MedicineDose.status == DoseStatus.TAKEN.value, 1), else_=0)
            ).label("taken"),
            func.sum(
                case((MedicineDose.status == DoseStatus.MISSED.value, 1), else_=0)
            ).label("missed"),
            func.sum(
                case((MedicineDose.status == DoseStatus.SKIPPED.value, 1), else_=0)
            ).label("skipped"),
        ).where(and_(*conditions))
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        total = row.total or 0
        taken = row.taken or 0
        missed = row.missed or 0
        skipped = row.skipped or 0
        
        # Calculate adherence percentage
        # Only count scheduled doses that have been resolved (taken, missed, skipped)
        resolved = taken + missed + skipped
        adherence_percentage = (taken / resolved * 100) if resolved > 0 else 0.0
        
        return {
            "total_scheduled": total,
            "total_taken": taken,
            "total_missed": missed,
            "total_skipped": skipped,
            "adherence_percentage": round(adherence_percentage, 2),
        }
    
    async def calculate_streak(
        self,
        medicine_id: UUID,
    ) -> tuple[int, int]:
        """Calculate current and longest streak for a medicine.
        
        Args:
            medicine_id: Medicine's UUID
            
        Returns:
            Tuple of (current_streak, longest_streak)
        """
        # Get all doses ordered by scheduled time
        stmt = (
            select(MedicineDose)
            .where(
                MedicineDose.medicine_id == medicine_id,
                MedicineDose.status.in_([
                    DoseStatus.TAKEN.value,
                    DoseStatus.MISSED.value,
                    DoseStatus.SKIPPED.value,
                ])
            )
            .order_by(MedicineDose.scheduled_time.desc())
        )
        result = await self.db.execute(stmt)
        doses = list(result.scalars().all())
        
        if not doses:
            return 0, 0
        
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        
        for dose in doses:
            if dose.status == DoseStatus.TAKEN.value:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                if current_streak == 0:
                    current_streak = temp_streak
                temp_streak = 0
        
        # If we haven't broken the streak yet
        if current_streak == 0:
            current_streak = temp_streak
        
        return current_streak, longest_streak
