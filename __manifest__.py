# -*- coding: utf-8 -*-

{
    'name': "Real Estate - Commissions",
    'version': "1.0.0",
    'author':'Integrated Data Technology, Inc.',
    'category': "Website",
    'summary': '',
    'description': '''

        ''',
    'sequence': 14,
    'depends' : ['account','sale_management','itsys_real_estate'],
    'data' : [
        'security/ir.model.access.csv',
        'security/sales_commission_security.xml',
        'data/commission_sequence.xml',
        'data/product_data.xml',
        'view/res_partner.xml',
        'view/base.xml',
        'view/sale_config_settings_views.xml',
        'view/crm_team_view.xml',
        'view/product_template_view.xml',
        'view/product_category_view.xml',
        'view/sales_commission_view.xml',
        'view/account_invoice_view.xml',
        'view/report_sales_commission.xml',
        'view/report_sales_commission_worksheet.xml',
        'view/account_payment.xml',
        'view/sale_view.xml',
              ],
    'demo': [],
    'website':'https://www.i-datatech.com',
    'installable': True,
    'auto_install': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
