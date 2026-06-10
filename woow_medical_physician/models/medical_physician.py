# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MedicalPhysician(models.Model):
    """Medical Physician — one record per doctor, lifelong."""

    _name = 'medical.physician'
    _description = 'Medical Physician'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'physician_no desc'

    _sql_constraints = [
        (
            'physician_no_company_uniq',
            'UNIQUE(company_id, physician_no)',
            'Physician number must be unique per company.',
        ),
        (
            'license_no_company_uniq',
            'UNIQUE(company_id, license_no)',
            'License number must be unique per company.',
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
        help='The underlying res.partner record for this physician.',
    )

    # --- Identification ---
    physician_no = fields.Char(
        string='Physician No.',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Auto-generated physician number (D000001).',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User Account',
        index=True,
        tracking=True,
        help='The Odoo login account linked to this physician.',
    )

    # --- Specialty ---
    specialty_id = fields.Many2one(
        'medical.specialty',
        string='Primary Specialty',
        ondelete='set null',
        tracking=True,
        help='Primary clinical specialty.',
    )
    specialty_ids = fields.Many2many(
        'medical.specialty',
        'medical_physician_specialty_rel',
        'physician_id',
        'specialty_id',
        string='Additional Specialties',
        help='Additional clinical specialties.',
    )

    # --- License ---
    license_no = fields.Char(
        string='License No.',
        tracking=True,
        help='Medical license certificate number.',
    )
    practice_license_no = fields.Char(
        string='Practice License No.',
        help='Practice license number.',
    )
    license_expiry = fields.Date(
        string='License Expiry',
        tracking=True,
        help='License expiration date.',
    )

    # --- Background ---
    education = fields.Text(
        string='Education',
        help='Education background.',
    )
    experience = fields.Text(
        string='Experience',
        help='Professional experience.',
    )

    # --- Multi-company ---
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # --- Smart Button ---
    related_partner_count = fields.Integer(
        string='Related Contact Count',
        compute='_compute_related_partner_count',
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends('partner_id')
    def _compute_related_partner_count(self):
        for physician in self:
            physician.related_partner_count = 1 if physician.partner_id else 0

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Generate physician_no from ir.sequence on creation."""
        for vals in vals_list:
            if not vals.get('physician_no'):
                company = self.env['res.company'].browse(
                    vals.get('company_id', self.env.company.id)
                )
                vals['physician_no'] = (
                    self.env['ir.sequence']
                    .with_company(company)
                    .next_by_code('medical.physician')
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_open_partner(self):
        """Open the linked res.partner record in form view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contact'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
        }
