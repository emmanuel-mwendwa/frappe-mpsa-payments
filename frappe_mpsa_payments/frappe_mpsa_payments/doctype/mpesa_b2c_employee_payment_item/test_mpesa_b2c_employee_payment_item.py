# Copyright (c) 2024, Navari Limited and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class MPesaB2CEmployeePaymentItem(FrappeTestCase):
    def test_validate_fails_if_amount_is_less_than_10(self):
        """Test that the validate method raises a ValidationError if the amount is less than 10"""
        doc = frappe.get_doc(
            {
                "doctype": "MPesa B2C Employee Payment Item",
                "amount": 5,
                "record_amount": 100,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_validate_fails_if_amount_is_greater_than_record_amount(self):
        """Test that the validate method raises a ValidationError if the amount is greater than record_amount"""
        doc = frappe.get_doc(
            {
                "doctype": "MPesa B2C Employee Payment Item",
                "amount": 200,
                "record_amount": 100,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            doc.validate()
    
    def test_validate_fails_if_partyb_is_invalid(self):
        """Test that the validate method raises a ValidationError if partyb is invalid"""
        doc = frappe.get_doc(
            {
                "doctype": "MPesa B2C Employee Payment Item",
                "partyb": "some_invalid_number",
            }
        )
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_validate_passes_if_partyb_is_valid(self):
        """Test that the validate method does not raise a ValidationError if partyb is valid"""
        doc = frappe.get_doc(
            {
                "doctype": "MPesa B2C Employee Payment Item",
                "partyb": "+254712345678",
            }
        )
        try:
            doc.validate()
        except frappe.ValidationError:
            self.fail("validate() raised ValidationError unexpectedly!")

