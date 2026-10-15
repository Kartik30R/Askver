import uuid
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models.deal import Deal
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.core.database import Base


def test_meeting_is_created_for_existing_deal_and_keeps_date_only_value():
    engine = create_engine("sqlite:///:memory:")
    for table_name in ["users", "deals", "meetings"]:
        Base.metadata.tables[table_name].create(bind=engine)

    with Session(bind=engine) as session:
        user_id = uuid.uuid4()
        deal_id = uuid.uuid4()

        user = User(
            id=user_id,
            email="user@example.com",
            name="Test User",
            password_hash="hash",
        )
        deal = Deal(
            id=deal_id,
            title="Acme expansion",
            target_company="Acme",
            target_industry="Software",
            meeting_objective="grow expansion",
            owner_id=user_id,
        )

        session.add_all([user, deal])
        session.commit()

        meeting = Meeting(
            deal_id=deal_id,
            title="Discovery call",
            meeting_date=date(2026, 10, 15),
            meeting_type="Discovery",
            attendees="Alice, Bob",
            objectives="Understand needs",
            summary="Initial stakeholder alignment",
            owner_id=user_id,
        )
        session.add(meeting)
        session.commit()
        session.refresh(meeting)

        assert meeting.id is not None
        assert meeting.meeting_date == date(2026, 10, 15)
        assert meeting.deal_id == deal_id


def test_meetings_are_sorted_chronologically_for_deal():
    engine = create_engine("sqlite:///:memory:")
    for table_name in ["users", "deals", "meetings"]:
        Base.metadata.tables[table_name].create(bind=engine)

    with Session(bind=engine) as session:
        owner_id = uuid.uuid4()
        deal_id = uuid.uuid4()

        session.add(
            User(
                id=owner_id,
                email="owner@example.com",
                name="Owner",
                password_hash="hash",
            )
        )
        session.add(
            Deal(
                id=deal_id,
                title="Deal",
                target_company="Target",
                target_industry="Tech",
                meeting_objective="Assess business fit",
                owner_id=owner_id,
            )
        )
        session.commit()

        older = Meeting(
            deal_id=deal_id,
            title="Older meeting",
            meeting_date=date(2026, 9, 5),
            meeting_type="Follow-up",
            owner_id=owner_id,
        )
        newer = Meeting(
            deal_id=deal_id,
            title="Newer meeting",
            meeting_date=date(2026, 9, 30),
            meeting_type="Discovery",
            owner_id=owner_id,
        )
        session.add_all([older, newer])
        session.commit()

        rows = session.execute(
            select(Meeting)
            .where(Meeting.deal_id == deal_id)
            .order_by(Meeting.meeting_date.desc())
        ).scalars().all()

        assert [row.title for row in rows] == ["Newer meeting", "Older meeting"]


def test_meeting_tracks_transcript_text_for_analysis():
    engine = create_engine("sqlite:///:memory:")
    for table_name in ["users", "deals", "meetings"]:
        Base.metadata.tables[table_name].create(bind=engine)

    with Session(bind=engine) as session:
        owner_id = uuid.uuid4()
        deal_id = uuid.uuid4()

        session.add(
            User(
                id=owner_id,
                email="owner@example.com",
                name="Owner",
                password_hash="hash",
            )
        )
        session.add(
            Deal(
                id=deal_id,
                title="Deal",
                target_company="Target",
                target_industry="Tech",
                meeting_objective="Assess business fit",
                owner_id=owner_id,
            )
        )
        session.commit()

        meeting = Meeting(
            deal_id=deal_id,
            title="Discovery call",
            meeting_date=date(2026, 10, 15),
            meeting_type="Discovery",
            attendees="Alice, Bob",
            objectives="Understand needs",
            transcript_text="Customer confirmed the pain is slow manual workflows and wants a phased rollout.",
            summary="Initial discovery aligned around urgency and change management.",
            owner_id=owner_id,
        )
        session.add(meeting)
        session.commit()
        session.refresh(meeting)

        assert meeting.transcript_text == "Customer confirmed the pain is slow manual workflows and wants a phased rollout."
