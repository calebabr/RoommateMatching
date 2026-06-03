"""Report service — handles user reports and admin resolution."""
from datetime import datetime, timezone
from bson import ObjectId
from app.database import reports_collection


class ReportService:
    def __init__(self):
        self.reports = reports_collection

    async def create_report(
        self,
        reporter_id: int,
        reported_id: int,
        reason: str,
        description: str | None,
    ) -> dict:
        """Insert a new report document. Returns the created report."""
        if reporter_id == reported_id:
            raise ValueError("Cannot report yourself")

        doc = {
            "reportedUserId": reported_id,
            "reporterUserId": reporter_id,
            "reason": reason,
            "description": description,
            "status": "pending",
            "createdAt": datetime.now(timezone.utc),
            "reviewedAt": None,
            "reviewedBy": None,
            "resolution": None,
        }
        result = await self.reports.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        doc.pop("_id", None)
        return doc

    async def get_reports(self, status_filter: str | None = None) -> list[dict]:
        """Return all reports, optionally filtered by status."""
        query = {}
        if status_filter:
            query["status"] = status_filter

        docs = []
        async for doc in self.reports.find(query).sort("createdAt", -1):
            doc["id"] = str(doc.pop("_id"))
            docs.append(doc)
        return docs

    async def resolve_report(
        self,
        report_id: str,
        admin_id: int,
        resolution: str,
        status: str,
    ) -> dict:
        """Set status, reviewedAt, reviewedBy, and resolution on a report."""
        if status not in ("actioned", "dismissed"):
            raise ValueError("status must be 'actioned' or 'dismissed'")

        try:
            oid = ObjectId(report_id)
        except Exception:
            raise ValueError("Invalid report ID")

        result = await self.reports.find_one_and_update(
            {"_id": oid},
            {"$set": {
                "status": status,
                "resolution": resolution,
                "reviewedAt": datetime.now(timezone.utc),
                "reviewedBy": admin_id,
            }},
            return_document=True,
        )
        if not result:
            raise ValueError("Report not found")

        result["id"] = str(result.pop("_id"))
        return result
