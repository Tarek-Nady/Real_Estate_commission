
from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    x_mart_commission = fields.Float(string='Ownership Mart Commission')
    x_rental_mart_commission = fields.Float(string='Rental Mart Commission')
