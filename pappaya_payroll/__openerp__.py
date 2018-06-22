# -*- coding: utf-8 -*-
{
    'name': 'Pappaya Payroll Mgmt',
    'version': '9.0.2.4.0',
    'license': 'LGPL-3',
    'category': 'PappayaEd',
    "sequence": 1,
    'summary': 'Manage Educational Fees',
    'complexity': "easy",
    'description': """
        Description    ======
    """,
    'author': 'Think42Labs',
    'website': 'http://www.think42labs.com',
    'depends': ['hr','hr_payroll'],
    'data': [
        'views/hr_promotion_view.xml',
        # 'views/payroll_view.xml',

    ],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
