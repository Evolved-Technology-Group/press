# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import frappe
import requests


class HaloIntegrationError(RuntimeError):
	pass


class HaloClient:
	def __init__(self) -> None:
		self.resource_url = _https_config("yukon_hq_halo_resource_url")
		self.auth_url = _https_config("yukon_hq_halo_auth_url")
		self.client_id = _required_config("yukon_hq_halo_client_id")
		self.client_secret = _required_config("yukon_hq_halo_client_secret")

	def upsert_subscription(self, subscription, plan, tenant) -> str:
		values: dict[str, Any] = {
			"client_id": _integer_id(tenant.halo_client_id, "Halo client"),
			"Name": plan.halo_subscription_name or plan.plan_name,
			"count": 1,
			"type": 1,
		}
		if subscription.halo_software_licence_id:
			values["id"] = _integer_id(
				subscription.halo_software_licence_id,
				"Halo software licence",
			)
		result = _first_row(self._post("/softwarelicence", [values]))
		identifier = result.get("id") or subscription.halo_software_licence_id
		if not identifier:
			raise HaloIntegrationError("HaloPSA did not return the subscription identifier")
		return str(identifier)

	def create_ticket(self, request, tenant) -> dict[str, Any]:
		values: dict[str, Any] = {
			"summary": request.subject,
			"details": request.halo_details(),
			"client_id": _integer_id(tenant.halo_client_id, "Halo client"),
			"tickettype_id": _integer_config("yukon_hq_halo_ticket_type_id"),
		}
		_add_optional_id(values, "site_id", tenant.halo_site_id)
		_add_optional_id(values, "user_id", tenant.halo_user_id)
		priority_ids = frappe.conf.get("yukon_hq_halo_priority_ids") or {}
		_add_optional_id(values, "priority_id", priority_ids.get(request.priority))
		result = _first_row(self._post("/Tickets", [values]))
		if not result.get("id"):
			raise HaloIntegrationError("HaloPSA did not return the ticket identifier")
		return result

	def _post(self, path: str, payload: Any) -> Any:
		try:
			response = requests.post(
				f"{self.resource_url}{path}",
				headers={"Authorization": f"Bearer {self._access_token()}"},
				json=payload,
				timeout=20,
			)
			response.raise_for_status()
			return response.json()
		except Exception as error:
			frappe.logger("yukon_hq", allow_site=True).error(
				"HaloPSA request failed for %s: %s", path, type(error).__name__
			)
			raise HaloIntegrationError("HaloPSA could not complete the request") from error

	def _access_token(self) -> str:
		cache_key = "yukon-hq:halo-access-token"
		cached = frappe.cache().get_value(cache_key)
		if cached:
			return str(cached)
		try:
			response = requests.post(
				self.auth_url,
				data={
					"grant_type": "client_credentials",
					"client_id": self.client_id,
					"client_secret": self.client_secret,
					"scope": "all",
				},
				timeout=20,
			)
			response.raise_for_status()
			payload = response.json()
			token = str(payload.get("access_token") or "")
			if not token:
				raise HaloIntegrationError("HaloPSA did not return an access token")
			ttl = max(60, int(payload.get("expires_in") or 3600) - 60)
			frappe.cache().set_value(cache_key, token, expires_in_sec=ttl)
			return token
		except HaloIntegrationError:
			raise
		except Exception as error:
			frappe.logger("yukon_hq", allow_site=True).error(
				"HaloPSA authentication failed: %s", type(error).__name__
			)
			raise HaloIntegrationError("HaloPSA authentication failed") from error


def ticket_url(ticket_id: str) -> str:
	template = str(frappe.conf.get("yukon_hq_halo_ticket_url_template") or "").strip()
	return template.replace("{ticket_id}", str(ticket_id)) if "{ticket_id}" in template else ""


def _https_config(key: str) -> str:
	value = _required_config(key).rstrip("/")
	parsed = urlparse(value)
	if parsed.scheme != "https" or not parsed.netloc:
		raise HaloIntegrationError(f"{key} must be an HTTPS URL")
	return value


def _required_config(key: str) -> str:
	value = str(frappe.conf.get(key) or "").strip()
	if not value:
		raise HaloIntegrationError(f"{key} is not configured")
	return value


def _integer_config(key: str) -> int:
	return _integer_id(_required_config(key), key)


def _integer_id(value: Any, label: str) -> int:
	try:
		return int(value)
	except (TypeError, ValueError) as error:
		raise HaloIntegrationError(f"{label} identifier is not configured") from error


def _add_optional_id(values: dict[str, Any], key: str, value: Any) -> None:
	if str(value or "").strip():
		values[key] = _integer_id(value, key)


def _first_row(payload: Any) -> dict[str, Any]:
	if isinstance(payload, list) and payload and isinstance(payload[0], dict):
		return payload[0]
	if isinstance(payload, dict):
		return payload
	return {}
