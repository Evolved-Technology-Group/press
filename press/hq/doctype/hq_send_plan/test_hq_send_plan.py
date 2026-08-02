# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests import UnitTestCase


class TestHQSendPlan(UnitTestCase):
	def test_plan_normalizes_its_operator_code(self) -> None:
		plan = frappe.get_doc(
			{
				"doctype": "HQ Send Plan",
				"plan_code": " Starter-2K ",
				"plan_name": "Starter",
				"monthly_sends": 2000,
				"monthly_price": 19,
				"halo_subscription_name": "Yukon Send Starter",
			}
		)
		plan.autoname()
		self.assertEqual(plan.plan_code, "starter-2k")
		self.assertEqual(plan.name, "starter-2k")

	def test_plan_rejects_an_unavailable_delivery_limit(self) -> None:
		plan = frappe.get_doc(
			{
				"doctype": "HQ Send Plan",
				"plan_code": "invalid",
				"plan_name": "Invalid",
				"monthly_sends": 1234,
				"monthly_price": 0,
				"halo_subscription_name": "Invalid",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			plan.validate()
