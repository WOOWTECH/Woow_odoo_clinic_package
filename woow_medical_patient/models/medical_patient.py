# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models, _


class MedicalPatient(models.Model):
    """Medical Patient — one record per person, lifelong."""

    _name = 'medical.patient'
    _description = 'Medical Patient'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'medical_no desc'

    _sql_constraints = [
        (
            'medical_no_company_uniq',
            'UNIQUE(company_id, medical_no)',
            'Patient number must be unique per company.',
        ),
        (
            'national_id_length',
            'CHECK(national_id IS NULL OR LENGTH(national_id) <= 10)',
            'National ID must be at most 10 characters.',
        ),
    ]

    # --- Delegation ---
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        required=True,
        ondelete='restrict',
        auto_join=True,
        index=True,
        help='The underlying res.partner record for this patient.',
    )

    # --- Identification ---
    medical_no = fields.Char(
        string='Patient No.',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Auto-generated patient number (P000001).',
    )
    national_id = fields.Char(
        string='National ID',
        size=10,
        groups='woow_medical_patient.group_medical_pii',
        help='National identification number (restricted to PII group).',
    )
    nhi_card_no = fields.Char(
        string='NHI Card No.',
        groups='woow_medical_patient.group_medical_pii',
        help='National Health Insurance card number (restricted to PII group).',
    )

    # --- Biometrics ---
    gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        string='Gender',
        tracking=True,
    )
    birthday = fields.Date(
        string='Birthday',
    )
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        help='Computed from birthday.',
    )
    blood_type = fields.Selection(
        selection=[
            ('a', 'A'),
            ('b', 'B'),
            ('ab', 'AB'),
            ('o', 'O'),
        ],
        string='Blood Type',
    )

    # --- Medical History ---
    allergies = fields.Text(
        string='Allergies',
        help='Known allergies.',
    )
    chronic_diseases = fields.Text(
        string='Chronic Diseases',
        help='Chronic disease history.',
    )
    medication_history = fields.Text(
        string='Medication History',
        help='Long-term medication usage.',
    )
    surgery_history = fields.Text(
        string='Surgery History',
        help='Past surgical procedures.',
    )

    # --- Emergency Contact ---
    emergency_name = fields.Char(
        string='Emergency Contact',
        help='Emergency contact person name.',
    )
    emergency_phone = fields.Char(
        string='Emergency Phone',
        help='Emergency contact phone number.',
    )
    emergency_relation = fields.Char(
        string='Relationship',
        help='Relationship to the patient.',
    )

    # --- Multi-company ---
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends('birthday')
    def _compute_age(self):
        """Compute patient age from birthday."""
        today = date.today()
        for patient in self:
            if patient.birthday:
                birthday = patient.birthday
                patient.age = (
                    today.year - birthday.year
                    - ((today.month, today.day) < (birthday.month, birthday.day))
                )
            else:
                patient.age = 0

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Generate medical_no from ir.sequence on creation."""
        for vals in vals_list:
            if not vals.get('medical_no'):
                company = self.env['res.company'].browse(
                    vals.get('company_id', self.env.company.id)
                )
                vals['medical_no'] = (
                    self.env['ir.sequence']
                    .with_company(company)
                    .next_by_code('medical.patient')
                )
        return super().create(vals_list)
