# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import sbool
from frappe.utils.synchronization import filelock

from press.hq.authentication import authenticate_tenant
from press.hq.identifiers import tenant_record_name

REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,119}$")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def activate_yukon_send(
	tenant: str,
	plan_code: str,
	sender_email: str,
	sender_domain: str = "",
	tenant_url: str = "",
	reply_to: str = "",
	tracking_subdomain: str = "email",
	open_tracking: bool = False,
	click_tracking: bool = True,
) -> dict[str, str]:
	"""Activate one tenant plan behind a required idempotency key."""
	tenant_doc = authenticate_tenant(tenant)
	request_id = _idempotency_key()
	values = {
		"tenant": tenant_doc.name,
		"tenant_url": str(tenant_url or "").strip(),
		"plan": str(plan_code or "").strip().lower(),
		"sender_email": str(sender_email or "").strip().lower(),
		"sender_domain": _sender_domain(sender_email, sender_domain),
		"reply_to": str(reply_to or "").strip().lower(),
		"tracking_subdomain": str(tracking_subdomain or "email").strip().lower(),
		"open_tracking": sbool(open_tracking),
		"click_tracking": sbool(click_tracking),
	}
	fingerprint = _fingerprint(values)
	record_name = tenant_record_name("send", tenant_doc.name, request_id)
	with filelock(record_name):
		return _activate(request_id, values, fingerprint, tenant_doc)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_support_request(
	tenant: str,
	request_id: str,
	subject: str,
	description: str,
	category: str = "Technical issue",
	priority: str = "Normal",
	requester_email: str = "",
	page_url: str = "",
) -> dict[str, str]:
	"""Create one HaloPSA ticket under the tenant's mapped organization."""
	tenant_doc = authenticate_tenant(tenant)
	values = {
		"tenant": tenant_doc.name,
		"request_id": _request_id(request_id),
		"subject": str(subject or "").strip(),
		"description": str(description or "").strip(),
		"category": str(category or "Technical issue").strip(),
		"priority": str(priority or "Normal").strip(),
		"requester_email": str(requester_email or "").strip().lower(),
		"page_url": str(page_url or "").strip(),
	}
	fingerprint = _fingerprint(values)
	record_name = tenant_record_name("support", tenant_doc.name, values["request_id"])
	with filelock(record_name):
		request = _support_request(values, fingerprint)
		return request.submit_to_halo(tenant_doc)


@frappe.whitelist(methods=["POST"])
def issue_tenant_token(tenant: str) -> dict[str, str]:
	"""Rotate a tenant token and push it to the linked Press site once."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("HQ Tenant", tenant)
	doc.check_permission("write")
	token, job = doc.issue_token()
	return {"tenant": doc.name, "token": token, "configuration_job": job}


@frappe.whitelist(methods=["POST"])
def publish_tenant_configuration(tenant: str) -> dict[str, str]:
	"""Refresh plan and endpoint configuration without rotating credentials."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("HQ Tenant", tenant)
	doc.check_permission("write")
	job = doc.publish_configuration()
	return {"tenant": doc.name, "configuration_job": str(getattr(job, "name", "") or "")}


@frappe.whitelist(methods=["POST"])
def retire_previous_tenant_token(tenant: str) -> dict[str, str]:
	"""Retire the overlap token after its configuration job succeeds."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("HQ Tenant", tenant)
	doc.check_permission("write")
	doc.db_set("previous_token_digest", "")
	return {"tenant": doc.name, "status": "retired"}


def _activate(request_id: str, values: dict[str, Any], fingerprint: str, tenant_doc):
	record_name = tenant_record_name("send", tenant_doc.name, request_id)
	if frappe.db.exists("HQ Send Activation Request", record_name):
		request = frappe.get_doc("HQ Send Activation Request", record_name)
		if request.payload_hash != fingerprint:
			frappe.throw(_("Idempotency key was already used with different activation details"))
		subscription = frappe.get_doc("HQ Send Subscription", request.subscription)
		plan = frappe.get_doc("HQ Send Plan", request.plan)
		if request.status != "Completed":
			_update_subscription(subscription, request.plan, request.sender_email, request.sender_domain)
		return request.process(subscription, plan, tenant_doc)

	plan = frappe.get_doc("HQ Send Plan", values["plan"])
	if not plan.enabled:
		frappe.throw(_("That Yukon Send plan is not available"))
	subscription = _subscription(values)
	request = frappe.get_doc(
		{
			"doctype": "HQ Send Activation Request",
			"name": record_name,
			"request_id": request_id,
			"tenant": tenant_doc.name,
			"subscription": subscription.name,
			"plan": plan.name,
			"sender_email": values["sender_email"],
			"sender_domain": values["sender_domain"],
			"payload_hash": fingerprint,
			"requested_at": frappe.utils.now_datetime(),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return request.process(subscription, plan, tenant_doc)


def _subscription(values: dict[str, Any]):
	name = frappe.db.exists("HQ Send Subscription", values["tenant"])
	if name:
		doc = frappe.get_doc("HQ Send Subscription", name)
		_update_subscription(doc, values["plan"], values["sender_email"], values["sender_domain"])
		return doc
	return frappe.get_doc(
		{
			"doctype": "HQ Send Subscription",
			"tenant": values["tenant"],
			"plan": values["plan"],
			"sender_email": values["sender_email"],
			"sender_domain": values["sender_domain"],
		}
	).insert(ignore_permissions=True)


def _update_subscription(doc, plan: str, sender_email: str, sender_domain: str) -> None:
	doc.plan = plan
	doc.sender_email = sender_email
	doc.sender_domain = sender_domain
	doc.save(ignore_permissions=True)


def _support_request(values: dict[str, Any], fingerprint: str):
	record_name = tenant_record_name("support", values["tenant"], values["request_id"])
	if frappe.db.exists("HQ Support Request", record_name):
		request = frappe.get_doc("HQ Support Request", record_name)
		if request.payload_hash != fingerprint:
			frappe.throw(_("Support request ID was already used with different details"))
		return request
	return frappe.get_doc(
		{
			"doctype": "HQ Support Request",
			"name": record_name,
			"payload_hash": fingerprint,
			**values,
		}
	).insert(ignore_permissions=True)


def _idempotency_key() -> str:
	value = str(frappe.get_request_header("Idempotency-Key") or "").strip()
	if not value:
		frappe.throw(_("Idempotency-Key header is required"))
	return _request_id(value)


def _request_id(value: Any) -> str:
	request_id = str(value or "").strip()
	if not REQUEST_ID.fullmatch(request_id):
		frappe.throw(_("Invalid request identifier"))
	return request_id


def _sender_domain(sender_email: str, sender_domain: str) -> str:
	domain = str(sender_domain or "").strip().lower()
	return domain or str(sender_email or "").rsplit("@", 1)[-1].strip().lower()


def _fingerprint(values: dict[str, Any]) -> str:
	payload = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
	return hashlib.sha256(payload.encode()).hexdigest()
