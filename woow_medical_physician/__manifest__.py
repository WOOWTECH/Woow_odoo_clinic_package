# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

{
    'name': 'Woow 醫療 - 醫師管理',
    'version': '18.0.1.0.0',
    'category': 'Medical',
    'summary': '醫美診所醫師檔案與專科管理',
    'description': """
Woow Medical - Physician Management
====================================
管理醫美診所醫師的個人檔案、專科、執照資訊。
每位醫師一筆記錄，可關聯病歷與系統帳號。
    """,
    'author': 'WoowTech',
    'website': 'https://www.woowtech.io',
    'license': 'LGPL-3',
    'depends': [
        'woow_medical_patient',
        'mail',
    ],
    'data': [
        # Security (must load first)
        'security/medical_physician_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/medical_physician_data.xml',
        'data/medical_specialty_data.xml',
        # Views
        'views/medical_physician_views.xml',
        'views/medical_specialty_views.xml',
        'views/medical_physician_menus.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/medical_physician_demo.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
