# -*- coding: utf-8 -*-
#from openerp import models, fields, api
from odoo import models, fields, api

    
class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.depends()
    def _compute_is_apply(self):
        commission_based_on = self.env.company.commission_based_on
        for rec in self:
            rec.is_apply = False
            if commission_based_on == 'product_category':
                rec.is_apply = True

    commission_type = fields.Selection(
        string="Commission Amount Type",
        selection=[
            ('percentage', 'By Percentage'),
            ('fix', 'Fixed Amount'),
            ('per_unit', 'Per Unit'),
        ],
    )
    is_apply = fields.Boolean(
        string='Is Apply ?',
        compute='_compute_is_apply'
    )
    commission_range_ids = fields.One2many(
        'sales.commission.range',
        'commission_category_id',
         string='Sales Commission Range Category',
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
