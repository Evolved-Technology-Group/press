# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

from typing import Any

import frappe
import requests

API_BASE = "https://api.smtp2go.com/v3"
TENANT_ENDPOINTS = [
	"/domain/*",
	"/users/smtp/*",
	"/webhook/*",
	"/stats/email_cycle",
]


class DeliveryIntegrationError(RuntimeError):
	pass


class SMTP2GOClient:
	def __init__(self) -> None:
		self.api_key = str(frappe.conf.get("yukon_hq_smtp2go_api_key") or "").strip()
		if not self.api_key:
			raise DeliveryIntegrationError("Yukon Send provider is not configured")

	def create_subaccount(self, *, name: str, monthly_sends: int) -> str:
		result = self._post(
			"/subaccount/add",
			{"fullname": name, "limit": monthly_sends, "enforce_2fa": True},
		)
		identifier = _find_value(result, "id", "subaccount_id")
		if not identifier:
			raise DeliveryIntegrationError("Delivery provider did not return an account identifier")
		return identifier

	def update_subaccount(self, *, identifier: str, name: str, monthly_sends: int) -> None:
		self._post(
			"/subaccount/edit",
			{"id": identifier, "fullname": name, "limit": monthly_sends},
		)

	def create_api_key(self, *, subaccount_id: str, tenant_site: str) -> str:
		result = self._post(
			"/api_keys/add",
			{
				"description": f"Yukon Send — {tenant_site}",
				"subaccount_id": subaccount_id,
				"endpoints": TENANT_ENDPOINTS,
				"status": "allowed",
				"bounce_notifications": "drop",
			},
		)
		api_key = _find_value(result, "api_key", "key")
		if not api_key:
			raise DeliveryIntegrationError("Delivery provider did not return the scoped key")
		return api_key

	def _post(self, path: str, payload: dict[str, Any]) -> Any:
		try:
			response = requests.post(
				f"{API_BASE}{path}",
				headers={
					"Accept": "application/json",
					"Content-Type": "application/json",
					"X-Smtp2go-Api-Key": self.api_key,
				},
				json=payload,
				timeout=20,
			)
			body = response.json()
			if not response.ok or _provider_error(body):
				raise DeliveryIntegrationError("Delivery provider rejected the request")
			return body
		except DeliveryIntegrationError:
			raise
		except Exception as error:
			frappe.logger("yukon_hq", allow_site=True).error(
				"Delivery request failed for %s: %s", path, type(error).__name__
			)
			raise DeliveryIntegrationError("Delivery provider could not complete the request") from error


def _provider_error(payload: Any) -> Any:
	if not isinstance(payload, dict):
		return None
	if payload.get("error"):
		return payload["error"]
	data = payload.get("data")
	return data.get("error") if isinstance(data, dict) else None


def _find_value(payload: Any, *keys: str) -> str:
	for row in _candidate_rows(payload):
		for key in keys:
			if row.get(key):
				return str(row[key])
	return ""


def _candidate_rows(payload: Any) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	queue = [payload]
	while queue:
		value = queue.pop(0)
		if isinstance(value, dict):
			rows.append(value)
			queue.extend(value.values())
		elif isinstance(value, list):
			queue.extend(value)
	return rows
