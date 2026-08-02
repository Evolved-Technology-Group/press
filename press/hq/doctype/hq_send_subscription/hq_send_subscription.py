# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address

from press.hq.halo import HaloClient
from press.hq.smtp2go import SMTP2GOClient

DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class HQSendSubscription(Document):
	def validate(self) -> None:
		self.sender_email = str(self.sender_email or "").strip().lower()
		validate_email_address(self.sender_email, throw=True)
		self.sender_domain = str(self.sender_domain or "").strip().lower()
		if not DOMAIN.fullmatch(self.sender_domain):
			frappe.throw("Enter a valid sender domain")
		email_domain = self.sender_email.rsplit("@", 1)[-1]
		if email_domain != self.sender_domain and not email_domain.endswith(f".{self.sender_domain}"):
			frappe.throw("Sender email must belong to the sender domain")

	def activate(self, plan, tenant) -> None:
		self.status = "Activating"
		self.plan = plan.name
		self.last_error = ""
		self.save(ignore_permissions=True)
		frappe.db.commit()

		provider = SMTP2GOClient()
		if self.provider_subaccount_id:
			provider.update_subaccount(
				identifier=self.provider_subaccount_id,
				name=tenant.customer_name,
				monthly_sends=plan.monthly_sends,
			)
		else:
			self.provider_subaccount_id = provider.create_subaccount(
				name=tenant.customer_name,
				monthly_sends=plan.monthly_sends,
			)
			self.save(ignore_permissions=True)
			frappe.db.commit()

		if not self.get_password("provider_api_key", raise_exception=False):
			self.provider_api_key = provider.create_api_key(
				subaccount_id=self.provider_subaccount_id,
				tenant_site=self.tenant,
			)
			self.save(ignore_permissions=True)
			frappe.db.commit()

		self.halo_software_licence_id = HaloClient().upsert_subscription(self, plan, tenant)
		self.status = "Active"
		self.activated_at = now_datetime()
		self.save(ignore_permissions=True)
		frappe.db.commit()

	def mark_failed(self, error: Exception) -> None:
		self.status = "Failed"
		self.last_error = _safe_error(error)
		self.save(ignore_permissions=True)
		frappe.db.commit()

	def activation_payload(self) -> dict[str, str]:
		return {
			"status": self.status.lower(),
			"subscription_id": self.name,
			"delivery_api_key": self.get_password("provider_api_key"),
			"delivery_account_id": self.provider_subaccount_id or "",
		}


def _safe_error(error: Exception) -> str:
	return f"{type(error).__name__}: Yukon Send activation failed"[:500]
