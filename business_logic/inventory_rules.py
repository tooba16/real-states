from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from typing import Optional
import uuid

from models.inventory import Inventory, InventoryStatus
from models.builder import Builder
from models.investor import Investor
from models.investor_inventory_assignment import InvestorInventoryAssignment
from models.booking import Booking
from exceptions import (
    BuilderLimitExceededException,
    InvestorConsentRequiredException,
    HoldExpiredException,
    InvalidStatusTransitionException,
    DoubleBookingException
)
from core.config import settings

class InventoryBusinessLogic:
    @staticmethod
    async def validate_builder_project_limit(db: AsyncSession, builder_id: uuid.UUID):
        """Validate that builder hasn't exceeded project limit."""
        builder_result = await db.execute(
            select(Builder).filter(Builder.id == builder_id)
        )
        builder = builder_result.scalar_one_or_none()

        if not builder:
            raise ValueError("Builder not found")

        # Count active projects for this builder
        project_count_result = await db.execute(
            select(Inventory).filter(
                Inventory.builder_id == builder_id,
                Inventory.status != "cancelled"
            )
        )
        project_count = len(project_count_result.scalars().all())

        if project_count >= builder.max_projects:
            raise BuilderLimitExceededException(
                f"Maximum project limit ({builder.max_projects}) reached for this builder"
            )

    @staticmethod
    async def validate_investor_consent(db: AsyncSession, inventory_id: uuid.UUID):
        """Validate investor consent for locked inventory."""
        inventory_result = await db.execute(
            select(Inventory).filter(Inventory.id == inventory_id)
        )
        inventory = inventory_result.scalar_one_or_none()

        if not inventory:
            raise ValueError("Inventory not found")

        if inventory.investor_locked:
            # Check if there are any assignments requiring consent
            assignment_result = await db.execute(
                select(InvestorInventoryAssignment)
                .filter(
                    InvestorInventoryAssignment.inventory_id == inventory_id,
                    InvestorInventoryAssignment.consent_required == True
                )
            )
            assignments = assignment_result.scalars().all()

            if assignments:
                # In a real system, we would need to check if consent has been granted
                # For now, we'll assume consent is required and not yet given
                raise InvestorConsentRequiredException(
                    "Investor consent required for this locked inventory item"
                )

    @staticmethod
    async def check_hold_expiry(db: AsyncSession, inventory_id: uuid.UUID):
        """Check if inventory hold has expired."""
        inventory_result = await db.execute(
            select(Inventory).filter(Inventory.id == inventory_id)
        )
        inventory = inventory_result.scalar_one_or_none()

        if not inventory:
            raise ValueError("Inventory not found")

        if inventory.status == "on_hold" and inventory.hold_expiry_date:
            if datetime.utcnow() > inventory.hold_expiry_date:
                raise HoldExpiredException("Hold period has expired")

    @staticmethod
    async def validate_status_transition(
        current_status: InventoryStatus,
        new_status: InventoryStatus
    ) -> bool:
        """Validate if status transition is allowed."""
        allowed_transitions = {
            "available": ["on_hold", "booked"],
            "on_hold": ["available", "booked"],
            "booked": ["available", "sold"],
            "sold": [],
        }

        if current_status not in allowed_transitions:
            raise InvalidStatusTransitionException(f"Unknown current status: {current_status}")

        if new_status not in allowed_transitions[current_status]:
            raise InvalidStatusTransitionException(
                f"Invalid transition from {current_status} to {new_status}"
            )

        return True

    @staticmethod
    async def prevent_double_booking(db: AsyncSession, inventory_id: uuid.UUID):
        """Check if inventory is already booked by someone else."""
        inventory_result = await db.execute(
            select(Inventory).filter(Inventory.id == inventory_id)
        )
        inventory = inventory_result.scalar_one_or_none()

        if not inventory:
            raise ValueError("Inventory not found")

        if inventory.status in ["booked", "sold"]:
            raise DoubleBookingException("Property is already booked or sold")

    @staticmethod
    async def validate_inventory_availability(db: AsyncSession, inventory_id: uuid.UUID):
        """Validate all conditions for inventory availability."""
        # Check hold expiry
        await InventoryBusinessLogic.check_hold_expiry(db, inventory_id)

        # Check if it's already booked
        await InventoryBusinessLogic.prevent_double_booking(db, inventory_id)

        # Check investor consent if needed
        await InventoryBusinessLogic.validate_investor_consent(db, inventory_id)

        # Get current inventory status
        inventory_result = await db.execute(
            select(Inventory).filter(Inventory.id == inventory_id)
        )
        inventory = inventory_result.scalar_one_or_none()

        if inventory.status not in ["available", "on_hold"]:
            raise InvalidStatusTransitionException(
                f"Inventory is not available for booking (current status: {inventory.status})"
            )