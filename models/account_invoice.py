
# -*- coding: utf-8 -*-
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
#from openerp import models, fields, api
#from openerp.exceptions import UserError, ValidationError
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    sale_commission_id = fields.Many2one(
        'sales.commission',
        string='Sales Commission',
        states={'draft': [('readonly', False)]}
    )
    commission_manager_id = fields.Many2one(
        'sales.commission.line',
        string='Sales Commission for Manager'
    )
    commission_person_id = fields.Many2one(
        'sales.commission.line',
        string='Sales Commission for Member'
    )
    is_mart_commission = fields.Boolean('Is Mart Commission',default=False)
    mart_commission = fields.Float(string='Mart Commission')
    @api.model
    def get_categorywise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person = amount_manager = 0.0
        for order in self:
            for line in order.invoice_line_ids:
                commission_type = line.product_id.categ_id.commission_type
                sales_manager_commission = 0.0
                sales_person_commission = 0.0

                if commission_type:
                    if line.product_id.categ_id.commission_range_ids:
                        # sales_manager_commission = 0.0
                        # sales_person_commission = 0.0
                        
                        total = line.price_subtotal
                        if line.move_id.company_id.currency_id != line.move_id.currency_id:
                            amount = line.move_id.currency_id.compute(line.price_subtotal, line.move_id.company_id.currency_id)
                            total = amount
                        for range in line.product_id.categ_id.commission_range_ids:
                            for range in line.product_id.categ_id.commission_range_ids:
                                if total >= range.starting_range and total <=  range.ending_range:#2500 0 - 5000
                                    if commission_type == 'fix':
                                        sales_manager_commission = range.sales_manager_commission_amount
                                        sales_person_commission = range.sales_person_commission_amount
                                    else:
                                        sales_manager_commission = (line.price_subtotal * range.sales_manager_commission)/100
                                        sales_person_commission = (line.price_subtotal * range.sales_person_commission)/100

                        sum_line_manager.append(sales_manager_commission)
                        sum_line_person.append(sales_person_commission)                

            amount_manager = sum(sum_line_manager)
            amount_person = sum(sum_line_person)
        return amount_person, amount_manager
    
    def get_productwise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person = amount_manager = 0.0
        for order in self:
            for line in order.invoice_line_ids:
                commission_type = line.product_id.commission_type
                sales_manager_commission = 0.0
                sales_person_commission = 0.0

                if commission_type:
                    if line.product_id.commission_range_ids:
                        # sales_manager_commission = 0.0
                        # sales_person_commission = 0.0
                        
                        total = line.price_subtotal
                        if line.move_id.company_id.currency_id != line.move_id.currency_id:
                            amount = line.move_id.currency_id.compute(line.price_subtotal, line.move_id.company_id.currency_id)
                            total = amount

                        for range in line.product_id.commission_range_ids:
                            if total >= range.starting_range and total <=  range.ending_range:#2500 0 - 5000
                                if commission_type == 'fix':
                                    sales_manager_commission = range.sales_manager_commission_amount
                                    sales_person_commission = range.sales_person_commission_amount
                                else:
                                    sales_manager_commission = (line.price_subtotal * range.sales_manager_commission)/100
                                    sales_person_commission = (line.price_subtotal * range.sales_person_commission)/100

                    sum_line_manager.append(sales_manager_commission)
                    sum_line_person.append(sales_person_commission)                                

            amount_manager = sum(sum_line_manager)
            amount_person = sum(sum_line_person)
        return amount_person, amount_manager
    
    #@api.multi
    def get_teamwise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person = amount_manager = 0.0
        for order in self:
            commission_type = order.team_id.commission_type
            print(f'in account invoice - commission_type :{commission_type}')
            sales_manager_commission = 0.0
            sales_person_commission = 0.0

            if commission_type:
                if order.team_id.commission_range_ids:
                    # sales_manager_commission = 0.0
                    # sales_person_commission = 0.0

                    total = order.amount_untaxed
                    if order.company_id.currency_id != order.currency_id:
                        amount = order.currency_id.compute(order.amount_untaxed, order.company_id.currency_id)
                        total = amount
                    for range in order.team_id.commission_range_ids:
                        if total >= range.starting_range and total <=  range.ending_range:#2500 0 - 5000
                            if commission_type == 'fix':
                                sales_manager_commission = range.sales_manager_commission_amount
                                sales_person_commission = range.sales_person_commission_amount
                            elif commission_type == 'percentage':
                                sales_manager_commission = (order.amount_untaxed * range.sales_manager_commission)/100
                                sales_person_commission = (order.amount_untaxed * range.sales_person_commission)/100
                            elif commission_type == 'per_unit':
                                print(f'in account invoice - commission_type ------ equal  per_unit :{commission_type}')
                                sales_manager_commission = (order.amount_untaxed * range.sales_manager_commission) / 100
                                sales_person_commission = (order.amount_untaxed * range.sales_person_commission) / 100
                    amount_manager = sales_manager_commission
                    amount_person = sales_person_commission
        return amount_person, amount_manager

    def create_commission(self, amount, commission, type):
        commission_obj = self.env['sales.commission.line']
        product = self.env['product.product'].search([('is_commission_product','=',1)],limit=1)
        for invoice in self:
            date_invoice = invoice.invoice_date
            if not date_invoice:
                date_invoice = fields.Date.context_today(self)
            name_origin = ''
            if invoice.name:
                name_origin = invoice.name
            if invoice.invoice_origin:
                name_origin = name_origin + '-' +  invoice.invoice_origin
            
            if amount != 0.0:
                commission_value = {
                    'amount': amount,
                    'origin': name_origin,
                    'type':type,
                    'product_id': product.id,
                    'date' : date_invoice,
                    'src_invoice_id': invoice.id,
                    'sales_commission_id':commission.id,
                    'sales_team_id': invoice.team_id and invoice.team_id.id or False,
                    'company_id': invoice.company_id.id,
                    'currency_id': invoice.company_id.currency_id.id,
                }
                commission_id = commission_obj.create(commission_value)
                if type == 'sales_person':
                    invoice.commission_person_id = commission_id.id
                if type == 'sales_manager':
                    invoice.commission_manager_id = commission_id.id
        return True

    def create_base_commission(self, type):
        commission_obj = self.env['sales.commission']
        product = self.env['product.product'].search([('is_commission_product','=',1)],limit=1)
        for order in self:
            if type == 'sales_person':
                user = order.user_id.id
            if type == 'sales_manager':
                user = order.team_id.user_id.id
            first_day_tz, last_day_tz = self.env['sales.commission']._get_utc_start_end_date()

            commission_value = {
                    'start_date' : first_day_tz,
                    'end_date': last_day_tz,
                    'product_id':product.id,
                    'commission_user_id': user,
                    'company_id': order.company_id.id,
                    'currency_id': order.currency_id.id,
                }
            commission_id = commission_obj.create(commission_value)
        return commission_id

    def action_post(self):
        res = super(AccountInvoice, self).action_post()
        when_to_pay = self.env.company.when_to_pay
        if  when_to_pay == 'invoice_validate':
            for invoice in self:
                commission_based_on = invoice.company_id.commission_based_on if invoice.company_id else self.env.company.commission_based_on
                if invoice.move_type == 'out_invoice':
                    if commission_based_on == 'sales_team':
                        amount_person, amount_manager = invoice.get_teamwise_commission()
                    elif commission_based_on == 'product_category':
                        amount_person, amount_manager = invoice.get_categorywise_commission()
                    elif commission_based_on == 'product_template':
                        amount_person, amount_manager = invoice.get_productwise_commission()

                    date_invoice = invoice.invoice_date
                    if not date_invoice:
                        date_invoice = fields.Date.context_today(self)
                
                    commission = self.env['sales.commission'].search([
                        ('commission_user_id', '=', invoice.user_id.id),
                        ('start_date', '<=', date_invoice),
                        ('end_date', '>=', date_invoice),
                        ('state','=','draft'),
                        ('company_id', '=', invoice.company_id.id),
                        ],limit=1)

                    if not commission:
                        commission = invoice.create_base_commission(type='sales_person')
                    invoice.create_commission(amount_person, commission, type='sales_person')
                    
                    if not invoice.user_id.id == invoice.team_id.user_id.id and invoice.team_id.user_id:
                        commission = self.env['sales.commission'].search([
                            ('commission_user_id', '=', invoice.team_id.user_id.id),
                            ('start_date', '<=', date_invoice),
                            ('end_date', '>=', date_invoice),
                            ('state','=','draft'),
                            ('company_id', '=', invoice.company_id.id),
                            ],limit=1)
                        if not commission:
                            commission = invoice.create_base_commission(type='sales_manager')
                        invoice.create_commission(amount_manager,commission, type='sales_manager')
        return res

    def button_cancel(self):
        res = super(AccountInvoice, self).button_cancel()
        for rec in self:
            if rec.commission_manager_id:
                rec.commission_manager_id.state = 'exception'
            if rec.commission_person_id:
                rec.commission_person_id.state = 'exception'
        return res

