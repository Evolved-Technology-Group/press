# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import flt

PLAN_CODE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
PROVIDER_LIMITS = {
	2000,
	5000,
	10000,
	20000,
	30000,
	40000,
	50000,
	60000,
	80000,
	100000,
	250000,
	500000,
	1000000,
	2000000,
	3000000,
	5000000,
	10000000,
}


class HQSendPlan(Document):
	def autoname(self) -> None:
		self._normalize()
		self.name = self.plan_code

	def validate(self) -> None:
		self._normalize()
		if not PLAN_CODE.fullmatch(self.plan_code):
			frappe.throw("Plan code must be a lowercase slug")
		if int(self.monthly_sends or 0) not in PROVIDER_LIMITS:
			frappe.throw("Monthly sends must match an available Yukon Send provider limit")
		if flt(self.monthly_price) < 0:
			frappe.throw("Monthly price cannot be negative")

	def _normalize(self) -> None:
		self.plan_code = str(self.plan_code or "").strip().lower()
		self.plan_name = str(self.plan_name or "").strip()
		self.halo_subscription_name = str(self.halo_subscription_name or "").strip()
