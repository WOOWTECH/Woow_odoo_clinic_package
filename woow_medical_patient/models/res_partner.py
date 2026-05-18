# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Reverse link from medical.patient ---
    patient_ids = fields.One2many(
        'medical.patient',
        'partner_id',
        string='Patients',
        help='Medical patient records linked to this contact.',
    )
    patient_count = fields.Integer(
        string='Patient Count',
        compute='_compute_patient_count',
    )

    @api.depends('patient_ids')
    def _compute_patient_count(self):
        patient_data = self.env['medical.patient'].sudo().read_group(
            domain=[('partner_id', 'in', self.ids)],
            fields=['partner_id'],
            groupby=['partner_id'],
        )
        mapped_data = {
            data['partner_id'][0]: data['partner_id_count']
            for data in patient_data
        }
        for partner in self:
            partner.patient_count = mapped_data.get(partner.id, 0)

    def action_open_patients(self):
        """Open patient record(s) linked to this partner."""
        self.ensure_one()
        patients = self.patient_ids
        if len(patients) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Patient'),
                'res_model': 'medical.patient',
                'view_mode': 'form',
                'res_id': patients.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Patients'),
            'res_model': 'medical.patient',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }
