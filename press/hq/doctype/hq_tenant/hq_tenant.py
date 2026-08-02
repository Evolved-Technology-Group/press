# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import secrets
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_url, now_datetime

from press.hq.authentication import new_token, token_digest


class HQTenant(Document):
	def validate(self) -> None:
		self.site = str(self.site or "").strip().lower()
		self.customer_name = str(self.customer_name or "").strip()
		if self.site:
			self.team = frappe.db.get_value("Site", self.site, "team")

	def accepts_token(self, token: str) -> bool:
		digest = token_digest(token)
		return any(
			stored and secrets.compare_digest(digest, stored)
			for stored in (self.tenant_token_digest, self.previous_token_digest)
		)

	def issue_token(self) -> tuple[str, str]:
		token = new_token()
		previous = self.tenant_token_digest
		job = self.publish_configuration(token=token)
		self.previous_token_digest = previous
		self.tenant_token_digest = token_digest(token)
		self.token_issued_at = now_datetime()
		self.save()
		return token, str(getattr(job, "name", "") or "")

	def publish_configuration(self, *, token: str = "") -> Any:
		control_url = str(frappe.conf.get("yukon_hq_public_url") or get_url()).rstrip("/")
		config: dict[str, Any] = {
			"yukon_send_plans": _plan_catalog(),
			"yukon_send_activation_url": (f"{control_url}/api/method/press.api.hq.activate_yukon_send"),
			"yukon_hq_support_url": (f"{control_url}/api/method/press.api.hq.submit_support_request"),
			"yukon_support_url": str(
				frappe.conf.get("yukon_support_url") or "https://www.yukoncrm.com/support"
			),
			"yukon_support_email": str(frappe.conf.get("yukon_support_email") or "support@yukoncrm.com"),
		}
		if token:
			config["yukon_send_activation_token"] = token
			config["yukon_hq_support_token"] = token
		return frappe.get_doc("Site", self.site).update_site_config(config)


def _plan_catalog() -> list[dict[str, Any]]:
	plans = frappe.get_all(
		"HQ Send Plan",
		filters={"enabled": 1},
		fields=[
			"name",
			"plan_name",
			"monthly_sends",
			"monthly_price",
			"currency",
			"description",
			"recommended",
		],
		order_by="monthly_sends asc",
	)
	return [
		{
			"code": plan.name,
			"name": plan.plan_name,
			"monthly_sends": int(plan.monthly_sends),
			"monthly_price": f"{flt(plan.monthly_price):.2f}",
			"currency": plan.currency,
			"description": plan.description or "",
			"recommended": bool(plan.recommended),
		}
		for plan in plans
	]
