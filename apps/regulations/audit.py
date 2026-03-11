from apps.audit import AuditEvents, log_event


class RegulationsAuditService:
    OBJECT_TYPE = "regulation"

    @staticmethod
    def regulation_created(*, actor, regulation, ip_address=None):
        log_event(
            action=AuditEvents.REGULATION_CREATED,
            actor=actor,
            object_type=RegulationsAuditService.OBJECT_TYPE,
            object_id=str(regulation.id),
            category="content",
            ip_address=ip_address,
            metadata={
                "language": regulation.language,
                "type": regulation.type,
                "is_active": regulation.is_active,
            },
        )

    @staticmethod
    def regulation_updated(*, actor, regulation, changed_fields, ip_address=None):
        log_event(
            action=AuditEvents.REGULATION_UPDATED,
            actor=actor,
            object_type=RegulationsAuditService.OBJECT_TYPE,
            object_id=str(regulation.id),
            category="content",
            ip_address=ip_address,
            metadata={
                "changed_fields": sorted(changed_fields),
            },
        )

    @staticmethod
    def regulation_deleted(*, actor, regulation_id, ip_address=None):
        log_event(
            action=AuditEvents.REGULATION_DELETED,
            actor=actor,
            object_type=RegulationsAuditService.OBJECT_TYPE,
            object_id=str(regulation_id),
            category="content",
            ip_address=ip_address,
        )

    @staticmethod
    def regulation_acknowledged(*, actor, acknowledgement, ip_address=None, idempotent=False):
        log_event(
            action=AuditEvents.REGULATION_ACKNOWLEDGED,
            actor=actor,
            object_type="regulation_acknowledgement",
            object_id=str(acknowledgement.id),
            category="content",
            ip_address=ip_address,
            metadata={
                "user_id": acknowledgement.user_id,
                "full_name": acknowledgement.user_full_name,
                "regulation_id": str(acknowledgement.regulation_id),
                "regulation_title": acknowledgement.regulation_title,
                "acknowledged_at": acknowledgement.acknowledged_at.isoformat(),
                "idempotent": bool(idempotent),
            },
        )
