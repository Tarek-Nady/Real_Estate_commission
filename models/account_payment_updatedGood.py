# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    @api.depends('partner_type')
    def _check_partner_type(self):
        for rec in self:
            rec.sales_commission_apply = False
            if rec.partner_type == 'customer':
                rec.sales_commission_apply = True

    @api.model
    def get_team(self):
        if self._context.get('active_model') and self._context.get('active_model')  == 'account.move':
            invoice = self._context.get('active_id', False)
            if invoice:
                inv = self.env['account.move'].browse(invoice)
                return inv.team_id.id
        return False


    @api.model
    def get_team_person(self):
        if self._context.get('active_model') and self._context.get('active_model')  == 'account.move':
            invoice = self._context.get('active_id', False)
            if invoice:
                inv = self.env['account.move'].browse(invoice)
                return inv.user_id.id
        return False
        
    sales_team_id = fields.Many2one(
        'crm.team',
        string='Sales Team',
        default=get_team,
    )
    sales_user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=get_team_person,
    )

    commission_manager_id = fields.Many2one(
        'sales.commission.line',
        string='Sales Commission for Manager'
    )
    commission_person_id = fields.Many2one(
        'sales.commission.line',
        string='Sales Commission for Member'
    )
    commission_broker_id = fields.Many2one(
        'sales.commission.line',
        string='Sales Commission for Broker'
    )
    commission_third_party_id = fields.Many2one(
        'sales.commission.line',
        string='Sales Commission for Third Party'
    )

    sales_commission_apply = fields.Boolean(
        string='Sales Commission Apply',
        compute='_check_partner_type',
        store=True,
    )
    def make_salesperson_commission(self,payment):
        commission = self.env['sales.commission'].search([
            ('commission_user_id', '=', payment.sales_user_id.id),
            ('start_date', '<', payment.date),
            ('end_date', '>', payment.date),
            ('state', '=', 'draft'),
            ('company_id', '=', payment.company_id.id),
        ], limit=1)
        sales_person_commission = 0.0
        if not commission:
            commission = payment.create_base_commission(type='sales_person')
        sales_ownership_contracts = self.env['ownership.contract'].search(
            [('user_id', '=', payment.sales_user_id.id), ('state', '=', 'confirmed')])
        sales_ownership_contracts_filtered_contract = sales_ownership_contracts.loan_line. \
            filtered(lambda line: line.name == 'Down Payment' and line.payment_state == 'paid')
        sales_ownership_contracts_filtered_cc = sales_ownership_contracts_filtered_contract.mapped('invoice_id').mapped(
            'date')
        sales_ownership_contracts_filtered_dd = sales_ownership_contracts_filtered_contract.mapped(
            'invoice_id').filtered(lambda
                                       invoice: invoice.date >= commission.start_date.date() and invoice.date <= commission.end_date.date()).mapped(
            'ownership_line_id').mapped('loan_id')

        ownership_contracts = sales_ownership_contracts_filtered_dd.ids
        if payment.ownership_line_id.name=='Down Payment':
            ownership_contracts.append(payment.ownership_line_id.loan_id.id)
        self.env.cr.commit()
        commission.write({
            'ownership_contracts': [(6, 0, ownership_contracts)],
        })
        self.env.cr.commit()
        # ------- check units anf get amount for sales person in owner contacts for this person ==
        # salesman_contracts = self.env['ownership.contract'].search([('user_id','=',payment.sales_user_id.id),('is_sales_commission_taken','=',False)])
        sales_contracts_count = len(commission.ownership_contracts)
        total_amount_units_sales_person = sum([contract.pricing for contract in commission.ownership_contracts])

        commission_type = payment.sales_team_id.commission_type
        if payment.sales_team_id.commission_range_ids:
            for range in payment.sales_team_id.commission_range_ids:
                if commission_type == 'per_unit':
                    if sales_contracts_count >= range.starting_range and sales_contracts_count <= range.ending_range:
                        sales_person_commission = total_amount_units_sales_person * (
                            range.sales_person_commission) / 100
                        if commission.sales_commission_line:
                            commission.sales_commission_line = [(5, 0, 0)]
                        self.env.cr.commit()
                        payment.create_commission(sales_person_commission, commission, type='sales_person')
                        self.env.cr.commit()

    def make_salesmanager_commission(self,payment):
        print(f'in make make_salesmanager_commission commission:{payment}')
        commission = self.env['sales.commission'].search([
            ('commission_user_id', '=', payment.sales_team_id.user_id.id),
            ('start_date', '<', payment.date),
            ('end_date', '>', payment.date),
            ('state', '=', 'draft'),
            ('company_id', '=', payment.company_id.id),
        ], limit=1)
        sales_person_commission = 0.0
        if not commission:
            commission = payment.create_base_commission(type='sales_manager')
        sales_ownership_contracts = self.env['ownership.contract'].search(
            [('user_id', '=', payment.sales_user_id.id), ('state', '=', 'confirmed')])
        sales_ownership_contracts_filtered_contract = sales_ownership_contracts.loan_line. \
            filtered(lambda line: line.name == 'Down Payment' and line.payment_state == 'paid')
        sales_ownership_contracts_filtered_cc = sales_ownership_contracts_filtered_contract.mapped('invoice_id').mapped(
            'date')
        sales_ownership_contracts_filtered_dd = sales_ownership_contracts_filtered_contract.mapped(
            'invoice_id').filtered(lambda
                                       invoice: invoice.date >= commission.start_date.date() and invoice.date <= commission.end_date.date()).mapped(
            'ownership_line_id').mapped('loan_id')

        ownership_contracts = sales_ownership_contracts_filtered_dd.ids
        if payment.ownership_line_id.name=='Down Payment':
            ownership_contracts.append(payment.ownership_line_id.loan_id.id)

        self.env.cr.commit()
        commission.write({
            'ownership_contracts': [(6, 0, ownership_contracts)],
        })
        self.env.cr.commit()
        # ------- check units anf get amount for sales person in owner contacts for this person ==
        # salesman_contracts = self.env['ownership.contract'].search([('user_id','=',payment.sales_user_id.id),('is_sales_commission_taken','=',False)])
        sales_contracts_count = len(commission.ownership_contracts)
        print(f'sales_contracts_count :{sales_contracts_count}')
        print(f'sales_contracts_ids :{commission.ownership_contracts.ids}')
        total_amount_units_sales_manager = sum([contract.pricing for contract in commission.ownership_contracts])

        commission_type = payment.sales_team_id.commission_type
        if payment.sales_team_id.commission_range_ids:
            for range in payment.sales_team_id.commission_range_ids:
                if commission_type == 'per_unit':
                    if sales_contracts_count >= range.starting_range and sales_contracts_count <= range.ending_range:
                        sales_manager_commission = total_amount_units_sales_manager * (
                            range.sales_manager_commission) / 100
                        if commission.sales_commission_line:
                            commission.sales_commission_line = [(5, 0, 0)]
                        self.env.cr.commit()
                        payment.create_commission(sales_manager_commission, commission, type='sales_manager')
                        self.env.cr.commit()
    def get_teamwise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person, amount_manager = 0.0, 0.0
        amount_broker, amount_third_party = 0.0, 0.0
        for payment in self:
            if not self._context.get('active_ids') and not payment.sales_team_id:
                raise UserError(_('Please select Sales Team.'))
            if not self._context.get('active_ids') and not payment.sales_user_id:
                raise UserError(_('Please select Sales User.'))
            active_model = self._context.get('active_model')
            if self._context.get('active_ids') and not payment.sales_team_id:
                invoice_ids = self._context.get('active_ids')
                invoice_ids = self.env[active_model].sudo().browse(invoice_ids)
                payment.sales_team_id = invoice_ids[0].team_id.id
            if self._context.get('active_ids') and not payment.sales_user_id:
                invoice_ids = self._context.get('active_ids')
                invoice_ids = self.env[active_model].sudo().browse(invoice_ids)
                payment.sales_user_id = invoice_ids[0].user_id.id
            if True:
                commission_type = payment.sales_team_id.commission_type
                sales_manager_commission=0
                sales_person_commission=0
                sales_broker_commission=0
                sales_party_commission=0
                if commission_type:
                    if payment.sales_team_id.commission_range_ids:
                        total = payment.amount
                        if payment.company_id.currency_id != payment.currency_id:
                            amount = payment.currency_id.compute(payment.amount, payment.company_id.currency_id)
                            total = amount
                        # for range in payment.sales_team_id.commission_range_ids:
                        #     if total >= range.starting_range and total <= range.ending_range:
                        #         if commission_type == 'fix':
                        #             sales_manager_commission = range.sales_manager_commission_amount
                        #             sales_person_commission = range.sales_person_commission_amount
                        #         elif commission_type == 'percentage':
                        #             sales_manager_commission = (
                        #                                                    payment.amount * range.sales_manager_commission) / 100
                        #             sales_person_commission = (payment.amount * range.sales_person_commission) / 100
                        #         elif commission_type == 'per_unit':
                        #             print(
                        #                 f'in after payment after action post kkkkk - commission_type :{commission_type}')
                        #             sales_manager_commission = 10
                        #             sales_person_commission = 10
                        for range in payment.sales_team_id.commission_range_ids:
                            if commission_type == 'per_unit':
                                print(f'in after payment after action post kkkkk - commission_type :{commission_type}')
                                # sales_manager_commission =  (payment.amount * range.sales_manager_commission)/100
                                # sales_person_commission =  (payment.amount * range.sales_person_commission)/100
                                #
                                sales_manager_commission = (range.sales_manager_commission) / 100
                                sales_person_commission = (range.sales_person_commission)/ 100


                                # sales_broker_commission = (range.broker_commission)/100
                                # sales_party_commission = (range.third_party_commission)/100
                                sales_broker_commission = (range.broker_commission)/100
                                sales_party_commission = (range.third_party_commission)/100
                                print(f'in commission_type -per_unit -sales_broker_commission:{sales_broker_commission} -sales_party_commission :{sales_party_commission}  ')


                            else:
                                if total >= range.starting_range and total <=  range.ending_range:
                                    if commission_type == 'fix':
                                        sales_manager_commission = range.sales_manager_commission_amount
                                        sales_person_commission = range.sales_person_commission_amount
                                    elif commission_type == 'percentage':
                                        sales_manager_commission = (payment.amount * range.sales_manager_commission)/100
                                        sales_person_commission = (payment.amount * range.sales_person_commission)/100

                                    # elif commission_type == 'per_unit':
                                    #     print(f'in after payment after action post kkkkk - commission_type :{commission_type}')
                                    #     sales_manager_commission = 10
                                    #     sales_person_commission =10

                        amount_manager = sales_manager_commission
                        amount_person = sales_person_commission
                        broker_commission = sales_broker_commission
                        third_party_commission = sales_party_commission
        return amount_person, amount_manager,broker_commission,third_party_commission

    def create_commission(self, amount, commission, type):
        print(f'in create_commission - amount:{amount} - commission:{commission} - type:{type}')
        commission_obj = self.env['sales.commission.line']
        product = self.env['product.product'].search([('is_commission_product','=',1)],limit=1)
        for payment in self:
            if amount != 0.0:
                commission_value = {
                    'sales_team_id': payment.sales_team_id.id,
                    'amount': amount,
                    'origin': payment.name,
                    'type':type,
                    'product_id': product.id,
                    'date' : payment.date,
                    'src_payment_id': payment.id,
                    'sales_commission_id':commission.id,
                    'company_id': payment.company_id.id,
                    'currency_id': payment.company_id.currency_id.id,
                }
                commission_id = commission_obj.create(commission_value)
                if type == 'sales_person':
                    payment.commission_person_id = commission_id.id
                if type == 'sales_manager':
                    payment.commission_manager_id = commission_id.id
                if type == 'sales_broker':
                    payment.commission_broker_id = commission_id.id
                if type == 'sales_third_party':
                    payment.commission_third_party_id = commission_id.id
        return True
    
    def create_base_commission(self, type):
        commission_obj = self.env['sales.commission']
        product = self.env['product.product'].search([('is_commission_product','=',1)],limit=1)
        for order in self:
            if type == 'sales_person':
                user = order.sales_user_id.id
            if type == 'sales_manager':
                user = order.sales_team_id.user_id.id
            if type == 'sales_broker':
                user = order.broker_id.id
            if type == 'sales_third_party':
                user = order.third_party_id.id

            first_day_tz, last_day_tz = self.env['sales.commission']._get_utc_start_end_date()
            print(f'in create_base_commission -order.ownership_line_id.loan_id.id :{order.ownership_line_id.loan_id.id} ')
            commission_value = {
                    'start_date' : first_day_tz,
                    'end_date': last_day_tz,
                    'product_id':product.id,
                    'commission_user_id': user,
                    'company_id': order.company_id.id,
                    'currency_id': order.currency_id.id,
                    # 'ownership_contracts': [(4,order.ownership_line_id.loan_id.id)]
                    'ownership_contracts': (4,order.ownership_line_id.loan_id.id)
                # [(4, ref('sales_team.group_sale_manager'))]
                }
            if type=='sales_broker':
                commission_value.update({'broker_id':user})
            elif type=='sales_third_party':
                commission_value.update({'third_party_id': user})

            commission_id = commission_obj.create(commission_value)
        return commission_id

    # def action_post(self):
    #     res = super(AccountPayment, self).action_post()
    #     when_to_pay = self.env.company.when_to_pay
    #     if when_to_pay == 'invoice_payment':
    #         for payment in self:
    #             if payment.sales_commission_apply:
    #                 commission_based_on = payment.company_id.commission_based_on if payment.company_id else self.env.company.commission_based_on
    #                 amount_person, amount_manager = 0.0, 0.0
    #                 amount_broker, amount_third_party = 0.0, 0.0
    #                 if commission_based_on == 'sales_team':
    #                     print(f'in invoice_payment an account payment commission - sales_team')
    #                     amount_person, amount_manager, broker_commission, third_party_commission = payment.get_teamwise_commission()
    #                     print(
    #                         f'in invoice_payment an account payment commission - sales_team -amount_person: {amount_person} - amount_manager:{amount_manager} - broker_commission :{broker_commission} - third_party_commission:{third_party_commission} ')
    #
    #                 commission = self.env['sales.commission'].search([
    #                     ('commission_user_id', '=', payment.sales_user_id.id),
    #                     ('start_date', '<', payment.date),
    #                     ('end_date', '>', payment.date),
    #                     ('state', '=', 'draft'),
    #                     ('company_id', '=', payment.company_id.id),
    #                 ], limit=1)
    #                 if not commission:
    #                     commission = payment.create_base_commission(type='sales_person')
    #                 payment.create_commission(amount_person, commission, type='sales_person')
    #
    #                 if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
    #                     commission = self.env['sales.commission'].search([
    #                         ('commission_user_id', '=', payment.sales_team_id.user_id.id),
    #                         ('start_date', '<', payment.date),
    #                         ('end_date', '>', payment.date),
    #                         ('state', '=', 'draft'),
    #                         ('company_id', '=', payment.company_id.id),
    #                     ], limit=1)
    #                     if not commission:
    #                         commission = payment.create_base_commission(type='sales_manager')
    #                     payment.create_commission(amount_manager, commission, type='sales_manager')
    #
    #                 # --------- create broker commission====
    #                 # if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
    #                 if payment.ownership_line_id.id and payment.broker_id:
    #                     commission = self.env['sales.commission'].search([
    #                         ('broker_id', '=', payment.broker_id.id),
    #                         ('start_date', '<', payment.date),
    #                         ('end_date', '>', payment.date),
    #                         ('state', '=', 'draft'),
    #                         ('company_id', '=', payment.company_id.id),
    #                     ], limit=1)
    #                     if not commission:
    #                         commission = payment.create_base_commission(type='sales_broker')
    #                     payment.create_commission(amount_broker, commission, type='sales_broker')
    #
    #                 # --------- create third party commission====
    #                 # if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
    #                 if payment.ownership_line_id.id and payment.third_party_id:
    #                     commission = self.env['sales.commission'].search([
    #                         ('third_party_id', '=', payment.third_party_id.id),
    #                         ('start_date', '<', payment.date),
    #                         ('end_date', '>', payment.date),
    #                         ('state', '=', 'draft'),
    #                         ('company_id', '=', payment.company_id.id),
    #                     ], limit=1)
    #                     if not commission:
    #                         commission = payment.create_base_commission(type='sales_third_party')
    #                     payment.create_commission(amount_third_party, commission, type='sales_third_party')
    #     return res
    def action_post(self):
        res = super(AccountPayment, self).action_post()
        when_to_pay = self.env.company.when_to_pay
        if when_to_pay == 'invoice_payment':
            for payment in self:
                if payment.sales_commission_apply:
                    commission_based_on = payment.company_id.commission_based_on if payment.company_id else self.env.company.commission_based_on
                    amount_person, amount_manager = 0.0, 0.0
                    amount_broker, amount_third_party = 0.0, 0.0
                    if commission_based_on == 'sales_team':
                        print(f'in invoice_payment an account payment commission - sales_team')
                        # amount_person, amount_manager, broker_commission, third_party_commission = payment.get_teamwise_commission()
                        # print(
                        #     f'in invoice_payment an account payment commission - sales_team -amount_person: {amount_person} - amount_manager:{amount_manager} - broker_commission :{broker_commission} - third_party_commission:{third_party_commission} ')
                        #
                        payment.make_salesperson_commission(payment)
                        payment.make_salesmanager_commission(payment)
                        # commission = self.env['sales.commission'].search([
                        #     ('commission_user_id', '=', payment.sales_user_id.id),
                        #     ('start_date', '<', payment.date),
                        #     ('end_date', '>', payment.date),
                        #     ('state', '=', 'draft'),
                        #     ('company_id', '=', payment.company_id.id),
                        # ], limit=1)
                        # sales_person_commission = 0.0
                        # if not commission:
                        #     commission = payment.create_base_commission(type='sales_person')
                        # sales_ownership_contracts =[]
                        # sales_ownership_contracts = self.env['ownership.contract'].search([('user_id','=',payment.sales_user_id.id),('state','=','confirmed')])
                        # print(f'sales_ownership_contracts :contract{sales_ownership_contracts}')
                        # sales_ownership_contracts_filtered_contract = sales_ownership_contracts.loan_line.\
                        #     filtered(lambda line: line.name =='Down Payment' and line.payment_state=='paid')
                        # sales_ownership_contracts_filtered_cc= sales_ownership_contracts_filtered_contract.mapped('invoice_id').mapped('date')
                        # print(f'sales_ownership_contracts_filtered_cc :{sales_ownership_contracts_filtered_cc}')
                        # sales_ownership_contracts_filtered_dd= sales_ownership_contracts_filtered_contract.mapped('invoice_id').filtered(lambda invoice: invoice.date >=commission.start_date.date() and invoice.date <=commission.end_date.date()).mapped('ownership_line_id').mapped('loan_id')
                        # print(f'sales_ownership_contracts_filtered_dd :{sales_ownership_contracts_filtered_dd}')
                        # print(f'sales_ownership_contracts_filtered_dd idssss :{sales_ownership_contracts_filtered_dd.ids}')
                        #
                        # ownership_contracts = sales_ownership_contracts_filtered_dd.ids
                        # print(f'ownership_contracts afterrrr update :{ownership_contracts}')
                        # self.env.cr.commit()
                        # commission.write({
                        #     'ownership_contracts':[(6, 0, ownership_contracts)],
                        # })
                        # self.env.cr.commit()
                        #         # ------- check units anf get amount for sales person in owner contacts for this person ==
                        #         # salesman_contracts = self.env['ownership.contract'].search([('user_id','=',payment.sales_user_id.id),('is_sales_commission_taken','=',False)])
                        # sales_contracts_count = len(commission.ownership_contracts)
                        # print(f'sales_contracts_count :{sales_contracts_count}')
                        # print(f'sales_contracts_ids :{commission.ownership_contracts.ids}')
                        # total_amount_units_sales_person = sum([contract.pricing for contract in commission.ownership_contracts])
                        # print(f'total_amount_units_sales_person :{total_amount_units_sales_person}')
                        #
                        # commission_type = payment.sales_team_id.commission_type
                        # if payment.sales_team_id.commission_range_ids:
                        #     for range in payment.sales_team_id.commission_range_ids:
                        #         if commission_type == 'per_unit':
                        #             if sales_contracts_count >= range.starting_range and sales_contracts_count <= range.ending_range:
                        #                 print(f'condition range accepted')
                        #                 sales_person_commission = total_amount_units_sales_person*(range.sales_person_commission)/ 100
                        #                 print(f'condition range accepted - sales_person_commission :{sales_person_commission}')
                        #                 if commission.sales_commission_line:
                        #                     commission.sales_commission_line = [(5, 0, 0)]
                        #                 print(
                        #                     f'condition range accepted afffff- sales_person_commission before create :{sales_person_commission}')
                        #                 self.env.cr.commit()
                        #                 payment.create_commission(sales_person_commission, commission, type='sales_person')
                        #                 self.env.cr.commit()



                    # if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
                    #     commission = self.env['sales.commission'].search([
                    #         ('commission_user_id', '=', payment.sales_team_id.user_id.id),
                    #         ('start_date', '<', payment.date),
                    #         ('end_date', '>', payment.date),
                    #         ('state', '=', 'draft'),
                    #         ('company_id', '=', payment.company_id.id),
                    #     ], limit=1)
                    #     if not commission:
                    #         commission = payment.create_base_commission(type='sales_manager')
                    #     payment.create_commission(amount_manager, commission, type='sales_manager')

                    # --------- create broker commission====
                    # if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
                    # if payment.ownership_line_id.id and payment.broker_id:
                    #     commission = self.env['sales.commission'].search([
                    #         ('broker_id', '=', payment.broker_id.id),
                    #         ('start_date', '<', payment.date),
                    #         ('end_date', '>', payment.date),
                    #         ('state', '=', 'draft'),
                    #         ('company_id', '=', payment.company_id.id),
                    #     ], limit=1)
                    #     if not commission:
                    #         commission = payment.create_base_commission(type='sales_broker')
                    #     payment.create_commission(amount_broker, commission, type='sales_broker')

                    # --------- create third party commission====
                    # if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
                    # if payment.ownership_line_id.id and payment.third_party_id:
                    #     commission = self.env['sales.commission'].search([
                    #         ('third_party_id', '=', payment.third_party_id.id),
                    #         ('start_date', '<', payment.date),
                    #         ('end_date', '>', payment.date),
                    #         ('state', '=', 'draft'),
                    #         ('company_id', '=', payment.company_id.id),
                    #     ], limit=1)
                    #     if not commission:
                    #         commission = payment.create_base_commission(type='sales_third_party')
                    #     payment.create_commission(amount_third_party, commission, type='sales_third_party')
        return res
    def action_cancel(self):
        res = super(AccountPayment, self).action_cancel()
        for rec in self:
            if rec.commission_manager_id:
                rec.commission_manager_id.state = 'exception'
            if rec.commission_person_id:
                rec.commission_person_id.state = 'exception'
            if rec.commission_broker_id:
                rec.commission_broker_id.state = 'exception'
            if rec.commission_third_party_id:
                rec.commission_third_party_id.state = 'exception'
        return res
