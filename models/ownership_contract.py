from odoo import api, fields, models


class OwnershipContract(models.Model):
    _inherit = "ownership.contract"

    sale_commission_id=fields.Many2one('sales.commission',string='Sale Commission')
