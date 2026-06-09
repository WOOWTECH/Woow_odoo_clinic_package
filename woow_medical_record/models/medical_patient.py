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
        if not self.ids:
            for patient in self:
                patient.record_count = 0
            return
        data = self.env['medical.record'].sudo().read_group(
            [('patient_id', 'in', self.ids)],
            ['patient_id'],
            ['patient_id'],
        )
        counts = {d['patient_id'][0]: d['patient_id_count'] for d in data}
        for patient in self:
            patient.record_count = counts.get(patient.id, 0)

    @api.depends('record_ids.visit_date')
    def _compute_last_visit_date(self):
        """Compute the most recent visit date."""
        for patient in self:
            dates = list(filter(None, patient.record_ids.mapped('visit_date')))
            patient.last_visit_date = max(dates) if dates else False

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
