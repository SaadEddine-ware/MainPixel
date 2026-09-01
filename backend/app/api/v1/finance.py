from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from uuid import UUID
from typing import List, Optional
from datetime import date, datetime, timezone
import random
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.finance import FeeStructure, Invoice, Payment
from app.models.student import Student
from app.models.school_class import SchoolClass
from app.utils.events import emit, EventTypes
from app.schemas.finance_schema import (
    FeeStructureCreate, FeeStructureUpdate, FeeStructureOut,
    InvoiceCreate, InvoiceUpdate, InvoiceOut,
    PaymentCreate, PaymentOut,
    BulkInvoiceCreate, BulkInvoiceResponse, BulkInvoiceItem,
    RevenueSummary, RevenueByMonth, RevenueByClass,
    StudentLedger, StudentLedgerEntry,
    OverdueInvoice,
    PaymentReconcileResponse, PaymentReconcileItem,
)

router = APIRouter()


# ---- Fee Structures ----

@router.get("/fee-structures", response_model=List[FeeStructureOut])
async def list_fee_structures(school_id: UUID, academic_year: str = None, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    query = select(FeeStructure).where(FeeStructure.school_id == school_id)
    if academic_year:
        query = query.where(FeeStructure.academic_year == academic_year)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/fee-structures", response_model=FeeStructureOut, status_code=status.HTTP_201_CREATED)
async def create_fee_structure(school_id: UUID, data: FeeStructureCreate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    obj = FeeStructure(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/fee-structures/{fee_id}", response_model=FeeStructureOut)
async def get_fee_structure(fee_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FeeStructure).where(FeeStructure.id == fee_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Fee structure not found")
    return obj


@router.put("/fee-structures/{fee_id}", response_model=FeeStructureOut)
async def update_fee_structure(fee_id: UUID, data: FeeStructureUpdate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FeeStructure).where(FeeStructure.id == fee_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Fee structure not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/fee-structures/{fee_id}")
async def delete_fee_structure(fee_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FeeStructure).where(FeeStructure.id == fee_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Fee structure not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Fee structure deleted"}


# ---- Invoices ----

@router.get("/invoices", response_model=List[InvoiceOut])
async def list_invoices(school_id: UUID, student_id: UUID = None, invoice_status: str = None, academic_year: str = None, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    query = select(Invoice).where(Invoice.school_id == school_id)
    if student_id:
        query = query.where(Invoice.student_id == student_id)
    if invoice_status:
        query = query.where(Invoice.status == invoice_status)
    if academic_year:
        query = query.join(FeeStructure, Invoice.fee_structure_id == FeeStructure.id).where(FeeStructure.academic_year == academic_year)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(school_id: UUID, data: InvoiceCreate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    invoice_number = f"INV-{random.randint(100000, 999999)}"
    obj = Invoice(school_id=school_id, invoice_number=invoice_number, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await emit(EventTypes.INVOICE_CREATED, {
        "school_id": school_id,
        "student_id": data.student_id,
        "invoice_id": obj.id,
        "amount": float(data.amount),
        "invoice_number": invoice_number,
    })

    return obj


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return obj


@router.put("/invoices/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(invoice_id: UUID, data: InvoiceUpdate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Invoice deleted"}


# ---- Bulk Invoice Generation ----

@router.post("/invoices/bulk", response_model=BulkInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_invoices(school_id: UUID, data: BulkInvoiceCreate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    fee_result = await db.execute(select(FeeStructure).where(FeeStructure.id == data.fee_structure_id))
    fee_structure = fee_result.scalar_one_or_none()
    if not fee_structure:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    if data.student_ids:
        students_result = await db.execute(
            select(Student).where(Student.id.in_(data.student_ids), Student.is_active == True)
        )
    elif data.class_id:
        students_result = await db.execute(
            select(Student).where(Student.class_id == data.class_id, Student.is_active == True)
        )
    else:
        students_result = await db.execute(
            select(Student).where(Student.school_id == school_id, Student.is_active == True)
        )

    students = students_result.scalars().all()
    if not students:
        raise HTTPException(status_code=400, detail="No students found for invoice generation")

    amount = data.override_amount or fee_structure.amount
    created_invoices = []

    for student in students:
        existing = await db.execute(
            select(Invoice).where(
                Invoice.student_id == student.id,
                Invoice.fee_structure_id == data.fee_structure_id,
                Invoice.school_id == school_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        invoice_number = f"INV-{random.randint(100000, 999999)}"
        invoice = Invoice(
            school_id=school_id,
            student_id=student.id,
            fee_structure_id=data.fee_structure_id,
            invoice_number=invoice_number,
            amount=amount,
            due_date=fee_structure.due_date,
        )
        db.add(invoice)
        await db.flush()
        created_invoices.append(BulkInvoiceItem(
            student_id=student.id,
            student_name=f"{student.first_name} {student.last_name}",
            invoice_number=invoice_number,
            amount=amount,
        ))

    await db.commit()
    return BulkInvoiceResponse(invoices_created=len(created_invoices), invoices=created_invoices)


# ---- Payments ----

@router.get("/payments", response_model=List[PaymentOut])
async def list_payments(school_id: UUID, student_id: UUID = None, invoice_id: UUID = None, payment_method: str = None, date_from: date = None, date_to: date = None, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    query = select(Payment).where(Payment.school_id == school_id)
    if student_id:
        query = query.where(Payment.student_id == student_id)
    if invoice_id:
        query = query.where(Payment.invoice_id == invoice_id)
    if payment_method:
        query = query.where(Payment.payment_method == payment_method)
    if date_from:
        query = query.where(Payment.payment_date >= date_from)
    if date_to:
        query = query.where(Payment.payment_date <= date_to)
    query = query.order_by(Payment.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def record_payment(school_id: UUID, data: PaymentCreate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == data.invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    obj = Payment(school_id=school_id, payment_date=data.payment_date or date.today(), **data.model_dump())
    db.add(obj)

    total_paid_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == data.invoice_id)
    )
    total_paid = float(total_paid_result.scalar() or 0) + float(data.amount)

    if total_paid >= float(invoice.amount):
        invoice.status = "paid"
    elif total_paid > 0:
        invoice.status = "partial"

    await db.commit()
    await db.refresh(obj)

    await emit(EventTypes.PAYMENT_RECEIVED, {
        "school_id": school_id,
        "student_id": data.student_id,
        "invoice_id": data.invoice_id,
        "amount": float(data.amount),
        "payment_id": obj.id,
    })

    return obj


@router.get("/payments/{payment_id}", response_model=PaymentOut)
async def get_payment(payment_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    return obj


@router.delete("/payments/{payment_id}")
async def delete_payment(payment_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Payment not found")

    invoice_result = await db.execute(select(Invoice).where(Invoice.id == obj.invoice_id))
    invoice = invoice_result.scalar_one_or_none()

    await db.delete(obj)

    if invoice:
        total_paid_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice.id,
                Payment.id != payment_id,
            )
        )
        total_paid = float(total_paid_result.scalar() or 0)
        if total_paid >= float(invoice.amount):
            invoice.status = "paid"
        elif total_paid > 0:
            invoice.status = "partial"
        else:
            invoice.status = "pending"

    await db.commit()
    return {"detail": "Payment deleted"}


# ---- Financial Reports ----

@router.get("/reports/revenue-summary", response_model=RevenueSummary)
async def get_revenue_summary(school_id: UUID, academic_year: str, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    invoices_result = await db.execute(
        select(Invoice).join(FeeStructure, Invoice.fee_structure_id == FeeStructure.id).where(
            Invoice.school_id == school_id,
            FeeStructure.academic_year == academic_year,
        )
    )
    invoices = invoices_result.scalars().all()

    total_expected = sum(float(inv.amount) for inv in invoices)
    total_invoices = len(invoices)
    paid_invoices = sum(1 for inv in invoices if inv.status == "paid")
    pending_invoices = sum(1 for inv in invoices if inv.status == "pending")
    overdue_invoices = sum(1 for inv in invoices if inv.status == "overdue")
    partial_invoices = sum(1 for inv in invoices if inv.status == "partial")

    total_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.school_id == school_id,
        )
    )
    total_revenue = float(total_revenue_result.scalar() or 0)

    collection_rate = round((total_revenue / total_expected * 100), 1) if total_expected > 0 else 0

    return RevenueSummary(
        academic_year=academic_year,
        total_revenue=total_revenue,
        total_expected=total_expected,
        collection_rate=collection_rate,
        total_invoices=total_invoices,
        paid_invoices=paid_invoices,
        pending_invoices=pending_invoices,
        overdue_invoices=overdue_invoices,
        partial_payments=partial_invoices,
    )


@router.get("/reports/revenue-by-month", response_model=List[RevenueByMonth])
async def get_revenue_by_month(school_id: UUID, academic_year: str, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Payment).where(Payment.school_id == school_id)
    )
    payments = result.scalars().all()

    months = {}
    for p in payments:
        if p.payment_date:
            month_key = p.payment_date.strftime("%Y-%m")
            if month_key not in months:
                months[month_key] = {"revenue": 0, "invoice_count": 0, "payment_count": 0}
            months[month_key]["revenue"] += float(p.amount)
            months[month_key]["payment_count"] += 1

    invoices_result = await db.execute(
        select(Invoice).join(FeeStructure, Invoice.fee_structure_id == FeeStructure.id).where(
            Invoice.school_id == school_id,
            FeeStructure.academic_year == academic_year,
        )
    )
    for inv in invoices_result.scalars().all():
        if inv.created_at:
            month_key = inv.created_at.strftime("%Y-%m")
            if month_key not in months:
                months[month_key] = {"revenue": 0, "invoice_count": 0, "payment_count": 0}
            months[month_key]["invoice_count"] += 1

    sorted_months = sorted(months.keys())
    return [
        RevenueByMonth(
            month=m,
            revenue=months[m]["revenue"],
            invoice_count=months[m]["invoice_count"],
            payment_count=months[m]["payment_count"],
        )
        for m in sorted_months
    ]


@router.get("/reports/revenue-by-class", response_model=List[RevenueByClass])
async def get_revenue_by_class(school_id: UUID, academic_year: str, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    classes_result = await db.execute(
        select(SchoolClass).where(SchoolClass.school_id == school_id)
    )
    classes = {c.id: c.name for c in classes_result.scalars().all()}

    result = []
    for class_id, class_name in classes.items():
        invoices_result = await db.execute(
            select(Invoice).join(Student, Invoice.student_id == Student.id).join(
                FeeStructure, Invoice.fee_structure_id == FeeStructure.id
            ).where(
                Student.school_id == school_id,
                Student.class_id == class_id,
                FeeStructure.academic_year == academic_year,
            )
        )
        invoices = invoices_result.scalars().all()
        total_expected = sum(float(inv.amount) for inv in invoices)

        total_collected = 0
        for inv in invoices:
            paid_result = await db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == inv.id)
            )
            total_collected += float(paid_result.scalar() or 0)

        collection_rate = round((total_collected / total_expected * 100), 1) if total_expected > 0 else 0
        result.append(RevenueByClass(
            class_id=class_id,
            class_name=class_name,
            total_expected=total_expected,
            total_collected=total_collected,
            collection_rate=collection_rate,
        ))

    return result


@router.get("/reports/student-ledger/{student_id}", response_model=StudentLedger)
async def get_student_ledger(student_id: UUID, academic_year: str, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    invoices_result = await db.execute(
        select(Invoice).join(FeeStructure, Invoice.fee_structure_id == FeeStructure.id).where(
            Invoice.student_id == student_id,
            FeeStructure.academic_year == academic_year,
        ).order_by(Invoice.created_at)
    )
    invoices = invoices_result.scalars().all()

    entries = []
    total_expected = Decimal("0")
    total_paid = Decimal("0")

    for inv in invoices:
        payments_result = await db.execute(
            select(Payment).where(Payment.invoice_id == inv.id).order_by(Payment.payment_date)
        )
        payments = payments_result.scalars().all()
        inv_paid = sum(float(p.amount) for p in payments)
        fee_result = await db.execute(select(FeeStructure).where(FeeStructure.id == inv.fee_structure_id))
        fee = fee_result.scalar_one_or_none()
        fee_name = fee.name if fee else "Unknown"

        entries.append(StudentLedgerEntry(
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            fee_name=fee_name,
            amount=inv.amount,
            status=inv.status,
            due_date=inv.due_date,
            payments=[PaymentOut.model_validate(p) for p in payments],
            total_paid=inv_paid,
            balance=float(inv.amount) - inv_paid,
        ))
        total_expected += inv.amount
        total_paid += inv_paid

    return StudentLedger(
        student_id=student_id,
        student_name=f"{student.first_name} {student.last_name}",
        academic_year=academic_year,
        entries=entries,
        total_expected=total_expected,
        total_paid=total_paid,
        total_balance=total_expected - total_paid,
    )


@router.get("/reports/overdue", response_model=List[OverdueInvoice])
async def get_overdue_invoices(school_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    today = date.today()
    result = await db.execute(
        select(Invoice).where(
            Invoice.school_id == school_id,
            Invoice.status.in_(["pending", "partial"]),
            Invoice.due_date < today,
        )
    )
    invoices = result.scalars().all()
    overdue_list = []

    for inv in invoices:
        student_result = await db.execute(select(Student).where(Student.id == inv.student_id))
        student = student_result.scalar_one_or_none()
        student_name = f"{student.first_name} {student.last_name}" if student else "Unknown"

        paid_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == inv.id)
        )
        amount_paid = float(paid_result.scalar() or 0)
        days_overdue = (today - inv.due_date).days if inv.due_date else 0

        overdue_list.append(OverdueInvoice(
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            student_id=inv.student_id,
            student_name=student_name,
            amount=inv.amount,
            amount_paid=amount_paid,
            balance=float(inv.amount) - amount_paid,
            due_date=inv.due_date,
            days_overdue=days_overdue,
        ))

    overdue_list.sort(key=lambda x: x.days_overdue, reverse=True)
    return overdue_list


# ---- Payment Reconciliation ----

@router.get("/reconcile", response_model=PaymentReconcileResponse)
async def reconcile_payments(school_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    payments_result = await db.execute(
        select(Payment).where(Payment.school_id == school_id).order_by(Payment.created_at)
    )
    payments = payments_result.scalars().all()
    items = []
    matched = 0
    mismatched = 0

    for p in payments:
        invoice_result = await db.execute(select(Invoice).where(Invoice.id == p.invoice_id))
        invoice = invoice_result.scalar_one_or_none()
        if not invoice:
            mismatched += 1
            items.append(PaymentReconcileItem(
                payment_id=p.id,
                invoice_id=p.invoice_id,
                invoice_number="MISSING",
                amount=p.amount,
                status="error",
                reconciled=False,
            ))
            continue

        total_paid_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == p.invoice_id)
        )
        total_paid = float(total_paid_result.scalar() or 0)
        is_reconciled = abs(total_paid - float(invoice.amount)) < 0.01 or total_paid > float(invoice.amount)

        if is_reconciled:
            matched += 1
        else:
            mismatched += 1

        items.append(PaymentReconcileItem(
            payment_id=p.id,
            invoice_id=p.invoice_id,
            invoice_number=invoice.invoice_number,
            amount=p.amount,
            status=invoice.status,
            reconciled=is_reconciled,
        ))

    return PaymentReconcileResponse(
        total_checked=len(payments),
        matched=matched,
        mismatched=mismatched,
        items=items,
    )
