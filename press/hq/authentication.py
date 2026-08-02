# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import hashlib
import secrets

import frappe
from frappe import _


class HQAuthenticationError(frappe.AuthenticationError):
	pass


def authenticate_tenant(site: str):
	tenant_site = str(site or "").strip().lower()
	if not tenant_site or not frappe.db.exists("HQ Tenant", tenant_site):
		raise HQAuthenticationError(_("Unknown Yukon tenant"))

	tenant = frappe.get_doc("HQ Tenant", tenant_site)
	if tenant.status != "Active":
		raise HQAuthenticationError(_("Yukon tenant access is suspended"))

	token = _tenant_token()
	if not tenant.accepts_token(token):
		raise HQAuthenticationError(_("Invalid Yukon tenant credential"))
	return tenant


def token_digest(token: str) -> str:
	return hashlib.sha256(str(token or "").encode()).hexdigest()


def new_token() -> str:
	return secrets.token_urlsafe(48)


def _tenant_token() -> str:
	token = str(frappe.get_request_header("X-Yukon-Tenant-Token") or "").strip()
	if token:
		return token
	raise HQAuthenticationError(_("Missing Yukon tenant credential"))
