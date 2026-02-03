from datetime import datetime
from typing import Dict, List, Optional
import json
import csv
from io import StringIO
from supabase import Client
import asyncio

class GDPRCompliance:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def export_user_data(self, user_id: str, format: str = "json") -> str:
        user_data = {}

        try:
            profile = self.supabase.table("users").select("*").eq("id", user_id).execute()
            user_data["profile"] = profile.data[0] if profile.data else {}

            courses = self.supabase.table("user_courses").select("*").eq("user_id", user_id).execute()
            user_data["courses"] = courses.data

            projects = self.supabase.table("projects").select("*").eq("creator_id", user_id).execute()
            user_data["projects"] = projects.data

            transactions = self.supabase.table("transactions").select("*").eq("user_id", user_id).execute()
            user_data["transactions"] = transactions.data

            votes = self.supabase.table("votes").select("*").eq("user_id", user_id).execute()
            user_data["votes"] = votes.data

            proposals = self.supabase.table("proposals").select("*").eq("creator_id", user_id).execute()
            user_data["proposals"] = proposals.data

            nfts = self.supabase.table("nfts").select("*").eq("owner_id", user_id).execute()
            user_data["nfts"] = nfts.data

            achievements = self.supabase.table("user_achievements").select("*").eq("user_id", user_id).execute()
            user_data["achievements"] = achievements.data

            user_data["export_date"] = datetime.now().isoformat()
            user_data["data_controller"] = "REALUM Platform"

            if format == "json":
                return json.dumps(user_data, indent=2, default=str)
            elif format == "csv":
                return self._convert_to_csv(user_data)
            else:
                return json.dumps(user_data, indent=2, default=str)

        except Exception as e:
            raise Exception(f"Failed to export user data: {str(e)}")

    def _convert_to_csv(self, data: dict) -> str:
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
        try:
            anonymized_email = f"deleted_user_{user_id[:8]}@anonymized.realum"
            anonymized_username = f"deleted_user_{user_id[:8]}"

            self.supabase.table("users").update({
                "email": anonymized_email,
                "username": anonymized_username,
                "full_name": "Deleted User",
                "bio": None,
                "location": None,
                "website": None,
                "social_links": None,
                "phone_number": None,
                "deleted_at": datetime.now().isoformat()
            }).eq("id", user_id).execute()

            return True
        except Exception as e:
            raise Exception(f"Failed to anonymize user data: {str(e)}")

    async def delete_user_account(self, user_id: str, hard_delete: bool = False) -> bool:
        try:
            if hard_delete:
                self.supabase.table("user_achievements").delete().eq("user_id", user_id).execute()
                self.supabase.table("votes").delete().eq("user_id", user_id).execute()
                self.supabase.table("user_courses").delete().eq("user_id", user_id).execute()
                self.supabase.table("transactions").delete().eq("user_id", user_id).execute()
                self.supabase.table("projects").delete().eq("creator_id", user_id).execute()
                self.supabase.table("proposals").delete().eq("creator_id", user_id).execute()
                self.supabase.table("users").delete().eq("id", user_id).execute()
            else:
                await self.anonymize_user_data(user_id)

            return True
        except Exception as e:
            raise Exception(f"Failed to delete user account: {str(e)}")

    async def log_data_access(self, user_id: str, accessed_by: str, purpose: str):
        try:
            self.supabase.table("data_access_log").insert({
                "user_id": user_id,
                "accessed_by": accessed_by,
                "purpose": purpose,
                "accessed_at": datetime.now().isoformat()
            }).execute()
        except Exception:
            pass

    async def get_consent_status(self, user_id: str) -> Dict[str, bool]:
        try:
            consent = self.supabase.table("user_consent").select("*").eq("user_id", user_id).execute()

            if consent.data:
                return consent.data[0]
            else:
                return {
                    "marketing_emails": False,
                    "data_analytics": False,
                    "third_party_sharing": False,
                    "cookie_consent": False
                }
        except Exception:
            return {}

    async def update_consent(self, user_id: str, consent_type: str, value: bool) -> bool:
        try:
            existing = self.supabase.table("user_consent").select("*").eq("user_id", user_id).execute()

            if existing.data:
                self.supabase.table("user_consent").update({
                    consent_type: value,
                    "updated_at": datetime.now().isoformat()
                }).eq("user_id", user_id).execute()
            else:
                self.supabase.table("user_consent").insert({
                    "user_id": user_id,
                    consent_type: value,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }).execute()

            self.supabase.table("consent_history").insert({
                "user_id": user_id,
                "consent_type": consent_type,
                "value": value,
                "changed_at": datetime.now().isoformat()
            }).execute()

            return True
        except Exception as e:
            raise Exception(f"Failed to update consent: {str(e)}")

    async def get_data_retention_info(self, user_id: str) -> Dict:
        return {
            "user_data_retention_days": 2555,
            "inactive_account_deletion_days": 730,
            "transaction_history_retention_years": 7,
            "can_request_deletion": True,
            "can_export_data": True,
            "data_portability": True
        }

    async def schedule_data_deletion(self, user_id: str, deletion_date: datetime) -> bool:
        try:
            self.supabase.table("scheduled_deletions").insert({
                "user_id": user_id,
                "scheduled_for": deletion_date.isoformat(),
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }).execute()
            return True
        except Exception:
            return False

    async def cancel_scheduled_deletion(self, user_id: str) -> bool:
        try:
            self.supabase.table("scheduled_deletions").delete().eq("user_id", user_id).eq("status", "pending").execute()
            return True
        except Exception:
            return False
