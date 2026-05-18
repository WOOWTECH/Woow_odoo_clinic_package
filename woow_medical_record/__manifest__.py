# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

{
    'name': 'Woow 醫療 - 病歷管理',
    'version': '18.0.1.0.0',
    'category': 'Medical',
    'summary': '醫美診所 SOAP 病歷與就診管理',
    'description': """
Woow Medical - Medical Record Management
==========================================
管理醫美診所的就診病歷，採用 SOAP 結構（主訴、客觀、評估、計畫）。
包含生命徵象記錄、狀態簽核流程、存取審計日誌。
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
        'security/medical_record_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/medical_record_data.xml',
        # Views
        'views/medical_record_views.xml',
        'views/medical_record_log_views.xml',
        'views/medical_record_menus.xml',
        # Patient view extension
        'views/medical_patient_views.xml',
    ],
    'demo': [
        'demo/medical_record_demo.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
