from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import csv
from io import StringIO
from core.database import db
import asyncio

class GDPRCompliance:
    """GDPR Compliance module for MongoDB"""
    
    def __init__(self):
        pass

    async def export_user_data(self, user_id: str, format: str = "json") -> str:
        """Export all user data for GDPR compliance (Data Portability)"""
        user_data = {}

        try:
            # User profile
            profile = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
            user_data["profile"] = profile or {}

            # Enrolled courses
            courses = await db.user_courses.find({"user_id": user_id}, {"_id": 0}).to_list(None)
            user_data["courses"] = courses

            # Created projects
            projects = await db.projects.find({"creator_id": user_id}, {"_id": 0}).to_list(None)
            user_data["projects"] = projects

            # Transaction history
            transactions = await db.transactions.find(
                {"$or": [{"from_id": user_id}, {"to_id": user_id}]},
                {"_id": 0}
            ).to_list(None)
            user_data["transactions"] = transactions

            # Votes cast
            votes = await db.votes.find({"user_id": user_id}, {"_id": 0}).to_list(None)
            user_data["votes"] = votes

            # Created proposals
            proposals = await db.proposals.find({"creator_id": user_id}, {"_id": 0}).to_list(None)
            user_data["proposals"] = proposals

            # Achievements
            achievements = await db.user_achievements.find({"user_id": user_id}, {"_id": 0}).to_list(None)
            user_data["achievements"] = achievements

            # Daily rewards history
            daily_rewards = await db.daily_rewards.find({"user_id": user_id}, {"_id": 0}).to_list(None)
            user_data["daily_rewards"] = daily_rewards

            # Referrals
            referrals = await db.referrals.find(
                {"$or": [{"referrer_id": user_id}, {"referred_id": user_id}]},
                {"_id": 0}
            ).to_list(None)
            user_data["referrals"] = referrals

            # Job applications
            job_applications = await db.job_applications.find({"user_id": user_id}, {"_id": 0}).to_list(None)
            user_data["job_applications"] = job_applications

            # Messages (chat)
            messages = await db.messages.find(
                {"$or": [{"sender_id": user_id}, {"recipient_id": user_id}]},
                {"_id": 0}
            ).to_list(None)
            user_data["messages"] = messages

            # Consent records
            consent = await db.user_consent.find_one({"user_id": user_id}, {"_id": 0})
            user_data["consent_records"] = consent or {}

            # Metadata
            user_data["export_date"] = datetime.now().isoformat()
            user_data["data_controller"] = "REALUM Platform"
            user_data["data_protection_officer"] = "dpo@realum.io"

            if format == "json":
                return json.dumps(user_data, indent=2, default=str)
            elif format == "csv":
                return self._convert_to_csv(user_data)
            else:
                return json.dumps(user_data, indent=2, default=str)

        except Exception as e:
            raise Exception(f"Failed to export user data: {str(e)}")

    def _convert_to_csv(self, data: dict) -> str:
        """Convert user data to CSV format"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["Section", "Field", "Value"])

        for section, content in data.items():
            if isinstance(content, list):
                for idx, item in enumerate(content):
                    if isinstance(item, dict):
                        for key, value in item.items():
                            writer.writerow([f"{section}[{idx}]", key, str(value)])
            elif isinstance(content, dict):
                for key, value in content.items():
                    writer.writerow([section, key, str(value)])
            else:
                writer.writerow([section, "", str(content)])

        return output.getvalue()

    async def anonymize_user_data(self, user_id: str) -> bool:
        """Anonymize user data for soft deletion (Right to Erasure)"""
        try:
            anonymized_email = f"deleted_user_{user_id[:8]}@anonymized.realum"
            anonymized_username = f"deleted_user_{user_id[:8]}"

            await db.users.update_one(
                {"id": user_id},
                {"$set": {
                    "email": anonymized_email,
                    "username": anonymized_username,
                    "full_name": "Deleted User",
                    "bio": None,
                    "location": None,
                    "website": None,
                    "social_links": None,
                    "phone_number": None,
                    "avatar_url": None,
                    "deleted_at": datetime.now(),
                    "is_deleted": True
                }}
            )

            return True
        except Exception as e:
            raise Exception(f"Failed to anonymize user data: {str(e)}")

    async def delete_user_account(self, user_id: str, hard_delete: bool = False) -> bool:
        """Delete user account (soft or hard delete)"""
        try:
            if hard_delete:
                # Hard delete - remove all user data
                await db.user_achievements.delete_many({"user_id": user_id})
                await db.votes.delete_many({"user_id": user_id})
                await db.user_courses.delete_many({"user_id": user_id})
                await db.daily_rewards.delete_many({"user_id": user_id})
                await db.job_applications.delete_many({"user_id": user_id})
                await db.messages.delete_many({"$or": [{"sender_id": user_id}, {"recipient_id": user_id}]})
                await db.user_consent.delete_many({"user_id": user_id})
                await db.consent_history.delete_many({"user_id": user_id})
                await db.data_access_log.delete_many({"user_id": user_id})
                await db.users.delete_one({"id": user_id})
            else:
                # Soft delete - anonymize data
                await self.anonymize_user_data(user_id)

            return True
        except Exception as e:
            raise Exception(f"Failed to delete user account: {str(e)}")

    async def log_data_access(self, user_id: str, accessed_by: str, purpose: str, ip_address: Optional[str] = None):
        """Log data access for audit trail"""
        try:
            await db.data_access_log.insert_one({
                "user_id": user_id,
                "accessed_by": accessed_by,
                "purpose": purpose,
                "ip_address": ip_address,
                "accessed_at": datetime.now()
            })
        except Exception:
            pass

    async def get_consent_status(self, user_id: str) -> Dict[str, bool]:
        """Get user consent status for various data processing activities"""
        try:
            consent = await db.user_consent.find_one({"user_id": user_id}, {"_id": 0})

            if consent:
                return consent
            else:
                return {
                    "user_id": user_id,
                    "marketing_emails": False,
                    "data_analytics": False,
                    "third_party_sharing": False,
                    "cookie_consent": False,
                    "personalization": False,
                    "newsletter": False
                }
        except Exception:
            return {}

    async def update_consent(self, user_id: str, consent_type: str, value: bool) -> bool:
        """Update user consent for a specific processing activity"""
        try:
            existing = await db.user_consent.find_one({"user_id": user_id})

            if existing:
                await db.user_consent.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        consent_type: value,
                        "updated_at": datetime.now()
                    }}
                )
            else:
                await db.user_consent.insert_one({
                    "user_id": user_id,
                    consent_type: value,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })

            # Log consent change history
            await db.consent_history.insert_one({
                "user_id": user_id,
                "consent_type": consent_type,
                "value": value,
                "changed_at": datetime.now()
            })

            return True
        except Exception as e:
            raise Exception(f"Failed to update consent: {str(e)}")

    async def get_data_retention_info(self, user_id: str) -> Dict:
        """Get data retention policy information"""
        return {
            "user_data_retention_days": 2555,  # ~7 years
            "inactive_account_deletion_days": 730,  # 2 years
            "transaction_history_retention_years": 7,
            "can_request_deletion": True,
            "can_export_data": True,
            "data_portability": True,
            "data_controller": "REALUM Platform",
            "data_protection_officer": "dpo@realum.io",
            "legal_basis": ["consent", "legitimate_interest", "contract_performance"]
        }

    async def schedule_data_deletion(self, user_id: str, deletion_date: datetime) -> bool:
        """Schedule future data deletion"""
        try:
            await db.scheduled_deletions.insert_one({
                "user_id": user_id,
                "scheduled_for": deletion_date,
                "status": "pending",
                "created_at": datetime.now()
            })
            return True
        except Exception:
            return False

    async def cancel_scheduled_deletion(self, user_id: str) -> bool:
        """Cancel a scheduled data deletion"""
        try:
            result = await db.scheduled_deletions.delete_many(
                {"user_id": user_id, "status": "pending"}
            )
            return result.deleted_count > 0
        except Exception:
            return False

    async def get_data_access_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get history of who accessed user's data"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            history = await db.data_access_log.find(
                {"user_id": user_id, "accessed_at": {"$gte": cutoff}},
                {"_id": 0}
            ).sort("accessed_at", -1).to_list(100)
            return history
        except Exception:
            return []

# Global instance
gdpr_compliance = GDPRCompliance()
