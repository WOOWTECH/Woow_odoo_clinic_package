# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MedicalPatientRecord(models.Model):
    """Extend medical.patient with record-related fields."""

    _inherit = 'medical.patient'

    record_ids = fields.One2many(
        'medical.record',
        'patient_id',
        string='Medical Records',
        help='All medical records for this patient.',
    )
    record_count = fields.Integer(
        string='Record Count',
        compute='_compute_record_count',
        help='Number of medical records.',
    )
    last_visit_date = fields.Datetime(
        string='Last Visit',
        compute='_compute_last_visit_date',
        help='Date of the most recent visit.',
    )

    @api.depends('record_ids')
    def _compute_record_count(self):
        """Compute the number of medical records for each patient."""
        for patient in self:
            patient.record_count = len(patient.record_ids)

    @api.depends('record_ids.visit_date')
    def _compute_last_visit_date(self):
        """Compute the most recent visit date."""
        for patient in self:
            if patient.record_ids:
                patient.last_visit_date = max(
                    patient.record_ids.mapped('visit_date')
                )
            else:
                patient.last_visit_date = False

    def action_view_records(self):
        """Open medical records for this patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Medical Records'),
            'res_model': 'medical.record',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id, 'medical_form_view': True},
        }
