# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests import UnitTestCase

from press.api.hq import _fingerprint, _request_id
from press.hq.authentication import new_token, token_digest
from press.hq.identifiers import tenant_record_name
from press.hq.smtp2go import _find_value


class TestHQHelpers(UnitTestCase):
	def test_tenant_tokens_are_random_and_stored_as_digests(self) -> None:
		first = new_token()
		second = new_token()
		self.assertNotEqual(first, second)
		self.assertEqual(len(token_digest(first)), 64)
		self.assertNotIn(first, token_digest(first))

	def test_provider_identifier_is_found_in_nested_responses(self) -> None:
		payload = {"data": {"results": [{"subaccount_id": "tenant-42"}]}}
		self.assertEqual(_find_value(payload, "id", "subaccount_id"), "tenant-42")

	def test_fingerprint_is_stable_across_key_order(self) -> None:
		self.assertEqual(_fingerprint({"b": 2, "a": 1}), _fingerprint({"a": 1, "b": 2}))

	def test_request_identifiers_are_bounded_safe_strings(self) -> None:
		self.assertEqual(_request_id("ys-01234567"), "ys-01234567")
		with self.assertRaises(frappe.ValidationError):
			_request_id("spaces are not accepted")

	def test_idempotency_rows_are_namespaced_by_tenant(self) -> None:
		first = tenant_record_name("support", "one.yukoncrm.com", "YUK-SUP-2026-00001")
		second = tenant_record_name("support", "two.yukoncrm.com", "YUK-SUP-2026-00001")
		self.assertNotEqual(first, second)
