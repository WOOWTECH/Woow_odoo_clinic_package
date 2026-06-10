# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext

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
        'medical.physician',
        string='Physician',
        required=True,
        default=lambda self: self.env['medical.physician'].search(
            [('user_id', '=', self.env.uid)], limit=1,
        ),
        tracking=True,
        index=True,
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
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains(
        'vital_height', 'vital_weight', 'vital_bp_systolic',
        'vital_bp_diastolic', 'vital_pulse', 'vital_temp',
    )
    def _check_vital_signs(self):
        """Prevent negative vital sign values."""
        vital_fields = {
            'vital_height': _('Height'),
            'vital_weight': _('Weight'),
            'vital_bp_systolic': _('Systolic BP'),
            'vital_bp_diastolic': _('Diastolic BP'),
            'vital_pulse': _('Pulse'),
            'vital_temp': _('Temperature'),
        }
        for record in self:
            for field_name, label in vital_fields.items():
                value = record[field_name]
                if value and value < 0:
                    raise ValidationError(
                        _('%s cannot be negative.', label)
                    )

    @api.constrains('physician_id')
    def _check_physician_required(self):
        """Enforce physician assignment at ORM level."""
        for record in self:
            if not record.physician_id:
                raise ValidationError(
                    _('A physician must be assigned to the medical record.')
                )

    @api.constrains('physician_id', 'company_id')
    def _check_physician_company(self):
        """Ensure the physician belongs to the same company as the record."""
        for record in self:
            if (
                record.physician_id
                and record.physician_id.company_id
                and record.company_id
                and record.physician_id.company_id != record.company_id
            ):
                raise ValidationError(
                    _('The physician must belong to the same company as the medical record.')
                )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends('access_log_ids')
    def _compute_access_log_count(self):
        """Compute number of access log entries."""
        if not self.ids:
            self.access_log_count = 0
            return
        data = self.env['medical.record.access.log'].read_group(
            domain=[('record_id', 'in', self.ids)],
            fields=['record_id'],
            groupby=['record_id'],
        )
        mapped = {d['record_id'][0]: d['record_id_count'] for d in data}
        for record in self:
            record.access_log_count = mapped.get(record.id, 0)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Generate daily record number (YYYYMMDD-001) using ir.sequence with daily date range."""
        for vals in vals_list:
            # Enforce new records start as draft (prevent workflow bypass via API)
            if vals.get('state') and vals['state'] != 'draft':
                raise UserError(
                    _('New records must be created in draft state.')
                )
            if not vals.get('name'):
                visit_date = vals.get('visit_date') or fields.Datetime.now()
                if isinstance(visit_date, str):
                    visit_date = fields.Datetime.from_string(visit_date)
                company_id = vals.get('company_id', self.env.company.id)
                company = self.env['res.company'].browse(company_id)
                # Ensure a daily date range exists so counter resets each day.
                # Use SELECT FOR UPDATE to prevent race conditions when
                # multiple physicians create the first record of the day.
                visit_day = visit_date.date()
                seq = self.env['ir.sequence'].search([
                    ('code', '=', 'medical.record'),
                    '|',
                    ('company_id', '=', company.id),
                    ('company_id', '=', False),
                ], order='company_id', limit=1)
                if not seq:
                    raise UserError(
                        _('Medical record sequence not found. '
                          'Please contact the administrator.')
                    )
                # Lock the sequence row to serialize concurrent access
                self.env.cr.execute(
                    "SELECT id FROM ir_sequence WHERE id = %s FOR UPDATE",
                    (seq.id,)
                )
                date_range = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', seq.id),
                    ('date_from', '=', visit_day),
                    ('date_to', '=', visit_day),
                ], limit=1)
                if not date_range:
                    # Remove or shrink any broader range that covers this day
                    broader = self.env['ir.sequence.date_range'].search([
                        ('sequence_id', '=', seq.id),
                        ('date_from', '<=', visit_day),
                        ('date_to', '>=', visit_day),
                    ])
                    for br in broader:
                        if br.date_from < visit_day and br.date_to > visit_day:
                            # Split: keep before-part, create after-part
                            original_date_to = br.date_to
                            br.write({'date_to': visit_day - timedelta(days=1)})
                            self.env['ir.sequence.date_range'].sudo().create({
                                'sequence_id': seq.id,
                                'date_from': visit_day + timedelta(days=1),
                                'date_to': original_date_to,
                                'number_next': 1,
                            })
                        elif br.date_from == visit_day:
                            br.write({'date_from': visit_day + timedelta(days=1)})
                        elif br.date_to == visit_day:
                            br.write({'date_to': visit_day - timedelta(days=1)})
                        else:
                            br.unlink()
                    self.env['ir.sequence.date_range'].sudo().create({
                        'sequence_id': seq.id,
                        'date_from': visit_day,
                        'date_to': visit_day,
                        'number_next': 1,
                    })
                vals['name'] = (
                    self.env['ir.sequence']
                    .with_company(company)
                    .with_context(ir_sequence_date=visit_date)
                    .next_by_code('medical.record')
                )
        return super().create(vals_list)

    def write(self, vals):
        """Block direct state manipulation and protect signed records.

        State changes are only allowed via _write_state() called from
        action methods. The context flag '_medical_workflow' is NOT used
        since it can be injected via JSON-RPC kwargs.
        """
        if 'state' in vals:
            raise UserError(
                _('State changes must go through the workflow buttons '
                  '(Start / Sign / Reset to Draft).')
            )
        # Protect clinical fields on signed records
        protected_fields = (
            SOAP_FIELDS | {'diagnosis', 'attachment_ids',
            'vital_height', 'vital_weight', 'vital_bp_systolic',
            'vital_bp_diastolic', 'vital_pulse', 'vital_temp',
            'patient_id', 'physician_id', 'visit_date',
            'company_id', 'name'}
        )
        if any(f in vals for f in protected_fields):
            for rec in self:
                if rec.state == 'signed':
                    raise UserError(
                        _('Cannot modify a signed record. '
                          'Reset to draft first.')
                    )
        return super().write(vals)

    def _write_state(self, vals):
        """Internal method for workflow state transitions.

        Bypasses the write() state guard by calling super().write()
        directly. Only called from action_start/action_sign/action_reset_to_draft.
        Not exposed as a public API method (no @api.model decorator, starts with _).
        """
        return super(MedicalRecord, self).write(vals)

    def read(self, fields=None, load='_classic_read'):
        """Log view access when SOAP fields are read in form view (single record only)."""
        result = super().read(fields=fields, load=load)
        # Only log for single-record reads (form view), skip batch reads (list/calendar/pivot)
        if (
            len(self) == 1
            and self.env.context.get('medical_form_view')
            and fields
            and SOAP_FIELDS.intersection(fields)
        ):
            record = self
            if isinstance(record.id, int) and record.id > 0:
                self.env['medical.record.access.log'].sudo().create({
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
            record._write_state({'state': 'in_progress'})

    def action_sign(self):
        """Transition from in_progress to signed. Requires at least one SOAP field."""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(
                    _('Only in-progress records can be signed.')
                )
            # Only the responsible physician or admin can sign
            is_admin = self.env.user.has_group(
                'woow_medical_patient.group_medical_admin'
            )
            if record.physician_id.user_id.id != self.env.uid and not is_admin:
                raise UserError(
                    _('Only the responsible physician can sign this record.')
                )
            # Validate at least one SOAP field has real content (strip HTML tags)
            soap_filled = any(
                html2plaintext(getattr(record, field) or '').strip()
                for field in SOAP_FIELDS
            )
            if not soap_filled:
                raise ValidationError(
                    _('At least one SOAP field (S/O/A/P) must be filled before signing.')
                )
            record._write_state({
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
        """Transition from signed back to draft. Admin-only. Writes audit log."""
        if not self.env.user.has_group('woow_medical_patient.group_medical_admin'):
            raise UserError(
                _('Only medical administrators can reset records to draft.')
            )
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
            record._write_state({
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
