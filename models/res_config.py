# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    commission_based_on = fields.Selection(
        string="Calculation Based On",
        related="company_id.commission_based_on",
        readonly=False,
    )
    when_to_pay = fields.Selection([
        ('invoice_validate', 'Invoice Validate'),
        ('invoice_payment', 'Customer Payment')], 
        string="When To Pay",
        related="company_id.when_to_pay",
        readonly=False,
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param("sales_commission_target_fix_percentage.when_to_pay", self.when_to_pay)
        if self.when_to_pay == 'invoice_payment':
            if self.commission_based_on == 'product_category' or self.commission_based_on == 'product_template':
                raise UserError(_("Sales Commission: You can not have commision based on product or category if you have selected when to pay is payment."))
        ICPSudo.set_param("sales_commission_target_fix_percentage.commission_based_on", self.commission_based_on)
