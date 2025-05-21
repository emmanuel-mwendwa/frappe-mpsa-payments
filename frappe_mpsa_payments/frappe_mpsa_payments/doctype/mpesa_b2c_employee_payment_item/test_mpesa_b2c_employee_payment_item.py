# Copyright (c) 2024, Navari Limited and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class MPesaB2CEmployeePaymentItem(FrappeTestCase):
    def test_validate(self):
        """Test the validate method of MPesaB2CEmployeePaymentItem"""
        # Create a new instance of the document
        doc = frappe.get_doc(
            {
                "doctype": "MPesa B2C Employee Payment Item",
                "partyb": "+254712345678",
                "amount": 100,
                "record_amount": 200,
            }
        )

        # Call the validate method
        doc.validate()

        # Check if the partyb field is correctly formatted
        self.assertEqual(doc.partyb, "254712345678")
