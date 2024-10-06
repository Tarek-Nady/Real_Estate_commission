# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
        if self._context.get('active_model') and self._context.get('active_model') == 'account.move':
            invoice = self._context.get('active_id', False)
            if invoice:
                inv = self.env['account.move'].browse(invoice)
                return inv.team_id.id
        return False

    @api.model
    def get_team_person(self):
        if self._context.get('active_model') and self._context.get('active_model') == 'account.move':
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
        string='Sales Commission Apply', default=True
    )

    def make_broker_commission(self, payment):
        ownership_contracts = []
        if payment.ownership_line_id.name == 'Down Payment':
            ownership_contracts.append(payment.ownership_line_id.loan_id.id)
            commission_brokers = self.env['sales.commission'].search([
                ('broker_id', '=', payment.broker_id.id),
                ('state', '=', 'draft'),
                ('company_id', '=', payment.company_id.id),

            ], )
            commission = commission_brokers.filtered(lambda
                                                         c: payment.ownership_line_id.loan_id.id in c.ownership_contracts.ids and not c.commission_user_id)
            sales_person_commission = 0.0
            if not commission:
                commission = payment.create_base_commission(type='sales_broker', payment_date=payment.date)
            self.env.cr.commit()
            commission.write({
                'ownership_contracts': [(6, 0, ownership_contracts)],
            })
            self.env.cr.commit()
            sales_contracts_count = len(commission.ownership_contracts)
            total_amount_units_broker_person = sum([contract.pricing for contract in commission.ownership_contracts])

            commission_type = payment.sales_team_id.commission_type
            if payment.sales_team_id.broker_commission and commission_type == 'per_unit':
                broker_commission = total_amount_units_broker_person * (
                    payment.sales_team_id.broker_commission) / 100
                if commission.sales_commission_line:
                    commission.sales_commission_line = [(5, 0, 0)]
                self.env.cr.commit()
                payment.sudo().create_commission(broker_commission, commission, type='sales_broker',
                                                 ownership_contract_id=payment.ownership_line_id.loan_id.id,
                                                 commission_percentage=payment.sales_team_id.broker_commission)
                self.env.cr.commit()

    def make_third_party_commission(self, payment):
        ownership_contracts = []
        if payment.ownership_line_id.name == 'Down Payment':
            ownership_contracts.append(payment.ownership_line_id.loan_id.id)
            commission_third_party = self.env['sales.commission'].search([
                ('third_party_id', '=', payment.third_party_id.id),
                ('state', '=', 'draft'),
                ('company_id', '=', payment.company_id.id),

            ], )
            commission = commission_third_party.filtered(lambda
                                                             c: payment.ownership_line_id.loan_id.id in c.ownership_contracts.ids and not c.commission_user_id)
            sales_person_commission = 0.0
            if not commission:
                commission = payment.create_base_commission(type='sales_third_party', payment_date=payment.date)

            self.env.cr.commit()
            commission.write({
                'ownership_contracts': [(6, 0, ownership_contracts)],
            })
            self.env.cr.commit()
            # ------- check units anf get amount for sales person in owner contacts for this person ==
            # salesman_contracts = self.env['ownership.contract'].search([('user_id','=',payment.sales_user_id.id),('is_sales_commission_taken','=',False)])
            sales_contracts_count = len(commission.ownership_contracts)
            total_amount_units_third_party_person = sum(
                [contract.pricing for contract in commission.ownership_contracts])

            commission_type = payment.sales_team_id.commission_type
            if payment.sales_team_id.third_party_commission and commission_type == 'per_unit':
                third_party_commission = total_amount_units_third_party_person * (
                    payment.sales_team_id.third_party_commission) / 100
                if commission.sales_commission_line:
                    commission.sales_commission_line = [(5, 0, 0)]
                self.env.cr.commit()
                payment.sudo().create_commission(third_party_commission, commission, type='sales_third_party',
                                                 ownership_contract_id=payment.ownership_line_id.loan_id.id,
                                                 commission_percentage=payment.sales_team_id.third_party_commission)
                self.env.cr.commit()

    def make_salesperson_commission(self, payment):
        commission = self.env['sales.commission'].search([
            ('commission_user_id', '=', payment.sales_user_id.id),
            ('start_date', '<=', payment.date),
            ('end_date', '>=', payment.date),
            ('state', '=', 'draft'),
            ('company_id', '=', payment.company_id.id),
        ], limit=1)
        sales_person_commission = 0.0
        if not commission:
            commission = payment.create_base_commission(type='sales_person')
        sales_ownership_contracts = self.env['ownership.contract'].search(
            [('user_id', '=', payment.sales_user_id.id), ('state', '=', 'confirmed')])
        sales_ownership_contracts_filtered_contract = sales_ownership_contracts.loan_line. \
            filtered(lambda
                         line: line.name == 'Down Payment' and line.payment_state == 'paid' or line.payment_state == 'in_payment')
        sales_ownership_contracts_filtered_cc = sales_ownership_contracts_filtered_contract.mapped('invoice_id').mapped(
            'date')
        sales_ownership_contracts_filtered_dd = sales_ownership_contracts_filtered_contract.mapped(
            'invoice_id').filtered(lambda
                                       invoice: invoice.date >= commission.start_date.date() and invoice.date <= commission.end_date.date()).mapped(
            'ownership_line_id').mapped('loan_id')

        ownership_contracts = sales_ownership_contracts_filtered_dd.ids
        if payment.ownership_line_id.name == 'Down Payment':
            ownership_contracts.append(payment.ownership_line_id.loan_id.id)
        self.env.cr.commit()
        commission.write({
            'ownership_contracts': [(6, 0, ownership_contracts)],
        })
        self.env.cr.commit()
        sales_contracts_count = len(commission.ownership_contracts)

        if commission.sales_commission_line:
            commission.sales_commission_line = [(5, 0, 0)]
        # ========= New Commission Calc ==========
        commission_type = payment.sales_team_id.commission_type
        if payment.sales_team_id.commission_range_ids:
            for range in payment.sales_team_id.commission_range_ids:
                ownership_contracts_orders = self.env['ownership.contract'].search(
                    [('id', 'in', commission.ownership_contracts.ids)], limit=range.ending_range, )
                if ownership_contracts_orders:
                    ownership_contracts_orders = ownership_contracts_orders.sorted(lambda c: c.create_date)

                if commission_type == 'per_unit':
                    if sales_contracts_count >= range.ending_range:
                        for contract in ownership_contracts_orders:
                            total_amount_units_sales_person = contract.pricing
                            sales_person_commission = total_amount_units_sales_person * (
                                range.sales_person_commission) / 100
                            self.env.cr.commit()
                            if contract.id not in commission.sales_commission_line.ownership_contract_id.ids:
                                payment.create_commission(sales_person_commission, commission, type='sales_person',
                                                          ownership_contract_id=contract.id,
                                                          commission_percentage=range.sales_person_commission)
                            self.env.cr.commit()

                    elif sales_contracts_count >= range.starting_range and sales_contracts_count <= range.ending_range:
                        for contract in commission.ownership_contracts:
                            total_amount_units_sales_person = contract.pricing
                            sales_person_commission = total_amount_units_sales_person * (
                                range.sales_person_commission) / 100

                            self.env.cr.commit()
                            if contract.id not in commission.sales_commission_line.ownership_contract_id.ids:
                                payment.create_commission(sales_person_commission, commission, type='sales_person',
                                                          ownership_contract_id=contract.id,
                                                          commission_percentage=range.sales_person_commission)
                            self.env.cr.commit()

        # ========= End New Commission Calc =======

    def make_unit_customer_bill(self, payment):
        if payment.ownership_line_id.loan_id:
            if not payment.ownership_line_id.loan_id.building_unit.partner_id:
                raise ValidationError(
                    f'You Must Set Owner for this Unit : {payment.ownership_line_id.loan_id.building_unit.name} To Create Customer Bill  ')

            owner_contract_loan_lines = payment.ownership_line_id.loan_id.mapped('loan_line')
            owner_contract = payment.ownership_line_id.loan_id
            is_down_payment = False
            if owner_contract_loan_lines:
                # is_down_payment =[if loan.name=='Down Payment' is_down_payment = True else is_down_payment = False for loan in owner_contract]
                for loan in owner_contract:
                    if loan.name == 'Down Payment' and loan.payment_state in ['in_payment', 'paid']:
                        is_down_payment = True
            if payment.ownership_line_id.name == 'Down Payment':
                is_down_payment = True
            customer_bill_object = None
            # 'product_id': payment.ownership_line_id.loan_id.building_unit.id,
            customer_bill_vals = {
                'partner_id': payment.ownership_line_id.loan_id.building_unit.partner_id.id,
                'ownership_id': payment.ownership_line_id.loan_id.id,
                'ref': payment.ownership_line_id.loan_id.name,
                'invoice_date': payment.date,
                'date': payment.date,
                'invoice_date_due': payment.date,
                'move_type': 'out_invoice',
                'is_mart_commission': True,
                'mart_commission': payment.ownership_line_id.loan_id.building_unit.partner_id.x_mart_commission,
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': self.env.ref('real_estate_commission.data_product_sales_commission').id,
                        'price_unit': (
                                                  payment.ownership_line_id.loan_id.pricing * payment.ownership_line_id.loan_id.building_unit.partner_id.x_mart_commission) / 100,
                        'quantity': 1,

                    }), ]
            }
            account_move = self.env['account.move'].sudo()
            customer_bill_before = account_move.search([
                ('partner_id', '=', payment.ownership_line_id.loan_id.building_unit.partner_id.id),
                ('ownership_id', '=', payment.ownership_line_id.loan_id.id),
                ('move_type', '=', 'out_invoice'),
                ('is_mart_commission', '=', True),
            ])
            if not customer_bill_before and is_down_payment:
                customer_bill_object = account_move.create(customer_bill_vals)
            if customer_bill_object:
                customer_bill_object.action_post()

    def make_unit_customer_commission_rental_bill(self, payment):
        if payment.rental_line_id.loan_id:
            if not payment.rental_line_id.loan_id.building_unit.partner_id:
                raise ValidationError(
                    f'You Must Set Owner for this Rental Unit : {payment.rental_line_id.loan_id.building_unit.name} To Create Customer Retnal Commission Bill  ')

            rental_contract_loan_lines = payment.rental_line_id.loan_id.mapped('loan_line')
            rental_contract = payment.rental_line_id.loan_id
            is_down_payment = False
            is_down_payment = True
            customer_bill_object = None
            customer_bill_vals = {
                'partner_id': payment.rental_line_id.loan_id.building_unit.partner_id.id,
                'rental_id': payment.rental_line_id.loan_id.id,
                'ref': payment.rental_line_id.loan_id.name,
                'invoice_date': payment.date,
                'date': payment.date,
                'invoice_date_due': payment.date,
                'move_type': 'out_invoice',
                'is_mart_commission': True,
                'mart_commission': payment.rental_line_id.loan_id.building_unit.partner_id.x_rental_mart_commission,
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': self.env.ref('real_estate_commission.data_product_sales_commission').id,
                        'price_unit': (
                                              payment.rental_line_id.loan_id.rental_fee * payment.rental_line_id.loan_id.building_unit.partner_id.x_rental_mart_commission) / 100,
                        'quantity': 1,
                    }), ]
            }
            account_move = self.env['account.move'].sudo()
            customer_bill_before = account_move.search([
                ('partner_id', '=', payment.rental_line_id.loan_id.building_unit.partner_id.id),
                ('rental_id', '=', payment.rental_line_id.loan_id.id),
                ('move_type', '=', 'out_invoice'),
                ('is_mart_commission', '=', True),
            ])

            if not customer_bill_before and is_down_payment:
                customer_bill_object = account_move.create(customer_bill_vals)
            if customer_bill_object:
                customer_bill_object.action_post()

    def make_salesmanager_commission(self, payment):
        commission = self.env['sales.commission'].search([
            ('commission_user_id', '=', payment.sales_team_id.user_id.id),
            ('start_date', '<=', payment.date),
            ('end_date', '>=', payment.date),
            ('state', '=', 'draft'),
            ('company_id', '=', payment.company_id.id),
        ], limit=1)
        sales_manager_commission = 0.0
        if not commission:
            commission = payment.create_base_commission(type='sales_manager', payment_date=payment.date)
        sales_ownership_contracts = self.env['ownership.contract'].search(
            ['&', '|', ('user_id', '=', payment.sales_user_id.id), ('salesmanager_id', '=', payment.sales_user_id.id),
             ('state', '=', 'confirmed')])

        sales_ownership_contracts_filtered_contract = sales_ownership_contracts.loan_line. \
            filtered(lambda
                         line: line.name == 'Down Payment' and line.payment_state == 'paid' or line.payment_state == 'in_payment')
        sales_ownership_contracts_filtered_cc = sales_ownership_contracts_filtered_contract.mapped('invoice_id').mapped(
            'date')
        sales_ownership_contracts_filtered_dd = sales_ownership_contracts_filtered_contract.mapped(
            'invoice_id').filtered(lambda
                                       invoice: invoice.date >= commission.start_date.date() and invoice.date <= commission.end_date.date()).mapped(
            'ownership_line_id').mapped('loan_id')
        ownership_contracts = sales_ownership_contracts_filtered_dd.ids
        if payment.ownership_line_id.name == 'Down Payment':
            ownership_contracts.append(payment.ownership_line_id.loan_id.id)
        self.env.cr.commit()
        commission.write({
            'ownership_contracts': [(6, 0, ownership_contracts)],
        })
        self.env.cr.commit()
        # ------- check units anf get amount for sales person in owner contacts for this person ==
        sales_contracts_count = len(commission.ownership_contracts)
        if commission.sales_commission_line:
            commission.sales_commission_line = [(5, 0, 0)]

        commission_type = payment.sales_team_id.commission_type
        if payment.sales_team_id.commission_range_ids:
            for range in payment.sales_team_id.commission_range_ids:
                ownership_contracts_orders = self.env['ownership.contract'].search(
                    [('id', 'in', commission.ownership_contracts.ids)], limit=range.ending_range, )
                if ownership_contracts_orders:
                    ownership_contracts_orders = ownership_contracts_orders.sorted(lambda c: c.create_date)
                if commission_type == 'per_unit':
                    if sales_contracts_count >= range.ending_range:
                        for contract in ownership_contracts_orders:
                            total_amount_units_sales_person = contract.pricing
                            sales_manager_commission = total_amount_units_sales_person * (
                                range.sales_manager_commission) / 100
                            self.env.cr.commit()
                            if contract.id not in commission.sales_commission_line.ownership_contract_id.ids:
                                payment.create_commission(sales_manager_commission, commission, type='sales_manager',
                                                          ownership_contract_id=contract.id,
                                                          commission_percentage=range.sales_manager_commission)
                            self.env.cr.commit()

                    elif sales_contracts_count >= range.starting_range and sales_contracts_count <= range.ending_range:
                        for contract in commission.ownership_contracts:
                            total_amount_units_sales_manager = contract.pricing
                            sales_manager_commission = total_amount_units_sales_manager * (
                                range.sales_manager_commission) / 100

                            self.env.cr.commit()
                            if contract.id not in commission.sales_commission_line.ownership_contract_id.ids:
                                print(f'w')
                                payment.create_commission(sales_manager_commission, commission, type='sales_manager',
                                                          ownership_contract_id=contract.id,
                                                          commission_percentage=range.sales_manager_commission)
                            self.env.cr.commit()

    def get_teamwise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person, amount_manager = 0.0, 0.0
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
                sales_manager_commission = 0
                sales_person_commission = 0
                if commission_type:
                    if payment.sales_team_id.commission_range_ids:
                        total = payment.amount
                        if payment.company_id.currency_id != payment.currency_id:
                            amount = payment.currency_id.compute(payment.amount, payment.company_id.currency_id)
                            total = amount
                        for range in payment.sales_team_id.commission_range_ids:
                            if total >= range.starting_range and total <= range.ending_range:
                                if commission_type == 'fix':
                                    sales_manager_commission = range.sales_manager_commission_amount
                                    sales_person_commission = range.sales_person_commission_amount
                                else:
                                    sales_manager_commission = (payment.amount * range.sales_manager_commission) / 100
                                    sales_person_commission = (payment.amount * range.sales_person_commission) / 100

                        amount_manager = sales_manager_commission
                        amount_person = sales_person_commission
        return amount_person, amount_manager

    def create_commission(self, amount, commission, type, ownership_contract_id=None, commission_percentage=None):
        commission_obj = self.env['sales.commission.line']
        product = self.env['product.product'].search([('is_commission_product', '=', 1)], limit=1)
        for payment in self:
            if amount != 0.0:
                commission_value = {
                    'sales_team_id': payment.sales_team_id.id,
                    'amount': amount,
                    'origin': payment.name,
                    'type': type,
                    'product_id': product.id,
                    'date': payment.date,
                    'src_payment_id': payment.id,
                    'sales_commission_id': commission.id,
                    'company_id': payment.company_id.id,
                    'currency_id': payment.company_id.currency_id.id,
                    'ownership_contract_id': ownership_contract_id if ownership_contract_id else False,
                    'commission_percentage': commission_percentage,
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

    def create_base_commission(self, type, payment_date=None):
        commission_obj = self.env['sales.commission']
        product = self.env['product.product'].search([('is_commission_product', '=', 1)], limit=1)
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
            commission_value = {
                'start_date': first_day_tz,
                'end_date': last_day_tz,
                'product_id': product.id,
                'commission_user_id': user,
                'company_id': order.company_id.id,
                'currency_id': order.currency_id.id,
                # 'ownership_contracts': [(4,order.ownership_line_id.loan_id.id)]
                #'ownership_contracts': [(4, order.ownership_line_id.loan_id.id)],
                'type': type,
            }
            if type == 'sales_person' or type == 'sales_manager':
                commission_value.update({'broker_id': False, 'third_party_id': False})
            if type == 'sales_broker':
                commission_value.update({'broker_id': user, 'commission_user_id': False, 'third_party_id': False})
                if payment_date:
                    commission_value.update({'start_date': payment_date, 'end_date': payment_date})
            elif type == 'sales_third_party':
                commission_value.update({'third_party_id': user, 'commission_user_id': False, 'broker_id': False})
            commission_id = commission_obj.create(commission_value)
        return commission_id

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        when_to_pay = self.env.company.when_to_pay
        if when_to_pay == 'invoice_payment':
            for payment in self:
                # payment.make_unit_vendor_bill(payment)
                payment.make_unit_customer_bill(payment)
                payment.make_unit_customer_commission_rental_bill(payment)
                if payment.sales_commission_apply:
                    commission_based_on = payment.company_id.commission_based_on if payment.company_id else self.env.company.commission_based_on
                    amount_person, amount_manager = 0.0, 0.0
                    amount_broker, amount_third_party = 0.0, 0.0
                    if commission_based_on == 'sales_team':
                        # amount_person, amount_manager, broker_commission, third_party_commission = payment.get_teamwise_commission()
                        amount_person, amount_manager = payment.get_teamwise_commission()
                    commission_type = payment.sales_team_id.commission_type
                    if commission_type:
                        if commission_type != 'per_unit':
                            commission = self.env['sales.commission'].search([
                                ('commission_user_id', '=', payment.sales_user_id.id),
                                ('start_date', '<', payment.date),
                                ('end_date', '>', payment.date),
                                ('state', '=', 'draft'),
                                ('company_id', '=', payment.company_id.id),
                            ], limit=1)
                            if not commission:
                                commission = payment.create_base_commission(type='sales_person')
                            payment.create_commission(amount_person, commission, type='sales_person')

                            if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
                                commission = self.env['sales.commission'].search([
                                    ('commission_user_id', '=', payment.sales_team_id.user_id.id),
                                    ('start_date', '<', payment.date),
                                    ('end_date', '>', payment.date),
                                    ('state', '=', 'draft'),
                                    ('company_id', '=', payment.company_id.id),
                                ], limit=1)
                                if not commission:
                                    commission = payment.create_base_commission(type='sales_manager')
                                payment.create_commission(amount_manager, commission, type='sales_manager',
                                                          ownership_contract_id=payment.ownership_line_id.loan_id.id)
                        else:

                            if payment.broker_id or payment.third_party_id:
                                if payment.ownership_line_id and not payment.rental_line_id:
                                    broker_third_party_commission_team = self.env['crm.team'].search(
                                        [('is_broker_third_party_commission', '=', True)], limit=1)
                                    if broker_third_party_commission_team:
                                        print(
                                            f'in payment.broker_id - payment.sales_team_id before:{payment.sales_team_id}')
                                        payment.sales_team_id = broker_third_party_commission_team.id
                                        payment.sales_user_id = payment.sales_team_id.user_id.id
                                        self.env.cr.commit()

                                        payment.make_salesmanager_commission(payment)
                                        if payment.broker_id:
                                            payment.make_broker_commission(payment)
                                        if payment.third_party_id:
                                            payment.make_third_party_commission(payment)

                            elif not payment.broker_id and not payment.third_party_id and payment.ownership_line_id.loan_id.user_id:
                                if payment.ownership_line_id and not payment.rental_line_id:
                                    # payment.sales_team_id = broker_third_party_commission_team.id
                                    payment.sales_user_id = payment.ownership_line_id.loan_id.user_id.id
                                    payment.make_salesmanager_commission(payment)
                                    payment.make_salesperson_commission(payment)

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
