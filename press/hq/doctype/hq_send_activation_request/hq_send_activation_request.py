# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from press.hq.identifiers import tenant_record_name

REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,119}$")


class HQSendActivationRequest(Document):
	def autoname(self) -> None:
		self.name = tenant_record_name("send", self.tenant, self.request_id)

	def validate(self) -> None:
		self.request_id = str(self.request_id or "").strip()
		if not REQUEST_ID.fullmatch(self.request_id):
			frappe.throw("Invalid Yukon Send idempotency key")

	def process(self, subscription, plan, tenant) -> dict[str, str]:
		if self.status == "Completed":
			return subscription.activation_payload()
		self.status = "Processing"
		self.last_error = ""
		self.save(ignore_permissions=True)
		frappe.db.commit()
		try:
			subscription.activate(plan, tenant)
		except Exception as error:
			subscription.mark_failed(error)
			self.status = "Failed"
			self.last_error = f"{type(error).__name__}: activation failed"[:500]
			self.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.logger("yukon_hq", allow_site=True).error(frappe.get_traceback())
			raise
		self.status = "Completed"
		self.completed_at = now_datetime()
		self.save(ignore_permissions=True)
		frappe.db.commit()
		return subscription.activation_payload()
