# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address

from press.hq.halo import HaloClient, ticket_url
from press.hq.identifiers import tenant_record_name

REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,119}$")


class HQSupportRequest(Document):
	def autoname(self) -> None:
		self.name = tenant_record_name("support", self.tenant, self.request_id)

	def validate(self) -> None:
		self.request_id = str(self.request_id or "").strip()
		self.subject = str(self.subject or "").strip()[:140]
		self.requester_email = str(self.requester_email or "").strip().lower()
		validate_email_address(self.requester_email, throw=True)
		self.description = str(self.description or "").strip()
		self.page_url = str(self.page_url or "").strip()[:1000]
		if not REQUEST_ID.fullmatch(self.request_id):
			frappe.throw("Invalid support request identifier")

	def submit_to_halo(self, tenant) -> dict[str, str]:
		if self.status == "Submitted":
			return self.as_api_payload()
		self.status = "Submitting"
		self.last_error = ""
		self.save(ignore_permissions=True)
		frappe.db.commit()
		try:
			result = HaloClient().create_ticket(self, tenant)
		except Exception as error:
			self.status = "Failed"
			self.last_error = f"{type(error).__name__}: support submission failed"[:500]
			self.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.logger("yukon_hq", allow_site=True).error(frappe.get_traceback())
			raise
		self.halo_ticket_id = str(result["id"])
		self.halo_ticket_url = ticket_url(self.halo_ticket_id)
		self.status = "Submitted"
		self.submitted_at = now_datetime()
		self.save(ignore_permissions=True)
		frappe.db.commit()
		return self.as_api_payload()

	def halo_details(self) -> str:
		return "\n".join(
			[
				self.description,
				"",
				f"Yukon tenant: {self.tenant}",
				f"Yukon request: {self.request_id}",
				f"Requester: {self.requester_email}",
				f"Category: {self.category}",
				f"Page: {self.page_url or 'Not provided'}",
			]
		)

	def as_api_payload(self) -> dict[str, str]:
		return {
			"request_id": self.request_id,
			"status": self.status,
			"ticket_id": self.halo_ticket_id or "",
			"ticket_url": self.halo_ticket_url or "",
		}
