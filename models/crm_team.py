# -*- coding: utf-8 -*-
#from openerp import models, fields, api
from odoo import models, fields, api


class Team(models.Model):
    _inherit = 'crm.team'

    @api.depends()
    def _compute_is_apply(self):
        for rec in self:
            commission_based_on = rec.company_id.commission_based_on if rec.company_id else self.env.company.commission_based_on
            rec.is_apply = False
            if commission_based_on == 'sales_team':
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
        'commission_team_id',
         string='Sales Commission Range',
    )

    #  ========= Per Unit Broker and Third Party Percentage ====
    # -------------------------------

    broker_commission = fields.Float(
        'Broker Commission(%)',
        required=True
    )
    third_party_commission = fields.Float(
        'Third Party Commission(%)',
        required=True
    )

    is_broker_third_party_commission = fields.Boolean(
        string='Is Broker Third Party Commission ?',
        default=False
    )
