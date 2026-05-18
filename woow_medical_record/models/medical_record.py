# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

SOAP_FIELDS = {'subjective', 'objective', 'assessment', 'plan'}


class MedicalRecord(models.Model):
    """Medical Record — one record per visit, SOAP structure."""

    _name = 'medical.record'
    _description = 'Medical Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_date desc, name desc'

    _sql_constraints = [
        (
            'name_company_uniq',
            'UNIQUE(company_id, name)',
            'Record number must be unique per company.',
        ),
    ]

    # --- Identification ---
    name = fields.Char(
        string='Record No.',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Auto-generated record number (YYYYMMDD-001).',
    )
    patient_id = fields.Many2one(
        'medical.patient',
        string='Patient',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        help='The patient this record belongs to.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        related='patient_id.partner_id',
        store=True,
    )
    physician_id = fields.Many2one(
        'res.users',
        string='Physician',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
        domain=lambda self: [
            ('groups_id', 'in', [
                self.env.ref('woow_medical_patient.group_medical_physician').id,
            ])
        ],
        help='The physician responsible for this record.',
    )
    visit_date = fields.Datetime(
        string='Visit Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help='Date and time of the visit.',
    )

    # --- SOAP ---
    subjective = fields.Html(
        string='Subjective (S)',
        sanitize=True,
        help='Chief complaint and subjective symptoms.',
    )
    objective = fields.Html(
        string='Objective (O)',
        sanitize=True,
        help='Objective findings and observations.',
    )
    assessment = fields.Html(
        string='Assessment (A)',
        sanitize=True,
        help='Clinical assessment and diagnosis discussion.',
    )
    plan = fields.Html(
        string='Plan (P)',
        sanitize=True,
        help='Treatment plan and follow-up.',
    )

    # --- Diagnosis ---
    diagnosis = fields.Text(
        string='Diagnosis',
        help='Free-text diagnosis (ICD-10 planned for future).',
    )

    # --- Vital Signs ---
    vital_height = fields.Float(
        string='Height (cm)',
        help='Patient height in centimeters.',
    )
    vital_weight = fields.Float(
        string='Weight (kg)',
        help='Patient weight in kilograms.',
    )
    vital_bp_systolic = fields.Integer(
        string='BP Systolic',
        help='Systolic blood pressure (mmHg).',
    )
    vital_bp_diastolic = fields.Integer(
        string='BP Diastolic',
        help='Diastolic blood pressure (mmHg).',
    )
    vital_pulse = fields.Integer(
        string='Pulse',
        help='Pulse rate (bpm).',
    )
    vital_temp = fields.Float(
        string='Temperature (°C)',
        help='Body temperature in Celsius.',
    )

    # --- Attachments ---
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help='Before/after photos, lab reports, etc.',
    )

    # --- State & Signing ---
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('signed', 'Signed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Record workflow status.',
    )
    signed_by = fields.Many2one(
        'res.users',
        string='Signed By',
        readonly=True,
        help='User who signed this record.',
    )
    signed_at = fields.Datetime(
        string='Signed At',
        readonly=True,
        help='Timestamp when the record was signed.',
    )

    # --- Multi-company ---
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # --- Audit ---
    access_log_ids = fields.One2many(
        'medical.record.access.log',
        'record_id',
        string='Access Logs',
    )
    access_log_count = fields.Integer(
        string='Access Log Count',
        compute='_compute_access_log_count',
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends('access_log_ids')
    def _compute_access_log_count(self):
        """Compute number of access log entries."""
        for record in self:
            record.access_log_count = len(record.access_log_ids)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Generate daily record number (YYYYMMDD-001) using ir.sequence with date range."""
        for vals in vals_list:
            if not vals.get('name'):
                visit_date = vals.get('visit_date') or fields.Datetime.now()
                company_id = vals.get('company_id', self.env.company.id)
                company = self.env['res.company'].browse(company_id)
                vals['name'] = (
                    self.env['ir.sequence']
                    .with_company(company)
                    .with_context(ir_sequence_date=visit_date)
                    .next_by_code('medical.record')
                )
        return super().create(vals_list)

    def read(self, fields_list=None, load='_classic_read'):
        """Log view access when SOAP fields are read in form view context."""
        result = super().read(fields_list=fields_list, load=load)
        if (
            self.env.context.get('medical_form_view')
            and fields_list
            and SOAP_FIELDS.intersection(fields_list)
        ):
            log_model = self.env['medical.record.access.log']
            for record in self:
                log_model.create({
                    'record_id': record.id,
                    'action': 'view',
                    'note': _('Viewed SOAP content from form view.'),
                })
        return result

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_start(self):
        """Transition from draft to in_progress."""
        for record in self:
            if record.state != 'draft':
                raise UserError(
                    _('Only draft records can be started.')
                )
            record.state = 'in_progress'

    def action_sign(self):
        """Transition from in_progress to signed. Requires at least one SOAP field."""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(
                    _('Only in-progress records can be signed.')
                )
            # Validate at least one SOAP field is filled
            soap_filled = any(
                getattr(record, field)
                for field in SOAP_FIELDS
            )
            if not soap_filled:
                raise ValidationError(
                    _('At least one SOAP field (S/O/A/P) must be filled before signing.')
                )
            record.write({
                'state': 'signed',
                'signed_by': self.env.uid,
                'signed_at': fields.Datetime.now(),
            })
            # Write audit log
            self.env['medical.record.access.log'].create({
                'record_id': record.id,
                'action': 'sign',
                'note': _('Record signed.'),
            })

    def action_reset_to_draft(self):
        """Transition from signed back to draft. Writes audit log."""
        for record in self:
            if record.state != 'signed':
                raise UserError(
                    _('Only signed records can be reset to draft.')
                )
            # Write audit log before resetting
            self.env['medical.record.access.log'].create({
                'record_id': record.id,
                'action': 'unsign',
                'note': _('Record reset to draft.'),
            })
            record.write({
                'state': 'draft',
                'signed_by': False,
                'signed_at': False,
            })

    def action_view_access_logs(self):
        """Open access logs for this record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Access Logs'),
            'res_model': 'medical.record.access.log',
            'view_mode': 'list',
            'domain': [('record_id', '=', self.id)],
        }
