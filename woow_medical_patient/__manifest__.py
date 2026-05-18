# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

{
    'name': 'Woow 醫療 - 病患管理',
    'version': '18.0.1.0.0',
    'category': 'Medical',
    'summary': '醫美診所病患基本資料管理',
    'description': """
Woow Medical - Patient Management
==================================
管理醫美診所病患的基本資料、病史、緊急聯絡人等長期靜態資料。
每位病患一筆記錄，貫穿一生。
    """,
    'author': 'WoowTech',
    'website': 'https://www.woowtech.io',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'mail',
    ],
    'data': [
        # Security (must load first)
        'security/medical_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/medical_patient_data.xml',
        # Views
        'views/medical_patient_views.xml',
        'views/medical_patient_menus.xml',
    ],
    'demo': [
        'demo/medical_patient_demo.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
